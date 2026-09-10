"""
Finance-aware text splitting.

Generic splitters cut straight through financial tables and leave numbers
without their labels ("1,428" with no idea it was Q2 revenue in millions).
This splitter works on structural blocks instead of a raw character window:

    * paragraphs are kept whole where possible
    * consecutive table-like lines are treated as one indivisible block
    * the nearest heading is prefixed to every chunk as a breadcrumb
    * oversized blocks fall back to sentence-boundary splits with overlap
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import config

_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s+.+"                       # markdown heading
    r"|(?:[A-Z][A-Z0-9 &/,'\-\.]{3,80})"        # ALL CAPS heading
    r"|(?:(?:Item|ITEM|Note|NOTE|Part|PART)\s+\d+[A-Za-z]?\.?.{0,80})"  # 10-K items
    r")\s*$"
)
_TABLE_LINE = re.compile(r"(\|.*\|)|(\t)|(\s{2,}[\(\)\-\$₹%\d,\.]{2,}\s*$)")
_NUMBER = re.compile(r"\d")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _is_table_line(line: str) -> bool:
    """A line that looks like a row of a financial table."""
    if not _NUMBER.search(line):
        return False
    numbers = len(re.findall(r"[\d,]+\.?\d*", line))
    return bool(_TABLE_LINE.search(line)) or numbers >= 3


def _blocks(text: str) -> list[tuple[str, str]]:
    """Split raw text into (kind, content) blocks. Kind is prose|table|heading."""
    lines = [line.rstrip() for line in text.splitlines()]
    blocks: list[tuple[str, str]] = []
    buffer: list[str] = []
    kind = "prose"

    def flush() -> None:
        nonlocal buffer
        content = "\n".join(buffer).strip()
        if content:
            blocks.append((kind, content))
        buffer = []

    for line in lines:
        if not line.strip():
            flush()
            continue
        if _HEADING.match(line) and len(line.strip()) < 90:
            flush()
            blocks.append(("heading", line.strip().lstrip("#").strip()))
            kind = "prose"
            continue
        line_kind = "table" if _is_table_line(line) else "prose"
        if line_kind != kind:
            flush()
            kind = line_kind
        buffer.append(line)
    flush()
    return blocks


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    """Split an oversized block on sentence boundaries, keeping an overlap."""
    sentences = _SENTENCE.split(text)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > size:  # a single monster sentence / table row
            parts.append(sentence[:size])
            sentence = sentence[size - overlap:]
        if len(current) + len(sentence) + 1 <= size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                parts.append(current)
            current = sentence
    if current:
        parts.append(current)
    return parts


def split_text(
    text: str,
    metadata: dict[str, Any] | None = None,
    size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """Split one document into retrieval-sized chunks with heading breadcrumbs."""
    size = size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    base = dict(metadata or {})

    chunks: list[Chunk] = []
    heading = ""
    current: list[str] = []
    current_len = 0

    def flush(carry_overlap: bool = True) -> None:
        nonlocal current, current_len
        body = "\n".join(current).strip()
        if not body:
            current, current_len = [], 0
            return
        text_out = f"{heading}\n{body}" if heading else body
        meta = dict(base)
        if heading:
            meta["section"] = heading
        meta["chunk_index"] = len(chunks)
        chunks.append(Chunk(text=text_out, metadata=meta))
        # carry an overlap tail into the next chunk so numbers keep their label,
        # but never across a heading — that would misattribute the section
        tail = body[-overlap:] if (overlap and carry_overlap) else ""
        current = [tail] if tail else []
        current_len = len(tail)

    for kind, content in _blocks(text):
        if kind == "heading":
            flush(carry_overlap=False)
            heading = content
            continue
        pieces = [content] if len(content) <= size else _split_long(content, size, overlap)
        for piece in pieces:
            if current_len + len(piece) > size and current_len:
                flush()
            current.append(piece)
            current_len += len(piece) + 1
    flush()
    return [c for c in chunks if len(c.text.strip()) > 40]
