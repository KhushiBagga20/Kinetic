"""
Knowledge — managing and inspecting the RAG corpus.

This view makes the retrieval pipeline visible: what is indexed, how it was
chunked, and exactly which passages a query brings back with what scores.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

import config
from src.market import resolve_symbol
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
from src.rag.ingest import SUPPORTED_SUFFIXES
from ui.components import chips, hint, metric_tile, panel_header, steps


def _ingest_uploads(files) -> None:
    total = 0
    for upload in files:
        suffix = Path(upload.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(upload.read())
            temporary = handle.name
        try:
            total += ingest_file(temporary, source_name=upload.name)
        except Exception as exc:
            st.error(f"{upload.name}: {exc}")
        finally:
            Path(temporary).unlink(missing_ok=True)
    if total:
        st.success(f"Indexed {total} chunks from {len(files)} file(s).")
        st.rerun()


def render() -> None:
    counts = stats()
    panel_header(
        "Knowledge base",
        f"CHROMADB · {counts['embedding_model'].split('/')[-1]} · "
        f"CHUNK {config.CHUNK_SIZE}/{config.CHUNK_OVERLAP}",
    )

    columns = st.columns(4)
    with columns[0]:
        metric_tile("Document chunks", f"{counts['documents']:,}")
    with columns[1]:
        metric_tile("Live market chunks", f"{counts['market_feed']:,}")
    with columns[2]:
        metric_tile("Retrieval", f"top {config.RETRIEVAL_K}")
    with columns[3]:
        metric_tile("Fusion", "dense + BM25")

    if counts["documents"] == 0 and counts["market_feed"] == 0:
        steps(
            [
                ("Add your documents", "Upload annual reports, fund fact sheets or your own notes below — PDF, TXT, MD, CSV or HTML."),
                ("Or capture the live market", "Snapshot a symbol's quote, fundamentals and headlines straight into the index."),
                ("Then ask questions", "The assistant searches this index before every answer and cites what it used."),
            ]
        )

    upload_tab, live_tab, browse_tab, test_tab = st.tabs(
        ["Add documents", "Capture live data", "Indexed sources", "Test retrieval"]
    )

    with upload_tab:
        files = st.file_uploader(
            "Drop financial documents here",
            type=[suffix.lstrip(".") for suffix in sorted(SUPPORTED_SUFFIXES)],
            accept_multiple_files=True,
        )
        if files and st.button("Ingest uploads", type="primary"):
            with st.spinner("Chunking, embedding and indexing…"):
                _ingest_uploads(files)

        hint(
            f"Files placed in <code>{config.DOCUMENTS_DIR}</code> can be indexed in one go. "
            "Re-ingesting a file replaces its old chunks rather than duplicating them."
        )
        if st.button("Ingest the documents folder"):
            with st.spinner("Reading the documents folder…"):
                result = ingest_directory()
            if not result:
                st.warning(f"No supported files found in {config.DOCUMENTS_DIR}")
            else:
                for name, chunks in result.items():
                    st.write(f"- **{name}** → {chunks} chunks")
                st.rerun()

    with live_tab:
        st.markdown(
            "Capturing a symbol writes its live quote, fundamentals and recent headlines into "
            "the vector store, each stamped with the time it was fetched. That is what lets the "
            "assistant retrieve *current* evidence rather than only static filings."
        )
        symbol_column, button_column = st.columns([3, 1], vertical_alignment="bottom")
        with symbol_column:
            query = st.text_input("Symbol or company to capture", value=st.session_state.get("symbol", config.DEFAULT_SYMBOL))
        with button_column:
            capture = st.button("Capture", use_container_width=True, type="primary")
        if capture:
            symbol = resolve_symbol(query)
            if not symbol:
                st.warning(f"No instrument found for “{query}”.")
            else:
                with st.spinner(f"Fetching and indexing live data for {symbol}…"):
                    written = ingest_market_feed(symbol)
                if written:
                    st.success(f"Indexed {written} passages for {symbol}.")
                    st.rerun()
                else:
                    st.warning(f"No live data could be captured for {symbol}.")

    with browse_tab:
        rows = sources()
        if not rows:
            hint("Nothing indexed yet.")
        for row in rows:
            source_column, count_column, delete_column = st.columns([5, 2, 1], vertical_alignment="center")
            source_column.markdown(f"**{row['source']}**")
            count_column.markdown(
                f'<span class="hint">{row["chunks"]} chunks · {row.get("ingested", "")}</span>',
                unsafe_allow_html=True,
            )
            if delete_column.button("Remove", key=f"del_{row['source']}"):
                delete_source(row["source"])
                st.rerun()

        st.markdown("---")
        if st.button("Reset the entire index"):
            reset()
            st.warning("Index cleared.")
            st.rerun()

    with test_tab:
        st.markdown(
            "Run a query through the retriever alone — no model involved. This is the "
            "fastest way to check whether a number is actually retrievable before asking about it."
        )
        query = st.text_input("Retrieval query", placeholder="e.g. operating margin fiscal 2024")
        if query:
            passages, elapsed = search_with_timing(query)
            chips([("live", f"{len(passages)} passages in {elapsed:.0f} ms")])
            if not passages:
                st.warning("Nothing matched. Try different wording, or index more documents.")
            for index, passage in enumerate(passages, 1):
                kind = "live market feed" if passage.collection.endswith("market_feed") else "document"
                st.markdown(f"**[S{index}] {passage.label}** · {kind} · similarity {passage.score:.3f}")
                st.caption(passage.text[:900])
