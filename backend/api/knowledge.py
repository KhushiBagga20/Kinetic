"""Knowledge-base endpoints — the RAG corpus and the retriever itself."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

import config
from src import market
from src.rag import (
    delete_source,
    ingest_directory,
    ingest_file,
    ingest_market_feed,
    reset,
    search_with_timing,
    sources,
    stats,
)

from .schemas import CaptureRequest, SearchRequest, passage_json

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats")
def index_stats() -> dict[str, Any]:
    return {
        **stats(),
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
        "retrieval_k": config.RETRIEVAL_K,
        "documents_dir": str(config.DOCUMENTS_DIR),
    }


@router.get("/sources")
def list_sources() -> list[dict[str, Any]]:
    return sources()


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """Chunk, embed and index one or more uploaded documents."""
    results: list[dict[str, Any]] = []
    for upload_file in files:
        suffix = Path(upload_file.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(await upload_file.read())
            temporary = handle.name
        try:
            chunks = ingest_file(temporary, source_name=upload_file.filename)
            results.append({"file": upload_file.filename, "chunks": chunks})
        except Exception as exc:
            results.append({"file": upload_file.filename, "error": str(exc)})
        finally:
            Path(temporary).unlink(missing_ok=True)
    return {"results": results, "stats": stats()}


@router.post("/ingest-directory")
def ingest_folder() -> dict[str, Any]:
    return {"results": ingest_directory(), "stats": stats()}


@router.post("/capture")
def capture(request: CaptureRequest) -> dict[str, Any]:
    """Snapshot a symbol's live quote, fundamentals and headlines into the index."""
    symbol = market.resolve_symbol(request.symbol)
    if not symbol:
        raise HTTPException(404, f"No tradable instrument found for '{request.symbol}'")
    return {"symbol": symbol, "chunks": ingest_market_feed(symbol), "stats": stats()}


@router.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    """Run the retriever on its own, so its behaviour is inspectable."""
    passages, elapsed = search_with_timing(request.query, k=request.k)
    return {
        "query": request.query,
        "ms": round(elapsed, 1),
        "passages": [passage_json(p) for p in passages],
    }


@router.delete("/sources/{source:path}")
def remove_source(source: str) -> dict[str, Any]:
    delete_source(source)
    return {"stats": stats()}


@router.post("/reset")
def reset_index() -> dict[str, Any]:
    reset()
    return {"stats": stats()}
