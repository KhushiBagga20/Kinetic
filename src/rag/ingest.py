"""
Ingestion — turning files and live market data into searchable chunks.

Two entry points matter:

    ingest_file / ingest_directory   your own documents (PDF, TXT, MD, CSV, HTML)
    ingest_market_feed               live quotes, fundamentals and headlines

The second one is what makes retrieval *live*: today's headlines and today's
valuation numbers become retrievable passages, tagged with the timestamp they
were captured at, and re-ingesting a symbol replaces its previous snapshot.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from src.rag import store
from src.rag.chunking import split_text
from src.rag.retriever import invalidate_cache

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown", ".csv", ".html", ".htm", ".json"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ─── File loaders ─────────────────────────────────────────────────────────────

def _load_pdf(path: Path) -> list[tuple[str, dict[str, Any]]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((text, {"page": number}))
    return pages


def _load_csv(path: Path) -> list[tuple[str, dict[str, Any]]]:
    import pandas as pd

    frame = pd.read_csv(path)
    return [(frame.to_string(index=False), {"rows": int(len(frame))})]


def _load_html(path: Path) -> list[tuple[str, dict[str, Any]]]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", raw)
    return [(re.sub(r"\n{3,}", "\n\n", text), {})]


def _load_plain(path: Path) -> list[tuple[str, dict[str, Any]]]:
    return [(path.read_text(encoding="utf-8", errors="ignore"), {})]


def load_file(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Read one file into (text, metadata) parts. Unsupported types return []."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".csv":
        return _load_csv(path)
    if suffix in {".html", ".htm"}:
        return _load_html(path)
    if suffix in {".txt", ".md", ".markdown", ".json"}:
        return _load_plain(path)
    return []


# ─── Document ingestion ───────────────────────────────────────────────────────

def ingest_text(
    text: str,
    source: str,
    extra: dict[str, Any] | None = None,
    collection: str = store.DOCUMENTS,
) -> int:
    """Chunk, embed and index a raw string. Returns the chunk count."""
    base = {"source": source, "kind": "document", "ingested": _now(), **(extra or {})}
    chunks = split_text(text, base)
    if not chunks:
        return 0
    written = store.add(
        [c.text for c in chunks], [c.metadata for c in chunks], name=collection
    )
    invalidate_cache()
    return written


def ingest_file(path: str | Path, source_name: str | None = None) -> int:
    """Index one document file. Re-ingesting the same file refreshes it."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    parts = load_file(path)
    if not parts:
        raise ValueError(f"Unsupported file type: {path.suffix or 'none'}")

    source = source_name or path.name
    store.delete_source(source, store.DOCUMENTS)

    total = 0
    for text, metadata in parts:
        base = {
            "source": source,
            "kind": "document",
            "file_type": path.suffix.lstrip(".").lower(),
            "ingested": _now(),
            **metadata,
        }
        chunks = split_text(text, base)
        if chunks:
            total += store.add(
                [c.text for c in chunks], [c.metadata for c in chunks], name=store.DOCUMENTS
            )
    invalidate_cache()
    return total


def ingest_directory(directory: str | Path | None = None) -> dict[str, int]:
    """Index every supported file in a folder. Returns {filename: chunks}."""
    directory = Path(directory or config.DOCUMENTS_DIR)
    results: dict[str, int] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            try:
                results[path.name] = ingest_file(path)
            except Exception as exc:
                results[path.name] = 0
                print(f"  ! {path.name}: {exc}")
    return results


# ─── Live market ingestion ────────────────────────────────────────────────────

def _quote_document(symbol: str) -> tuple[str, dict[str, Any]] | None:
    from src.market import get_fundamentals, get_quote

    quote = get_quote(symbol)
    if quote is None:
        return None
    lines = [quote.to_text()]

    fundamentals = get_fundamentals(symbol)
    if fundamentals:
        lines.append(f"\nFundamentals for {symbol} (live, {fundamentals.get('as_of', '')}):")
        for key, value in fundamentals.items():
            if key in {"as_of", "business_summary"}:
                continue
            if isinstance(value, float):
                value = f"{value:,.4f}".rstrip("0").rstrip(".")
            lines.append(f"- {key.replace('_', ' ')}: {value}")
        if fundamentals.get("business_summary"):
            lines.append(f"\nBusiness summary: {fundamentals['business_summary']}")

    return "\n".join(lines), {
        "source": f"live:{symbol}:snapshot",
        "symbol": symbol,
        "kind": "market_snapshot",
        "ingested": _now(),
    }


def ingest_market_feed(symbol: str, include_news: bool = True) -> int:
    """
    Capture the current state of one symbol into the vector store.

    Indexes a price/fundamentals snapshot plus recent headlines, so questions
    like "what is the market saying about NVDA right now?" retrieve fresh,
    timestamped evidence instead of stale text.
    """
    from src.market import get_news

    symbol = symbol.strip().upper()
    if not symbol:
        return 0

    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    snapshot = _quote_document(symbol)
    if snapshot is None:
        return 0
    store.delete_source(snapshot[1]["source"], store.MARKET)
    for chunk in split_text(snapshot[0], snapshot[1]):
        texts.append(chunk.text)
        metadatas.append(chunk.metadata)

    if include_news:
        for index, article in enumerate(get_news(symbol)):
            body = f"{article.title}\n{article.summary}".strip()
            metadata = {
                "source": f"live:{symbol}:news:{index}",
                "symbol": symbol,
                "kind": "news",
                "publisher": article.publisher,
                "published": article.published,
                "url": article.url,
                "ingested": _now(),
                "chunk_index": 0,
            }
            store.delete_source(metadata["source"], store.MARKET)
            texts.append(body)
            metadatas.append(metadata)

    written = store.add(texts, metadatas, name=store.MARKET)
    invalidate_cache()
    return written
