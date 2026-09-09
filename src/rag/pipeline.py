"""
RAG Pipeline — End-to-end retrieval-augmented generation pipeline.

Orchestrates: load → split → embed → store → retrieve → generate

Low-latency optimizations:
    1. LRU cache for repeated queries (<5ms for cache hits)
    2. Lazy initialization (models load only when first query hits)
    3. Small embedding model (all-MiniLM-L6-v2, ~14ms/query)
    4. Minimal retrieval (k=3 by default)
    5. Pre-computed embeddings persist across restarts
"""

import time
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from langchain_core.documents import Document

import config
from src.rag.document_loader import load_all_documents, load_uploaded_file
from src.rag.text_splitter import split_documents
from src.rag.vector_store import (
    add_documents,
    similarity_search,
    get_retriever,
    get_document_count,
    reset_vector_store,
)
from src.llm.model import get_llm


class RAGPipeline:
    """
    End-to-end RAG pipeline for financial document Q&A.

    Usage:
        pipeline = RAGPipeline()
        pipeline.ingest()                         # Load and index documents
        answer, sources = pipeline.query("What was the revenue in Q2?")
    """

    def __init__(self):
        self._is_initialized = False
        self._query_cache: Dict[str, Tuple[str, List[Document]]] = {}
        self._cache_max_size = 100

    def ingest(self, directory: str = None) -> int:
        """
        Ingest all documents from the data directory into the vector store.

        Steps: load files → split into chunks → embed → store in ChromaDB

        Args:
            directory: Path to documents directory. Defaults to config.DATA_DIR.

        Returns:
            Number of chunks indexed.
        """
        print("=" * 60)
        print("📥 INGESTING DOCUMENTS")
        print("=" * 60)

        start = time.time()

        # Step 1: Load documents
        print("\n[1/3] Loading documents...")
        docs = load_all_documents(directory)
        if not docs:
            print("⚠️  No documents found to ingest.")
            return 0

        # Step 2: Split into chunks
        print("\n[2/3] Splitting into chunks...")
        chunks = split_documents(docs)

        # Step 3: Embed and store
        print("\n[3/3] Embedding and storing...")
        add_documents(chunks)

        elapsed = time.time() - start
        print(f"\n✅ Ingestion complete in {elapsed:.1f}s")
        print(f"   Documents: {len(docs)} → Chunks: {len(chunks)}")
        self._is_initialized = True

        return len(chunks)

    def ingest_file(self, file_path: str) -> int:
        """
        Ingest a single uploaded file into the vector store.

        Args:
            file_path: Absolute path to the file.

        Returns:
            Number of chunks indexed.
        """
        docs = load_uploaded_file(file_path)
        chunks = split_documents(docs)
        add_documents(chunks)
        self._is_initialized = True
        return len(chunks)

    def query(
        self,
        question: str,
        k: int = None,
        use_cache: bool = True,
    ) -> Tuple[str, List[Document]]:
        """
        Query the RAG pipeline with a question.

        Args:
            question: The user's natural language question.
            k: Number of relevant documents to retrieve.
            use_cache: Whether to use the LRU cache for repeated queries.

        Returns:
            Tuple of (generated_answer, source_documents).
        """
        start = time.time()

        # Check cache first for low-latency repeated queries
        if use_cache and question in self._query_cache:
            cached = self._query_cache[question]
            print(f"⚡ Cache hit ({time.time() - start:.3f}s)")
            return cached

        # Retrieve relevant documents
        source_docs = similarity_search(question, k=k)

        if not source_docs:
            answer = (
                "I couldn't find any relevant information in the uploaded documents. "
                "Please make sure you've uploaded financial documents and try again."
            )
            return answer, []

        # Build context from retrieved documents
        context = self._build_context(source_docs)

        # Generate answer using LLM
        llm = get_llm()
        prompt = self._build_prompt(question, context)
        answer = llm.invoke(prompt)

        # Cache the result
        if use_cache:
            if len(self._query_cache) >= self._cache_max_size:
                # Evict oldest entry
                oldest_key = next(iter(self._query_cache))
                del self._query_cache[oldest_key]
            self._query_cache[question] = (answer, source_docs)

        elapsed = time.time() - start
        print(f"📊 Query completed in {elapsed:.3f}s (retrieved {len(source_docs)} docs)")

        return answer, source_docs

    def _build_context(self, documents: List[Document]) -> str:
        """Build a context string from retrieved documents."""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source_file", "unknown")
            page = doc.metadata.get("page", "N/A")
            context_parts.append(
                f"[Source {i}: {source}, Page {page}]\n{doc.page_content}"
            )
        return "\n\n---\n\n".join(context_parts)

    def _build_prompt(self, question: str, context: str) -> str:
        """Build the prompt for the LLM with retrieved context."""
        return (
            "You are a financial research assistant. Answer the question based "
            "on the provided context from financial documents. Always cite which "
            "source document the information came from. If the context doesn't "
            "contain enough information, say so clearly.\n\n"
            "Be precise with numbers — always include units (USD, INR, millions, "
            "crores, etc.) and specify the time period.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return {
            "documents_indexed": get_document_count(),
            "cache_size": len(self._query_cache),
            "cache_max_size": self._cache_max_size,
        }

    def clear_cache(self):
        """Clear the query cache."""
        self._query_cache.clear()
        print("🗑️  Query cache cleared.")


# ─── Singleton pipeline ──────────────────────────────────────────────────────

_pipeline_instance: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    """Get the singleton RAG pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance
