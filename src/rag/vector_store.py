"""
Vector Store — ChromaDB persistent storage for document embeddings.

Features:
    - Persistent storage in chroma_db/ directory
    - Survives restarts without re-embedding
    - Configurable top-k retrieval (default k=3)
    - Collection management (create, reset, query)
"""

from typing import List, Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

import config
from src.rag.embeddings import get_embedding_model


# ─── Singleton vector store ──────────────────────────────────────────────────
_vector_store: Optional[Chroma] = None


def get_vector_store() -> Chroma:
    """
    Get the singleton ChromaDB vector store.
    Creates or loads the persistent collection on first call.

    Returns:
        Chroma vector store instance.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name=config.CHROMA_COLLECTION_NAME,
            embedding_function=get_embedding_model(),
            persist_directory=str(config.CHROMA_DB_DIR),
        )
        count = _vector_store._collection.count()
        print(f"📦 Vector store loaded: {count} existing documents")
    return _vector_store


def add_documents(documents: List[Document]) -> None:
    """
    Add documents to the vector store.
    Embeds and persists documents to ChromaDB.

    Args:
        documents: List of LangChain Document objects (already chunked).
    """
    if not documents:
        print("⚠️  No documents to add.")
        return

    store = get_vector_store()
    store.add_documents(documents)
    count = store._collection.count()
    print(f"✅ Added {len(documents)} chunks. Total in store: {count}")


def similarity_search(query: str, k: int = None) -> List[Document]:
    """
    Search for the most relevant documents matching the query.

    Args:
        query: The search query string.
        k: Number of results to return. Defaults to config.RAG_RETRIEVAL_K.

    Returns:
        List of the top-k most relevant Document objects.
    """
    if k is None:
        k = config.RAG_RETRIEVAL_K

    store = get_vector_store()
    results = store.similarity_search(query, k=k)
    return results


def get_retriever(k: int = None):
    """
    Get a LangChain retriever wrapping the vector store.

    Equivalent to: vector_store.as_retriever(search_kwargs={"k": 3})

    Args:
        k: Number of documents to retrieve. Defaults to config.RAG_RETRIEVAL_K.

    Returns:
        A LangChain retriever instance.
    """
    if k is None:
        k = config.RAG_RETRIEVAL_K

    store = get_vector_store()
    return store.as_retriever(search_kwargs={"k": k})


def reset_vector_store() -> None:
    """
    Reset the vector store by deleting all documents.
    Use with caution — this is irreversible.
    """
    global _vector_store
    store = get_vector_store()
    store.delete_collection()
    _vector_store = None
    print("🗑️  Vector store reset. All documents deleted.")


def get_document_count() -> int:
    """Get the number of documents currently in the vector store."""
    store = get_vector_store()
    return store._collection.count()
