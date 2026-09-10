"""
Hybrid retrieval — dense vectors + BM25 keyword matching.

Dense search understands meaning ("how profitable is it" → margins), keyword
search nails exact tokens (a ticker, "FY2024", "3.2%"). Financial questions
need both, so the two ranked lists are fused with Reciprocal Rank Fusion and
then diversified with MMR to remove near-duplicate chunks.

    query ─┬─ dense  (Chroma, cosine) ─┐
           └─ BM25   (in-memory)       ├─ RRF ─ MMR ─ top-k passages
                                       ┘
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

import config
from src.rag import store
from src.rag.embeddings import embed, embed_query

_TOKEN = re.compile(r"[a-z0-9][a-z0-9\.\-%]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


# ─── BM25 ─────────────────────────────────────────────────────────────────────

class BM25:
    """Compact Okapi BM25 over the chunks currently in a collection."""

    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = [tokenize(t) for t in texts]
        self.lengths = [len(d) for d in self.docs]
        self.avg_length = (sum(self.lengths) / len(self.docs)) if self.docs else 0.0
        self.frequencies: list[dict[str, int]] = []
        document_count: dict[str, int] = {}
        for tokens in self.docs:
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            self.frequencies.append(counts)
            for token in counts:
                document_count[token] = document_count.get(token, 0) + 1
        total = len(self.docs) or 1
        self.idf = {
            token: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for token, freq in document_count.items()
        }

    def scores(self, query: str) -> np.ndarray:
        tokens = tokenize(query)
        result = np.zeros(len(self.docs), dtype=np.float32)
        if not self.docs:
            return result
        for index, counts in enumerate(self.frequencies):
            length = self.lengths[index] or 1
            total = 0.0
            for token in tokens:
                frequency = counts.get(token)
                if not frequency:
                    continue
                norm = 1 - self.b + self.b * length / (self.avg_length or 1)
                total += self.idf.get(token, 0.0) * frequency * (self.k1 + 1) / (
                    frequency + self.k1 * norm
                )
            result[index] = total
        return result


# ─── Passages ─────────────────────────────────────────────────────────────────

@dataclass
class Passage:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    collection: str = ""

    @property
    def source(self) -> str:
        return str(self.metadata.get("source", "unknown"))

    @property
    def label(self) -> str:
        section = self.metadata.get("section")
        page = self.metadata.get("page")
        parts = [self.source]
        if page:
            parts.append(f"p.{page}")
        if section:
            parts.append(str(section)[:60])
        return " · ".join(parts)


# ─── Lexical index cache ──────────────────────────────────────────────────────

_index_cache: dict[str, tuple[int, list[dict], BM25]] = {}


def _lexical_index(name: str) -> tuple[list[dict], BM25]:
    """BM25 index for a collection, rebuilt whenever its chunk count changes."""
    total = store.count(name)
    cached = _index_cache.get(name)
    if cached and cached[0] == total:
        return cached[1], cached[2]
    chunks = store.all_chunks(name)
    bm25 = BM25([c["text"] for c in chunks])
    _index_cache[name] = (total, chunks, bm25)
    return chunks, bm25


def invalidate_cache() -> None:
    """Called after ingestion so the next search sees the new chunks."""
    _index_cache.clear()


# ─── Fusion ───────────────────────────────────────────────────────────────────

def _rrf(rankings: list[list[str]], k: int) -> dict[str, float]:
    """Reciprocal Rank Fusion: robust to the two legs using different scales."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for position, key in enumerate(ranking):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + position + 1)
    return fused


def _mmr(query_vector: np.ndarray, vectors: np.ndarray, k: int, lambda_: float) -> list[int]:
    """Maximal Marginal Relevance — relevance minus redundancy."""
    if len(vectors) == 0:
        return []
    relevance = vectors @ query_vector
    selected: list[int] = [int(np.argmax(relevance))]
    while len(selected) < min(k, len(vectors)):
        best_index, best_score = -1, -np.inf
        similarity = vectors @ vectors[selected].T
        for index in range(len(vectors)):
            if index in selected:
                continue
            score = lambda_ * relevance[index] - (1 - lambda_) * float(similarity[index].max())
            if score > best_score:
                best_index, best_score = index, score
        if best_index < 0:
            break
        selected.append(best_index)
    return selected


# ─── Public API ───────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    k: int | None = None,
    collections: tuple[str, ...] = (store.DOCUMENTS, store.MARKET),
) -> list[Passage]:
    """
    Retrieve the passages most likely to answer `query`.

    Runs dense and lexical search over each collection, fuses the rankings,
    drops anything below the relevance floor and diversifies the survivors.
    """
    query = query.strip()
    k = k or config.RETRIEVAL_K
    if not query:
        return []

    pool: dict[str, dict[str, Any]] = {}
    rankings: list[list[str]] = []

    for name in collections:
        if store.count(name) == 0:
            continue

        dense = store.search(query, k=config.RETRIEVAL_CANDIDATES, name=name)
        dense_ranking = []
        for hit in dense:
            key = f"{name}:{hash(hit['text'])}"
            pool.setdefault(key, hit)
            pool[key]["score"] = max(pool[key].get("score", 0.0), hit["score"])
            dense_ranking.append(key)
        rankings.append(dense_ranking)

        chunks, bm25 = _lexical_index(name)
        if chunks:
            scores = bm25.scores(query)
            best = np.argsort(scores)[::-1][: config.RETRIEVAL_CANDIDATES]
            lexical_ranking = []
            for index in best:
                if scores[index] <= 0:
                    continue
                chunk = chunks[int(index)]
                key = f"{name}:{hash(chunk['text'])}"
                entry = pool.setdefault(key, {**chunk, "score": 0.0})
                entry["keyword_score"] = float(scores[index])
                lexical_ranking.append(key)
            rankings.append(lexical_ranking)

    if not pool:
        return []

    fused = _rrf(rankings, config.RRF_K)
    ordered = sorted(pool.items(), key=lambda item: fused.get(item[0], 0.0), reverse=True)
    shortlist = [entry for _, entry in ordered[: max(k * 4, config.RETRIEVAL_CANDIDATES)]]

    # Relevance floor: a chunk that is neither semantically close nor a strong
    # keyword match is noise, and noise in a financial answer is worse than
    # silence. Lexical hits are judged relative to the best hit for this query.
    best_keyword = max((e.get("keyword_score", 0.0) for e in shortlist), default=0.0)
    shortlist = [
        entry
        for entry in shortlist
        if entry.get("score", 0.0) >= config.MIN_RELEVANCE
        or entry.get("keyword_score", 0.0) >= 0.35 * best_keyword > 0
    ]
    if not shortlist:
        return []

    vectors = np.asarray(embed([entry["text"] for entry in shortlist]), dtype=np.float32)
    query_vector = np.asarray(embed_query(query), dtype=np.float32)
    chosen = _mmr(query_vector, vectors, k, config.MMR_LAMBDA)

    return [
        Passage(
            text=shortlist[i]["text"],
            metadata=shortlist[i]["metadata"],
            score=round(float(vectors[i] @ query_vector), 4),
            collection=shortlist[i].get("collection", ""),
        )
        for i in chosen
    ]


def format_context(passages: list[Passage]) -> str:
    """Render passages as numbered, citable sources for the prompt."""
    blocks = []
    for index, passage in enumerate(passages, 1):
        blocks.append(f"[S{index}] {passage.label}\n{passage.text.strip()}")
    return "\n\n".join(blocks)


def search_with_timing(query: str, k: int | None = None) -> tuple[list[Passage], float]:
    """Retrieve and report how long it took, for the latency read-out."""
    started = time.perf_counter()
    passages = retrieve(query, k=k)
    return passages, (time.perf_counter() - started) * 1000
