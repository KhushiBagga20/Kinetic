"""
Vector store — a persistent ChromaDB instance on disk.

Two collections, because they have very different lifecycles:

    documents    your own corpus (annual reports, fact sheets, notes)
    market_feed  live headlines and snapshots, re-indexed as markets move

Embeddings are computed by `src.rag.embeddings` and passed in explicitly, so
Chroma never downloads a model of its own.
"""

from __future__ import annotations

import hashlib
from typing import Any

import chromadb

import config
from src.rag.embeddings import embed, embed_query

DOCUMENTS = config.COLLECTION_DOCUMENTS
MARKET = config.COLLECTION_MARKET

_client: chromadb.ClientAPI | None = None


def client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(config.VECTOR_DIR))
    return _client


def collection(name: str = DOCUMENTS):
    """Get or create a cosine-distance collection."""
    return client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def make_id(text: str, metadata: dict[str, Any]) -> str:
    """Stable content hash, so re-ingesting a file cannot create duplicates."""
    key = f"{metadata.get('source', '')}|{metadata.get('chunk_index', '')}|{text}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Chroma only stores scalars."""
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, (str, int, float, bool)) and value != ""
    }


def add(texts: list[str], metadatas: list[dict[str, Any]], name: str = DOCUMENTS) -> int:
    """Embed and upsert a batch of chunks. Returns the number written."""
    if not texts:
        return 0
    metas = [_clean_metadata(m) for m in metadatas]
    ids = [make_id(t, m) for t, m in zip(texts, metadatas)]
    collection(name).upsert(
        ids=ids, embeddings=embed(texts), documents=texts, metadatas=metas
    )
    return len(ids)


def search(
    query: str,
    k: int,
    name: str = DOCUMENTS,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Dense nearest-neighbour search. Returns dicts with a cosine `score`."""
    store = collection(name)
    if store.count() == 0:
        return []
    result = store.query(
        query_embeddings=[embed_query(query)],
        n_results=min(k, store.count()),
        where=where or None,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for text, meta, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "metadata": dict(meta or {}),
                "score": round(1.0 - float(distance), 4),  # cosine similarity
                "collection": name,
            }
        )
    return hits


def all_chunks(name: str = DOCUMENTS, limit: int | None = None) -> list[dict[str, Any]]:
    """Every stored chunk — used to build the lexical (BM25) index."""
    store = collection(name)
    if store.count() == 0:
        return []
    payload = store.get(include=["documents", "metadatas"], limit=limit)
    return [
        {"text": text, "metadata": dict(meta or {}), "collection": name}
        for text, meta in zip(payload["documents"], payload["metadatas"])
    ]


def count(name: str = DOCUMENTS) -> int:
    return collection(name).count()


def sources(name: str = DOCUMENTS) -> list[dict[str, Any]]:
    """One row per ingested source file, with its chunk count."""
    tally: dict[str, dict[str, Any]] = {}
    for chunk in all_chunks(name):
        meta = chunk["metadata"]
        key = str(meta.get("source", "unknown"))
        row = tally.setdefault(
            key,
            {"source": key, "chunks": 0, "kind": meta.get("kind", "document"), "ingested": meta.get("ingested", "")},
        )
        row["chunks"] += 1
    return sorted(tally.values(), key=lambda r: r["source"])


def delete_source(source: str, name: str = DOCUMENTS) -> None:
    """Remove every chunk that came from one file."""
    collection(name).delete(where={"source": source})


def reset(name: str | None = None) -> None:
    """Drop one collection, or the whole index when `name` is None."""
    for target in ([name] if name else [DOCUMENTS, MARKET]):
        try:
            client().delete_collection(target)
        except Exception:
            pass


def stats() -> dict[str, Any]:
    return {
        "documents": count(DOCUMENTS),
        "market_feed": count(MARKET),
        "path": str(config.VECTOR_DIR),
        "embedding_model": config.EMBEDDING_MODEL,
    }
