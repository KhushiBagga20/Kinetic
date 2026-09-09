"""
Document Loader — loads financial documents (PDFs, text files) for the RAG pipeline.

Supports:
    - PDF files (.pdf) via PyPDFLoader
    - Text files (.txt) via TextLoader
    - Batch loading from the data/documents/ directory
"""

import os
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

import config


# ─── Supported file extensions and their loaders ─────────────────────────────
LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
}


def load_single_document(file_path: str) -> List[Document]:
    """
    Load a single document file and return a list of Document objects.

    Args:
        file_path: Absolute path to the document file.

    Returns:
        List of LangChain Document objects with page content and metadata.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = Path(file_path).suffix.lower()
    if ext not in LOADER_MAP:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported types: {list(LOADER_MAP.keys())}"
        )

    loader_cls = LOADER_MAP[ext]
    loader = loader_cls(file_path)
    docs = loader.load()

    # Enrich metadata with source filename
    for doc in docs:
        doc.metadata["source_file"] = Path(file_path).name
        doc.metadata["source_type"] = "static_document"

    return docs


def load_all_documents(directory: str = None) -> List[Document]:
    """
    Load all supported documents from the specified directory.

    Args:
        directory: Path to the documents directory.
                   Defaults to config.DATA_DIR.

    Returns:
        List of all Document objects from all files in the directory.
    """
    if directory is None:
        directory = str(config.DATA_DIR)

    all_docs: List[Document] = []
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"⚠️  Documents directory does not exist: {directory}")
        return all_docs

    supported_files = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in LOADER_MAP
    ]

    if not supported_files:
        print(f"ℹ️  No supported documents found in: {directory}")
        return all_docs

    for file_path in sorted(supported_files):
        try:
            docs = load_single_document(str(file_path))
            all_docs.extend(docs)
            print(f"  ✅ Loaded: {file_path.name} ({len(docs)} pages/chunks)")
        except Exception as e:
            print(f"  ❌ Failed to load {file_path.name}: {e}")

    print(f"\n📄 Total documents loaded: {len(all_docs)} from {len(supported_files)} files")
    return all_docs


def load_uploaded_file(file_path: str) -> List[Document]:
    """
    Load a single uploaded file (e.g., from Streamlit file_uploader).
    Convenience wrapper around load_single_document.

    Args:
        file_path: Path to the uploaded file (saved to disk).

    Returns:
        List of Document objects.
    """
    return load_single_document(file_path)
