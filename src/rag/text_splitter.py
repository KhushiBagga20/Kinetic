"""
Text Splitter — splits financial documents into chunks for embedding.

Financial documents have special considerations:
    - Tables with numbers must stay intact (not split mid-row)
    - Headers/labels must stay attached to their values
    - Dense numeric sections need careful boundary handling

chunk_size=800 and chunk_overlap=200 are tuned for financial content:
    - 800 chars captures most table rows and paragraph blocks
    - 200 char overlap ensures numbers don't lose their labels at boundaries
"""

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import config


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """
    Create a text splitter optimized for financial documents.

    Uses RecursiveCharacterTextSplitter with separators ordered to prefer
    splitting at paragraph/section boundaries before falling back to
    sentence or word boundaries.

    Returns:
        Configured RecursiveCharacterTextSplitter instance.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=config.RAG_CHUNK_SIZE,
        chunk_overlap=config.RAG_CHUNK_OVERLAP,
        length_function=len,
        separators=[
            "\n\n\n",   # Triple newline — major section breaks
            "\n\n",      # Double newline — paragraph breaks
            "\n",        # Single newline — line breaks (careful with tables)
            ". ",        # Sentence boundaries
            ", ",        # Clause boundaries
            " ",         # Word boundaries (last resort)
            "",          # Character-level (emergency fallback)
        ],
        is_separator_regex=False,
    )


def split_documents(documents: List[Document]) -> List[Document]:
    """
    Split a list of documents into smaller chunks for embedding.

    Each chunk preserves the original document's metadata and adds
    a chunk_index for tracking position within the source document.

    Args:
        documents: List of LangChain Document objects to split.

    Returns:
        List of chunked Document objects with preserved metadata.
    """
    if not documents:
        return []

    splitter = get_text_splitter()
    chunks = splitter.split_documents(documents)

    # Add chunk index metadata for traceability
    source_chunk_counts = {}
    for chunk in chunks:
        source = chunk.metadata.get("source_file", "unknown")
        if source not in source_chunk_counts:
            source_chunk_counts[source] = 0
        chunk.metadata["chunk_index"] = source_chunk_counts[source]
        source_chunk_counts[source] += 1

    print(f"📝 Split {len(documents)} documents into {len(chunks)} chunks")
    print(f"   Avg chunk size: {sum(len(c.page_content) for c in chunks) // max(len(chunks), 1)} chars")

    return chunks
