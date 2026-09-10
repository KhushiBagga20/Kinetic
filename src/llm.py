"""
Local LLM engine — Gemma 4 (26B A4B, 4-bit) running on Apple Silicon via MLX.

Nothing here touches the GPU until `engine().load()` is called, so importing
Kinetic stays instant. The engine speaks Gemma's native chat format, which
gives us three things for free:

    * streamed tokens          → the UI can render text as it is produced
    * a separate "thought"     → reasoning is shown apart from the answer
    * native tool calls        → `<|tool_call>call:name{...}<tool_call|>`

Usage:
    from src.llm import engine
    for piece in engine().stream(messages, tools=TOOL_SCHEMAS):
        ...
"""

from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

import config

# Gemma 4 control markers.
TOOL_CALL_OPEN = "<|tool_call>"
TOOL_CALL_CLOSE = "<tool_call|>"
THOUGHT_OPEN = "<|channel>"
THOUGHT_CLOSE = "<channel|>"
QUOTE = '<|"|>'

_MARKERS = (TOOL_CALL_OPEN, TOOL_CALL_CLOSE, THOUGHT_OPEN, THOUGHT_CLOSE)
_MAX_MARKER = max(len(m) for m in _MARKERS)


# ─── Data types ───────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """A tool invocation requested by the model."""
    name: str
    arguments: dict[str, Any]


@dataclass
class Piece:
    """One streamed fragment. `channel` is "answer", "thought" or "tool"."""
    channel: str
    text: str


@dataclass
class Reply:
    """A complete model turn."""
    text: str = ""
    thought: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    tokens_per_sec: float = 0.0


# ─── Gemma argument parsing ───────────────────────────────────────────────────

def _parse_value(src: str, i: int) -> tuple[Any, int]:
    """Parse one Gemma-formatted value starting at `src[i]`."""
    if src.startswith(QUOTE, i):
        end = src.find(QUOTE, i + len(QUOTE))
        end = len(src) if end == -1 else end
        return src[i + len(QUOTE):end], end + len(QUOTE)

    if src[i] == "{":
        mapping, i = {}, i + 1
        while i < len(src) and src[i] != "}":
            key, i = _parse_key(src, i)
            if i < len(src) and src[i] == ":":
                i += 1
            mapping[key], i = _parse_value(src, i)
            if i < len(src) and src[i] == ",":
                i += 1
        return mapping, i + 1

    if src[i] == "[":
        items, i = [], i + 1
        while i < len(src) and src[i] != "]":
            item, i = _parse_value(src, i)
            items.append(item)
            if i < len(src) and src[i] == ",":
                i += 1
        return items, i + 1

    end = i
    while end < len(src) and src[end] not in ",}]":
        end += 1
    raw = src[i:end].strip()
    return _coerce(raw), end


def _parse_key(src: str, i: int) -> tuple[str, int]:
    if src.startswith(QUOTE, i):
        end = src.find(QUOTE, i + len(QUOTE))
        end = len(src) if end == -1 else end
        return src[i + len(QUOTE):end], end + len(QUOTE)
    end = i
    while end < len(src) and src[end] != ":":
        end += 1
    return src[i:end].strip(), end


def _coerce(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw.strip('"')


def parse_tool_call(body: str) -> ToolCall | None:
    """
    Parse the inside of a `<|tool_call>...<tool_call|>` block.

    mlx-lm ships a parser for this format; we use it when present and fall
    back to the reader below, which handles partial or malformed bodies.
    """
    body = body.strip()
    try:
        from mlx_lm.tool_parsers.gemma4 import parse_tool_call as mlx_parse

        parsed = mlx_parse(body)
        if isinstance(parsed, list):
            parsed = parsed[0]
        return ToolCall(name=parsed["name"], arguments=parsed.get("arguments") or {})
    except Exception:
        pass
    if body.startswith("call:"):
        body = body[len("call:"):]
    brace = body.find("{")
    if brace == -1:
        return ToolCall(name=body.strip(), arguments={})
    name = body[:brace].strip()
    args, _ = _parse_value(body[brace:], 0)
    return ToolCall(name=name, arguments=args if isinstance(args, dict) else {})


# ─── Incremental stream parser ────────────────────────────────────────────────

class StreamParser:
    """
    Splits a raw token stream into answer text, thoughts and tool calls.

    Markers can be split across tokens, so text is held back until it is
    provably not the start of a marker.
    """

    def __init__(self) -> None:
        self.buffer = ""
        self.channel = "answer"
        self.thought = ""
        self.answer = ""
        self.tool_calls: list[ToolCall] = []
        self._tool_body = ""
        self._label_buffer = ""      # holds the channel name until its newline
        self._awaiting_label = False

    def feed(self, text: str) -> list[Piece]:
        self.buffer += text
        return self._drain(final=False)

    def finish(self) -> list[Piece]:
        return self._drain(final=True)

    def _drain(self, final: bool) -> list[Piece]:
        pieces: list[Piece] = []
        while self.buffer:
            marker, index = self._next_marker()
            if marker is None:
                safe = self.buffer if final else self._safe_length()
                if safe <= 0:
                    break
                pieces += self._emit(self.buffer[:safe] if not final else self.buffer)
                self.buffer = "" if final else self.buffer[safe:]
                if not final:
                    break
                continue

            pieces += self._emit(self.buffer[:index])
            self.buffer = self.buffer[index + len(marker):]

            if marker == TOOL_CALL_OPEN:
                self.channel, self._tool_body = "tool", ""
            elif marker == TOOL_CALL_CLOSE:
                call = parse_tool_call(self._tool_body)
                if call and call.name:
                    self.tool_calls.append(call)
                    pieces.append(Piece("tool", call.name))
                self.channel, self._tool_body = "answer", ""
            elif marker == THOUGHT_OPEN:
                # The block opens with its channel name ("thought\n"), which is
                # metadata rather than content — swallow it before the newline.
                self.channel = "thought"
                self._awaiting_label = True
                self._label_buffer = ""
            elif marker == THOUGHT_CLOSE:
                self.channel = "answer"
        return pieces

    def _next_marker(self) -> tuple[str | None, int]:
        best, best_at = None, len(self.buffer)
        for marker in _MARKERS:
            at = self.buffer.find(marker)
            if at != -1 and at < best_at:
                best, best_at = marker, at
        return best, best_at

    def _safe_length(self) -> int:
        """How much of the buffer cannot be the prefix of a pending marker."""
        tail = min(_MAX_MARKER - 1, len(self.buffer))
        for size in range(tail, 0, -1):
            suffix = self.buffer[-size:]
            if any(m.startswith(suffix) for m in _MARKERS):
                return len(self.buffer) - size
        return len(self.buffer)

    def _emit(self, text: str) -> list[Piece]:
        if not text:
            return []
        if self.channel == "tool":
            self._tool_body += text
            return []
        if self.channel == "thought":
            if self._awaiting_label:
                self._label_buffer += text
                if "\n" not in self._label_buffer and len(self._label_buffer) < 32:
                    return []  # still inside the channel name
                head, _, text = self._label_buffer.partition("\n")
                self._awaiting_label = False
                self._label_buffer = ""
                if not _:  # no newline arrived — the label was not a label
                    text = head
                if not text:
                    return []
            self.thought += text
            return [Piece("thought", text)] if text else []
        self.answer += text
        return [Piece("answer", text)]


# ─── Engine ───────────────────────────────────────────────────────────────────

class LocalLLM:
    """
    Lazy wrapper around one MLX model.

    MLX streams are thread-local: weights loaded on one thread cannot be
    evaluated on another. Streamlit runs each interaction on a fresh script
    thread, so every MLX call — loading and generation alike — is funnelled
    through one dedicated worker thread, and generated pieces are handed back
    to the caller through a queue.
    """

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or config.LLM_MODEL
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kinetic-mlx")
        self._load_seconds = 0.0
        self._error = ""

    # -- lifecycle ------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "loaded": self.is_loaded,
            "load_seconds": round(self._load_seconds, 1),
            "error": self._error,
            "backend": "MLX / Apple Silicon",
        }

    def load(self) -> None:
        """Load weights into unified memory. Blocking, ~10-60s on first run."""
        if self.is_loaded:
            return
        self._worker.submit(self._load_on_worker).result()

    def _load_on_worker(self) -> None:
        """Runs on the MLX thread — every array is created there."""
        if self.is_loaded:
            return
        with self._lock:
            if self.is_loaded:
                return
            started = time.time()
            try:
                from mlx_lm import load

                self._model, self._tokenizer = load(self.model_id)
                self._error = ""
            except Exception as exc:  # surfaced in the UI, never raised at import
                self._error = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                self._load_seconds = time.time() - started

    def unload(self) -> None:
        """Drop the weights. Freed on the worker thread that created them."""

        def release() -> None:
            self._model = None
            self._tokenizer = None

        self._worker.submit(release).result()

    # -- generation -----------------------------------------------------------

    def stream(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict] | None = None,
        max_tokens: int | None = None,
        thinking: bool | None = None,
    ) -> Iterator[Piece]:
        """Yield answer/thought/tool pieces as the model produces them."""
        pieces: queue.Queue = queue.Queue()
        done = object()

        def produce() -> None:
            try:
                self._load_on_worker()
                for piece in self._generate(messages, tools, max_tokens, thinking):
                    pieces.put(piece)
            except BaseException as exc:  # re-raised on the consumer's thread
                pieces.put(exc)
            finally:
                pieces.put(done)

        future = self._worker.submit(produce)
        while True:
            item = pieces.get()
            if item is done:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
        future.result()

    def _generate(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict] | None,
        max_tokens: int | None,
        thinking: bool | None,
    ) -> Iterator[Piece]:
        """The actual MLX call. Only ever runs on the worker thread."""
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        prompt = self._build_prompt(messages, tools, thinking)
        sampler = make_sampler(
            temp=config.LLM_TEMPERATURE,
            top_p=config.LLM_TOP_P,
            top_k=config.LLM_TOP_K,
        )

        parser = StreamParser()
        self._last = Reply()
        for response in stream_generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens or config.LLM_MAX_TOKENS,
            sampler=sampler,
        ):
            for piece in parser.feed(response.text):
                yield piece
            self._last.tokens = response.generation_tokens
            self._last.tokens_per_sec = response.generation_tps
        for piece in parser.finish():
            yield piece

        self._last.text = parser.answer.strip()
        self._last.thought = parser.thought.strip()
        self._last.tool_calls = parser.tool_calls

    def last_reply(self) -> Reply:
        """The complete turn produced by the most recent `stream()` call."""
        return getattr(self, "_last", Reply())

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict] | None = None,
        max_tokens: int | None = None,
    ) -> Reply:
        """Non-streaming convenience wrapper."""
        for _ in self.stream(messages, tools=tools, max_tokens=max_tokens):
            pass
        return self.last_reply()

    def _build_prompt(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict] | None,
        thinking: bool | None,
    ) -> list[int]:
        """Render the chat template to token ids.

        The template emits its own `<bos>`, so the text is encoded without
        adding special tokens a second time.
        """
        kwargs: dict[str, Any] = {"add_generation_prompt": True, "tokenize": False}
        if tools:
            kwargs["tools"] = list(tools)
        kwargs["enable_thinking"] = config.LLM_THINKING if thinking is None else thinking
        try:
            text = self._tokenizer.apply_chat_template(list(messages), **kwargs)
        except TypeError:  # a template that does not accept enable_thinking
            kwargs.pop("enable_thinking", None)
            text = self._tokenizer.apply_chat_template(list(messages), **kwargs)
        return self._tokenizer.encode(text, add_special_tokens=False)


_engine: LocalLLM | None = None


def engine() -> LocalLLM:
    """The process-wide LLM engine (created, not loaded)."""
    global _engine
    if _engine is None:
        _engine = LocalLLM()
        if config.LLM_AUTOLOAD:
            _engine.load()
    return _engine
