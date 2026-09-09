"""
Embeddings — sentence-transformers embedding model for the RAG pipeline.

Uses all-MiniLM-L6-v2 (384-dimensional):
    - Fast: ~14ms per query on Apple Silicon
    - Small: ~80MB model size
    - Accurate: good performance on semantic similarity tasks
    - Cached: singleton pattern avoids reloading

For higher accuracy (at cost of speed), consider:
    - all-mpnet-base-v2 (768-dim, ~40ms/query)
    - bge-small-en-v1.5 (384-dim, ~15ms/query)
"""

from typing import Optional

from langchain_community.embeddings import HuggingFaceEmbeddings

import config


# ─── Singleton embedding model ───────────────────────────────────────────────
_embedding_model: Optional[HuggingFaceEmbeddings] = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Get the singleton embedding model instance.
    Loads the model lazily on first call for fast startup.

    Returns:
        HuggingFaceEmbeddings instance using the configured model.
    """
    global _embedding_model
    if _embedding_model is None:
        print(f"🔄 Loading embedding model: {config.EMBEDDING_MODEL}...")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},   # MPS can be used: "mps"
            encode_kwargs={
                "normalize_embeddings": True,  # cosine similarity optimization
                "batch_size": 64,              # batch for faster bulk embedding
            },
        )
        print(f"✅ Embedding model loaded: {config.EMBEDDING_MODEL}")
    return _embedding_model
