"""Retrieval-augmented generation over your documents and the live market feed."""

from src.rag.ingest import (
    ingest_directory,
    ingest_file,
    ingest_market_feed,
    ingest_text,
)
from src.rag.retriever import Passage, format_context, retrieve, search_with_timing
from src.rag.store import count, delete_source, reset, sources, stats

__all__ = [
    "Passage",
    "count",
    "delete_source",
    "format_context",
    "ingest_directory",
    "ingest_file",
    "ingest_market_feed",
    "ingest_text",
    "reset",
    "retrieve",
    "search_with_timing",
    "sources",
    "stats",
]
