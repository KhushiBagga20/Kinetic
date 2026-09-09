"""
Chat View — Institutional Financial Research Analyst Workstation.

Features:
    - Analyst terminal workstation interface (structured query/synthesis logs)
    - Vector index and document management in sidebar
    - Automated query routing (live market lookup, document RAG, macro news)
    - Precision quick-action query prompts
"""

import os
import tempfile
from textwrap import dedent
import streamlit as st

from src.agent.agent import get_agent
from src.rag.pipeline import get_pipeline
from src.rag.vector_store import get_document_count
import config


def render_chat():
    """Render the institutional research agent workstation tab."""

    # ── Header Bar ────────────────────────────────────────────────────
    st.markdown("""
    <div class="terminal-panel-header" style="margin-top: 4px;">
        <div class="terminal-panel-title">
            <span style="color: #CDFF9A;">●</span>
            <span>Institutional Research Agent // Workstation</span>
        </div>
        <div class="terminal-panel-meta">
            ROUTER: MULTI-TOOL HYBRID // VECTOR STORE: CHROMADB // LLM: MLX
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar Document Management ───────────────────────────────────
    with st.sidebar:
        st.markdown("### Document & Vector Index")

        doc_count = get_document_count()
        st.markdown(dedent(f"""
        <div style="background: rgba(32, 61, 67, 0.4); border: 1px solid rgba(205, 255, 154, 0.15); border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;">
            <div style="font-family: 'IBM Plex Sans', sans-serif; font-size: 0.70rem; color: #627C80; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">Indexed Corpus</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #CDFF9A; margin: 4px 0;">{doc_count} <span style="font-size: 0.75rem; color: #9EB5B7; font-weight: 400;">chunks</span></div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #627C80;">EMBEDDINGS: all-MiniLM-L6-v2</div>
        </div>
        """), unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Upload 10-K, 10-Q, Pitch Books (PDF/TXT)",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            key="doc_uploader",
        )

        if uploaded_files:
            if st.button("📥 INGEST TO VECTOR STORE", key="ingest_btn"):
                pipeline = get_pipeline()
                with st.spinner("Embedding and indexing documents..."):
                    total_chunks = 0
                    for uploaded_file in uploaded_files:
                        suffix = os.path.splitext(uploaded_file.name)[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(uploaded_file.read())
                            tmp_path = tmp.name

                        chunks = pipeline.ingest_file(tmp_path)
                        total_chunks += chunks
                        os.unlink(tmp_path)

                    st.success(f"Indexed {total_chunks} chunks from {len(uploaded_files)} file(s).")
                    st.rerun()

        if st.button("📂 INGEST DATA/DOCUMENTS/ CORPUS", key="ingest_dir_btn"):
            pipeline = get_pipeline()
            with st.spinner("Ingesting directory documents..."):
                chunks = pipeline.ingest()
                if chunks > 0:
                    st.success(f"Indexed {chunks} chunks from disk.")
                else:
                    st.warning("No documents found in data/documents/")
                st.rerun()

    # ── Chat Session Initialization ───────────────────────────────────
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ── Quick Action Command Prompts (Empty State) ─────────────────────
    if not st.session_state.chat_messages:
        st.markdown("""
        <div class="glass-card" style="padding: 24px; text-align: left; margin: 16px 0;">
            <div style="font-family: 'IBM Plex Sans', sans-serif; font-size: 1.1rem; font-weight: 600; color: #FFFFFF; margin-bottom: 6px;">
                Financial Analyst Terminal Ready
            </div>
            <p style="color: #9EB5B7; font-size: 0.88rem; margin: 0 0 16px 0; line-height: 1.5;">
                Ask institutional research questions spanning live stock quotes, fundamental financial statements, SEC filings from your vector store, or macro news headlines.
            </p>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #627C80; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.08em;">
                Sample Intelligence Inquiries:
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ [QUOTE] Current Valuation & Day Metrics: AAPL", key="qa_1"):
                _quick_ask("What is the current stock price, volume, and daily movement for AAPL?")
            if st.button("📰 [WIRE] Recent News Sentiment & Catalysts: NVDA", key="qa_2"):
                _quick_ask("What are the recent news headlines and key catalysts for Nvidia (NVDA)?")

        with col2:
            if st.button("📄 [FILINGS] Review Uploaded Documents for Revenue Trends", key="qa_3"):
                _quick_ask("What was the revenue and margin performance in the latest quarter according to our indexed documents?")
            if st.button("🔍 [SYNTHESIS] Compare Live Price vs Document Guidance", key="qa_4"):
                _quick_ask("Analyze the current price of Microsoft (MSFT) and synthesize it with the financial guidance mentioned in uploaded documents.")

    # ── Chat History Log ──────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            st.markdown(dedent(f"""
            <div class="chat-user">
                <div>{content}</div>
            </div>
            """), unsafe_allow_html=True)
        else:
            st.markdown(dedent(f"""
            <div class="chat-assistant">
                <div style="color: #EAF2F1; font-family: var(--k-font-sans);">{content}</div>
            </div>
            """), unsafe_allow_html=True)

    # ── Chat Input ────────────────────────────────────────────────────
    user_input = st.chat_input(
        "Enter financial research query or ticker inquiry...",
        key="chat_input",
    )

    if user_input:
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input,
        })

        with st.spinner("⚙️ Accessing market feeds and vector indices..."):
            agent = get_agent()
            response = agent.query(user_input)

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": response,
        })
        st.rerun()

    # ── Workspace Utilities ───────────────────────────────────────────
    if st.session_state.chat_messages:
        c_clear, _ = st.columns([1, 4])
        with c_clear:
            if st.button("🗑️ RESET SESSION", key="clear_chat_btn"):
                st.session_state.chat_messages = []
                agent = get_agent()
                agent.clear_history()
                st.rerun()


def _quick_ask(question: str):
    """Execute a predefined analyst query."""
    st.session_state.chat_messages.append({
        "role": "user",
        "content": question,
    })

    agent = get_agent()
    response = agent.query(question)

    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": response,
    })
    st.rerun()
