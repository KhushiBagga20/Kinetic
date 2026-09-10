"""
Research agent — retrieval-grounded, tool-calling, and streamed.

One question flows through three stages:

    1. retrieve   hybrid RAG over the user's documents and the live market feed
    2. reason     Gemma 4 sees that context plus the tool catalogue
    3. act        native tool calls run locally; results go back to the model

Everything is emitted as `Event` objects so the interface can show retrieval,
tool activity and the answer forming token by token.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import config
from src import preferences, tools
from src.llm import engine
from src.rag import Passage, format_context, search_with_timing

SYSTEM_PROMPT = """You are Kinetic, an investment research analyst that runs entirely on the user's own machine.

How you work:
- You are given RETRIEVED CONTEXT from the user's private knowledge base. Use it when it is relevant, and cite it as [S1], [S2] matching the numbering you were given.
- You have tools for live market data. Call them whenever the question depends on a current price, current fundamentals, current news, a screener or a forecast. Never guess a number you could look up.
- If the user names a company rather than a ticker, call resolve_ticker first.
- Anything phrased with "my" — my portfolio, my holdings, am I exposed, how am I doing — means the user's own book: call get_portfolio, or get_portfolio_exposure when they ask about a theme or an event.
- You may call several tools before answering, and you may call a tool again with better arguments if the first result was not what you needed.

How you answer:
- State where every number came from: "live market data (fetched HH:MM UTC)" or "from <document name>". If the two disagree, say so explicitly.
- Always attach units and periods: currency (USD, INR), scale (millions, crores), and the as-of time or fiscal period. Use only timestamps that appear in the data you were given — never estimate or invent a time.
- Lead with the direct answer in one or two sentences, then the supporting detail.

Formatting — the interface renders GitHub-flavoured markdown, so use it:
- Whenever you report more than two numbers that share a shape — positions, sectors, competitors, periods, metrics — put them in a markdown table rather than a bullet list. Give every numeric column a unit in its header, for example `Value (INR)` or `Change (%)`.
- Keep prose to short paragraphs. Use `###` for section headings and `-` for bullets that are genuinely a list rather than a table.
- When a comparison is easier to see than to read — an allocation, a set of returns, a sector split, a ranking — add a chart by emitting a fenced block exactly like this:

```kinetic-chart
{"type": "bar", "title": "Unrealised P&L by holding", "unit": "INR", "data": [{"label": "RELIANCE.NS", "value": -3510}, {"label": "HDFCBANK.NS", "value": 5062}]}
```

  `type` is "bar", "line" or "donut". Use "donut" for shares of a whole, "line" for anything over time, "bar" otherwise. Keep it to at most eight data points, use only numbers you actually retrieved, and still state the key figures in the text — the chart supports the answer, it does not replace it. Add at most one chart per answer, and none when a single number is the answer.
- If the data needed is missing, say exactly what is missing and what the user could ingest or ask instead. Do not fill gaps with plausible-sounding numbers.
- You are a research tool, not an adviser. Describe evidence and probabilities; never tell the user to buy or sell.
- Write to this specific person: their currency, their horizon, their actual positions. Address them by name when you have it, and keep it plain — no jargon that a first-time investor would have to look up.
"""


def _user_context() -> str:
    """A short profile block so answers are written for this person."""
    prefs = preferences.load()
    lines = ["## About the person you are talking to", prefs.describe()]

    try:
        from src.portfolio import load_holdings

        holdings = load_holdings()
    except Exception:
        holdings = []

    if holdings:
        symbols = ", ".join(f"{h.symbol} ({h.quantity:g} units)" for h in holdings)
        lines.append(
            f"They hold: {symbols}. Call get_portfolio for live values, weights and "
            "profit or loss before answering anything about their position — never "
            "estimate it."
        )
    else:
        lines.append(
            "They have not entered any holdings yet, so there is no portfolio to read."
        )
    return "\n".join(lines)


@dataclass
class Event:
    """A single update from the agent to the interface."""

    kind: str  # status | sources | thought | token | step_reset | tool_call | tool_result | done | error
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    question: str
    answer: str
    passages: list[Passage] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)


class ResearchAgent:
    """Holds conversation state for one chat session."""

    def __init__(self) -> None:
        self.turns: list[Turn] = []

    def reset(self) -> None:
        self.turns.clear()

    # -- prompt assembly ------------------------------------------------------

    def _messages(self, question: str, context: str) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{_user_context()}"}
        ]
        for turn in self.turns[-config.LLM_HISTORY_TURNS:]:
            messages.append({"role": "user", "content": turn.question})
            messages.append({"role": "assistant", "content": turn.answer})

        if context:
            user_content = (
                f"RETRIEVED CONTEXT from the user's knowledge base:\n\n{context}\n\n"
                f"---\nQuestion: {question}"
            )
        else:
            user_content = (
                f"(The knowledge base returned no matching passages for this question.)\n"
                f"Question: {question}"
            )
        messages.append({"role": "user", "content": user_content})
        return messages

    # -- main loop ------------------------------------------------------------

    def stream(self, question: str) -> Iterator[Event]:
        """Answer a question, emitting events as the work happens."""
        question = question.strip()
        if not question:
            return

        started = time.perf_counter()

        yield Event("status", "Searching your knowledge base")
        passages, retrieval_ms = search_with_timing(question)
        yield Event(
            "sources",
            f"{len(passages)} passages in {retrieval_ms:.0f} ms",
            {"passages": passages, "ms": retrieval_ms},
        )

        llm = engine()
        if not llm.is_loaded:
            yield Event("status", f"Loading {config.LLM_MODEL} into unified memory")

        messages = self._messages(question, format_context(passages))
        schemas = tools.schemas()
        used: list[str] = []
        answer = ""

        try:
            for step in range(config.LLM_MAX_TOOL_STEPS):
                yield Event("status", "Reasoning" if step == 0 else "Reading tool results")

                for piece in llm.stream(messages, tools=schemas):
                    if piece.channel == "answer":
                        yield Event("token", piece.text)
                    elif piece.channel == "thought":
                        yield Event("thought", piece.text)
                    elif piece.channel == "tool":
                        # The prose emitted before a tool call was a plan, not
                        # the answer — tell the interface to drop it.
                        yield Event("step_reset")

                reply = llm.last_reply()
                answer = reply.text

                if not reply.tool_calls:
                    break

                messages.append(
                    {
                        "role": "assistant",
                        "content": reply.text,
                        "tool_calls": [
                            {
                                "id": f"call_{step}_{index}",
                                "type": "function",
                                "function": {"name": call.name, "arguments": call.arguments},
                            }
                            for index, call in enumerate(reply.tool_calls)
                        ],
                    }
                )

                for index, call in enumerate(reply.tool_calls):
                    yield Event("tool_call", call.name, {"arguments": call.arguments})
                    result = tools.call(call.name, call.arguments)
                    used.append(call.name)
                    yield Event(
                        "tool_result",
                        call.name,
                        {"arguments": call.arguments, "result": result},
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "name": call.name,
                            "tool_call_id": f"call_{step}_{index}",
                            "content": result,
                        }
                    )
            else:
                answer = answer or (
                    "I reached the tool-call limit for this question. Try asking about "
                    "one symbol or one document at a time."
                )
        except Exception as exc:
            yield Event("error", f"{type(exc).__name__}: {exc}")
            return

        self.turns.append(
            Turn(question=question, answer=answer, passages=passages, tools_used=used)
        )
        yield Event(
            "done",
            answer,
            {
                "tools_used": used,
                "passages": passages,
                "seconds": round(time.perf_counter() - started, 2),
                "tokens_per_sec": round(llm.last_reply().tokens_per_sec, 1),
                "tokens": llm.last_reply().tokens,
            },
        )
