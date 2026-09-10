"""
Chat — the streaming research assistant.

Every question runs the full pipeline: hybrid retrieval over the vector store,
then Gemma 4 reasoning locally with live-market tools, with the answer written
to the screen as it is generated.
"""

from __future__ import annotations

import html

import streamlit as st

import config
from src.agent import ResearchAgent
from src.llm import engine
from src.market import get_movers
from ui.components import chips, hint, model_control, panel_header, steps


def _agent() -> ResearchAgent:
    if "agent" not in st.session_state:
        st.session_state.agent = ResearchAgent()
    return st.session_state.agent


def _source_chips(passages) -> list[tuple[str, str]]:
    items = []
    for index, passage in enumerate(passages, 1):
        kind = "live" if passage.collection.endswith("market_feed") else "doc"
        items.append((kind, f"S{index} · {passage.label[:46]}"))
    return items


def _render_message(message: dict) -> None:
    if message["role"] == "user":
        st.markdown(
            f'<div class="chat-user"><div>{html.escape(message["content"])}</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="chat-assistant">', unsafe_allow_html=True)
    st.markdown(message["content"])
    st.markdown("</div>", unsafe_allow_html=True)

    used = message.get("tools", [])
    if used:
        chips([("tool", name) for name in dict.fromkeys(used)])
    if message.get("sources"):
        with st.expander(f"Retrieved context — {len(message['sources'])} passages"):
            for index, passage in enumerate(message["sources"], 1):
                st.markdown(f"**[S{index}] {passage.label}** · similarity {passage.score:.2f}")
                st.caption(passage.text[:700])
    if message.get("footer"):
        hint(message["footer"])


def _stream_answer(question: str) -> dict:
    """Run one turn, painting status, tools and tokens as they arrive."""
    status_slot = st.empty()
    chips_slot = st.empty()
    thought_slot = st.expander("Model reasoning", expanded=False)
    thought_box = thought_slot.empty()
    answer_slot = st.empty()

    answer, thought = "", ""
    tools_used: list[str] = []
    sources: list = []
    footer = ""

    for event in _agent().stream(question):
        if event.kind == "status":
            status_slot.markdown(f'<div class="hint">▸ {event.text}…</div>', unsafe_allow_html=True)

        elif event.kind == "sources":
            sources = event.data["passages"]
            with chips_slot:
                chips(_source_chips(sources) or [("doc", "no matching passages")])

        elif event.kind == "thought":
            thought += event.text
            thought_box.caption(thought)

        elif event.kind == "token":
            answer += event.text
            answer_slot.markdown(
                f'<div class="stream-answer">{html.escape(answer)}<span class="caret"></span></div>',
                unsafe_allow_html=True,
            )

        elif event.kind == "step_reset":
            answer = ""
            answer_slot.empty()

        elif event.kind == "tool_call":
            tools_used.append(event.text)
            status_slot.markdown(
                f'<div class="hint">▸ calling <code>{event.text}</code>…</div>',
                unsafe_allow_html=True,
            )

        elif event.kind == "tool_result":
            with chips_slot:
                chips(_source_chips(sources) + [("tool", name) for name in dict.fromkeys(tools_used)])

        elif event.kind == "error":
            status_slot.empty()
            st.error(event.text)
            return {"role": "assistant", "content": f"⚠️ {event.text}", "sources": [], "tools": []}

        elif event.kind == "done":
            answer = event.text or answer
            footer = (
                f"{event.data['seconds']}s · {event.data['tokens']} tokens at "
                f"{event.data['tokens_per_sec']} tok/s · {len(sources)} passages retrieved"
                + (f" · tools: {', '.join(dict.fromkeys(event.data['tools_used']))}" if event.data["tools_used"] else "")
            )

    status_slot.empty()
    answer_slot.empty()
    if not thought:
        thought_box.caption("The model answered directly, without a separate reasoning pass.")

    return {
        "role": "assistant",
        "content": answer or "_The model returned an empty response._",
        "sources": sources,
        "tools": tools_used,
        "footer": footer,
    }


def _suggestions() -> list[str]:
    """
    Prompts built from this user's own book and from what is moving right now —
    never a canned list.
    """
    from src.portfolio import load_holdings

    prompts: list[str] = []
    holdings = load_holdings()

    if holdings:
        prompts.append("How is my portfolio doing today, and which position is dragging it?")
        prompts.append(f"What is the news on {holdings[0].symbol}, and does it change anything for me?")
        prompts.append("Where is my biggest concentration risk right now?")
    for row in get_movers("most_actives", count=2):
        prompts.append(f"Why is {row['symbol']} moving today, and what do its fundamentals look like?")
    if not holdings:
        prompts.append("Summarise what my indexed documents say about revenue growth and margins.")
    return prompts[:4]


def render() -> None:
    panel_header(
        "Research assistant",
        f"RAG: HYBRID (DENSE + BM25) · ENGINE: {config.LLM_MODEL.split('/')[-1].upper()}",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not engine().is_loaded:
        left, right = st.columns([3, 1])
        with left:
            st.markdown(
                '<div class="glass-card" style="padding:18px 20px;">'
                '<div class="step-title">The reasoning model is not loaded yet</div>'
                '<div class="step-body">Kinetic runs Gemma 4 on this machine through MLX — '
                'nothing leaves your laptop. Loading takes about a minute and roughly 15 GB of '
                'unified memory. Retrieval, quotes and forecasts already work without it.</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            model_control(key="chat")

    if not st.session_state.messages:
        steps(
            [
                ("Ask in plain English", "Name a company or a ticker — <code>NVDA</code> or <code>nvidia</code>. Kinetic resolves symbols against a live search."),
                ("It retrieves first", "Your question is embedded and matched against your documents and the live market feed before the model sees it."),
                ("It calls live tools", "Quotes, fundamentals, news, screeners and the forecast engine run on demand, and every number is labelled with its source."),
            ]
        )
        st.markdown("**Try one of these — built from what is trading right now:**")
        columns = st.columns(2)
        for index, prompt in enumerate(_suggestions()):
            if columns[index % 2].button(prompt, key=f"suggest_{index}", use_container_width=True):
                st.session_state.pending = prompt
                st.rerun()

    for message in st.session_state.messages:
        _render_message(message)

    question = st.chat_input("Ask about a company, a filing, or the market…")
    if not question and st.session_state.get("pending"):
        question = st.session_state.pop("pending")

    if question:
        user_message = {"role": "user", "content": question}
        st.session_state.messages.append(user_message)
        _render_message(user_message)

        if not engine().is_loaded:
            st.warning(
                "Load the local model first — use the **LOAD MODEL** button above or in the sidebar."
            )
            st.session_state.messages.pop()
            return

        reply = _stream_answer(question)
        st.session_state.messages.append(reply)
        st.rerun()

    if st.session_state.messages:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.messages = []
            _agent().reset()
            st.rerun()
