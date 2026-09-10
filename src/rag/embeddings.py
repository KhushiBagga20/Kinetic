"""
Sentence embeddings — a small local model, loaded once, on demand.

all-MiniLM-L6-v2 produces 384-dimensional vectors in a few milliseconds per
query on Apple Silicon, which keeps retrieval well below the latency budget
of the generation step. Vectors are L2-normalised so cosine similarity is a
plain dot product.
"""

from __future__ import annotations

import threading

import numpy as np

import config

_model = None
_lock = threading.Lock()


def get_model():
    """Load (once) and return the sentence-transformer model."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of passages."""
    if not texts:
        return []
    vectors = get_model().encode(
        texts,
        batch_size=config.EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32).tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query."""
    return embed([text])[0]


def dimensions() -> int:
    return int(get_model().get_sentence_embedding_dimension())
