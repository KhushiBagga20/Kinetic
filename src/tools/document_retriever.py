"""
Document Retriever Tool — retrieves relevant financial document chunks via RAG.

Wraps the RAG pipeline's vector store retriever as a LangChain @tool.
Returns source-attributed document chunks with metadata.
"""

from langchain_core.tools import tool

from src.rag.vector_store import similarity_search, get_document_count


@tool
def retrieve_financial_docs(query: str) -> str:
    """
    Retrieve relevant information from uploaded financial documents.

    Use this tool when the user asks about information that would be found
    in financial documents like annual reports (10-K), mutual fund fact sheets,
    earnings reports, or investing guides that have been previously uploaded.

    This searches through the document database using semantic similarity
    to find the most relevant sections.

    Args:
        query: A natural language question about financial document content.
               Examples: "What was the revenue in Q2?",
                        "What is the expense ratio of the fund?",
                        "What are the key risk factors?"

    Returns:
        The top 3 most relevant document excerpts with source attribution.
        Each excerpt includes the source filename and page number.
        Data source is always stated (static document / uploaded file).

    Note:
        - Numbers are returned exactly as they appear in the documents
        - Currency units (USD, INR, etc.) are preserved from the source
        - Values are in the units specified in the document (millions, crores, etc.)
    """
    doc_count = get_document_count()
    if doc_count == 0:
        return (
            "📄 No financial documents have been uploaded yet.\n"
            "Please upload documents (PDF or text files) through the UI "
            "or place them in the data/documents/ directory and run ingestion."
        )

    # Retrieve relevant chunks
    results = similarity_search(query, k=3)

    if not results:
        return (
            f"📄 No relevant information found in the {doc_count} indexed "
            f"document chunks for: '{query}'.\n"
            "Try rephrasing your question or uploading more relevant documents."
        )

    # Format results with source attribution
    lines = [
        f"📄 Document Search Results (from {doc_count} indexed chunks)",
        f"   Query: '{query}'",
        "",
    ]

    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source_file", "Unknown file")
        page = doc.metadata.get("page", "N/A")
        chunk_idx = doc.metadata.get("chunk_index", "N/A")

        lines.extend([
            f"  ── Result {i} ──",
            f"  📁 Source: {source} (Page {page}, Chunk {chunk_idx})",
            f"  📊 Data type: Static document (uploaded file)",
            f"  Content:",
            f"  {doc.page_content[:500]}",
            "",
        ])

    lines.append("  📡 Source: Static financial documents (not live market data)")

    return "\n".join(lines)
