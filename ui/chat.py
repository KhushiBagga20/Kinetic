"""
Chat View — RAG-powered Q&A interface for financial document queries.

Features:
    - Chat interface with conversation history
    - Source attribution (live vs document)
    - Document upload functionality
    - Pipeline statistics display
"""

import os
import tempfile
import streamlit as st

from src.agent.agent import get_agent
from src.rag.pipeline import get_pipeline
from src.rag.vector_store import get_document_count

import config


def render_chat():
    """Render the research agent chat tab."""

    # ── Header ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="glass-card">
        <h2 style="color: #63b3ed; margin: 0;">🤖 Research Agent</h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0;">
            Ask questions about your financial documents or live market data.
            The agent automatically routes to the right data source.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Document Upload (Sidebar) ─────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📁 Document Management")

        doc_count = get_document_count()
        st.metric("Indexed Documents", f"{doc_count} chunks")

        # Upload
        uploaded_files = st.file_uploader(
            "Upload financial documents",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            key="doc_uploader",
        )

        if uploaded_files:
            if st.button("📥 Ingest Documents", key="ingest_btn"):
                pipeline = get_pipeline()
                with st.spinner("Ingesting documents..."):
                    total_chunks = 0
                    for uploaded_file in uploaded_files:
                        # Save to temp file
                        suffix = os.path.splitext(uploaded_file.name)[1]
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix
                        ) as tmp:
                            tmp.write(uploaded_file.read())
                            tmp_path = tmp.name

                        chunks = pipeline.ingest_file(tmp_path)
                        total_chunks += chunks
                        os.unlink(tmp_path)  # Clean up

                    st.success(f"✅ Ingested {total_chunks} chunks from {len(uploaded_files)} files")
                    st.rerun()

        # Ingest from directory
        if st.button("📂 Ingest from data/documents/", key="ingest_dir_btn"):
            pipeline = get_pipeline()
            with st.spinner("Ingesting all documents from data/documents/..."):
                chunks = pipeline.ingest()
                if chunks > 0:
                    st.success(f"✅ Ingested {chunks} chunks")
                else:
                    st.warning("No documents found in data/documents/")
                st.rerun()

    # ── Chat Interface ────────────────────────────────────────────────
    # Initialize session state for chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display chat history
    for msg in st.session_state.chat_messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            st.markdown(f"""
            <div class="chat-user">{content}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-assistant">{content}</div>
            """, unsafe_allow_html=True)

    # ── Chat Input ────────────────────────────────────────────────────
    user_input = st.chat_input(
        "Ask about your documents or live market data...",
        key="chat_input",
    )

    if user_input:
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input,
        })

        # Display user message
        st.markdown(f"""
        <div class="chat-user">{user_input}</div>
        """, unsafe_allow_html=True)

        # Generate response
        with st.spinner("🔍 Researching..."):
            agent = get_agent()
            response = agent.query(user_input)

        # Add assistant message
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": response,
        })

        # Display assistant message
        st.markdown(f"""
        <div class="chat-assistant">{response}</div>
        """, unsafe_allow_html=True)

        st.rerun()

    # ── Quick Actions ─────────────────────────────────────────────────
    if not st.session_state.chat_messages:
        st.markdown("### 💡 Try asking:")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📈 What's the current price of AAPL?", key="qa_1"):
                _quick_ask("What is the current stock price of AAPL?")
            if st.button("📊 Show me recent news for Tesla", key="qa_2"):
                _quick_ask("What are the recent news headlines for Tesla?")

        with col2:
            if st.button("📄 What was the revenue last quarter?", key="qa_3"):
                _quick_ask("What was the revenue in the last quarter according to the uploaded documents?")
            if st.button("🔍 Compare AAPL price to earnings report", key="qa_4"):
                _quick_ask("What is the current AAPL stock price and how does it compare to the earnings reported in the uploaded documents?")

    # ── Clear Chat ────────────────────────────────────────────────────
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Chat", key="clear_chat_btn"):
            st.session_state.chat_messages = []
            agent = get_agent()
            agent.clear_history()
            st.rerun()


def _quick_ask(question: str):
    """Handle quick action button clicks."""
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
