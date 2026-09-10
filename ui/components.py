"""Small shared render helpers — the pieces every view reuses."""

from __future__ import annotations

from typing import Any

import streamlit as st

import config
from src.llm import engine
from src.rag import stats as index_stats


def panel_header(title: str, meta: str = "") -> None:
    """The bar that opens every panel."""
    st.markdown(
        f"""
        <div class="terminal-panel-header">
            <div class="terminal-panel-title">
                <span style="color: #CDFF9A;">●</span><span>{title}</span>
            </div>
            <div class="terminal-panel-meta">{meta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hint(text: str) -> None:
    st.markdown(f'<div class="hint">{text}</div>', unsafe_allow_html=True)


def steps(items: list[tuple[str, str]]) -> None:
    """Numbered how-to cards."""
    blocks = []
    for number, (title, body) in enumerate(items, 1):
        blocks.append(
            f'<div class="step-card"><div class="step-number">{number}</div>'
            f'<div><div class="step-title">{title}</div>'
            f'<div class="step-body">{body}</div></div></div>'
        )
    st.markdown("".join(blocks), unsafe_allow_html=True)


def chips(items: list[tuple[str, str]]) -> None:
    """Row of labelled chips: (kind, label) where kind is live|doc|tool."""
    if not items:
        return
    html = "".join(f'<span class="chip chip-{kind}">{label}</span>' for kind, label in items)
    st.markdown(f'<div class="chip-row">{html}</div>', unsafe_allow_html=True)


def arrow(positive: bool | None) -> str:
    """Direction as a glyph, so colour is never the only signal of a move."""
    if positive is None:
        return ""
    return "▲" if positive else "▼"


def metric_tile(label: str, value: str, delta: str = "", positive: bool | None = None) -> None:
    colour = (
        "var(--k-lime)" if positive is True else "var(--k-orange)" if positive is False else "var(--k-text-secondary)"
    )
    mark = arrow(positive)
    delta_html = (
        f'<div style="font-family: var(--k-font-mono); font-size: 0.74rem; color: {colour};">'
        f'<span aria-hidden="true">{mark}</span> {delta}</div>'
        if delta
        else ""
    )
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def meter(value: float, tone: str = "lime") -> None:
    """A 0-100 bar."""
    width = max(0.0, min(100.0, value))
    st.markdown(
        f'<div class="meter"><div class="meter-fill meter-{tone}" style="width: {width:.0f}%;"></div></div>',
        unsafe_allow_html=True,
    )


def signal_pill(signal: str) -> str:
    upper = signal.upper()
    if "BULL" in upper:
        css = "signal-bullish"
    elif "BEAR" in upper:
        css = "signal-bearish"
    else:
        css = "signal-neutral"
    return f'<span class="signal-pill {css}">{signal}</span>'


def format_money(value: float | None, currency: str = "") -> str:
    if value is None:
        return "—"
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= threshold:
            return f"{value / threshold:,.2f}{suffix} {currency}".strip()
    return f"{value:,.2f} {currency}".strip()


def model_control(location: Any = st, key: str = "sidebar") -> bool:
    """
    Model status and the explicit load switch.

    Weights stay on disk until someone presses this button — startup is instant
    and nothing occupies memory until the user asks for reasoning.
    """
    llm = engine()
    status = llm.status()
    loaded = status["loaded"]

    dot = "#CDFF9A" if loaded else "#627C80"
    state = f"READY · {status['load_seconds']}s load" if loaded else "NOT LOADED"
    location.markdown(
        f"""
        <div style="background: rgba(32,61,67,0.4); border: 1px solid rgba(205,255,154,0.15);
                    border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;">
            <div class="metric-label">Local reasoning engine</div>
            <div style="font-family: var(--k-font-mono); font-size: 0.78rem; color: #F0F6F5; margin: 3px 0;">
                {config.LLM_MODEL.split('/')[-1]}
            </div>
            <div style="display:flex; align-items:center; gap:6px; font-family: var(--k-font-mono);
                        font-size: 0.7rem; color: {dot};">
                <span style="width:6px;height:6px;border-radius:50%;background:{dot};display:inline-block;"></span>
                {state} · MLX
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not loaded:
        if location.button("LOAD MODEL", key=f"load_model_{key}", use_container_width=True):
            with st.spinner("Loading weights into unified memory — first run takes a minute…"):
                try:
                    llm.load()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load the model: {exc}")
        location.markdown(
            '<div class="hint">Market data, retrieval and forecasts work without it. '
            'Load the model to chat and to get written analysis.</div>',
            unsafe_allow_html=True,
        )
    elif location.button("UNLOAD MODEL", key=f"unload_model_{key}", use_container_width=True):
        llm.unload()
        st.rerun()

    return loaded


def index_summary(location: Any = st) -> dict:
    """Vector-store counters, shown in the sidebar."""
    data = index_stats()
    location.markdown(
        f"""
        <div style="background: rgba(32,61,67,0.4); border: 1px solid rgba(205,255,154,0.15);
                    border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;">
            <div class="metric-label">Vector index</div>
            <div style="font-family: var(--k-font-mono); font-size: 0.78rem; color: #F0F6F5; margin: 3px 0;">
                {data['documents']} document · {data['market_feed']} live chunks
            </div>
            <div class="hint">{data['embedding_model'].split('/')[-1]} · ChromaDB</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return data


# ─── Navigation ───────────────────────────────────────────────────────────────

def nav_to(view: str, symbol: str | None = None) -> None:
    """
    Jump to another view, optionally carrying a symbol with you.

    The target is staged rather than set directly: the navigation widget has
    already been created by the time a view calls this, and Streamlit will not
    let a widget's own state be rewritten mid-run.
    """
    st.session_state["_pending_view"] = view
    if symbol:
        st.session_state["symbol"] = symbol.upper()
    st.rerun()


def apply_pending_nav() -> None:
    """Called once at the top of the app, before the navigation widget."""
    pending = st.session_state.pop("_pending_view", None)
    if pending:
        st.session_state["view"] = pending


def symbol_jump(symbol: str, label: str = "", key: str = "", view: str = "Research") -> None:
    """A button that opens a symbol in another view."""
    if st.button(label or f"Open {symbol}", key=key or f"jump_{view}_{symbol}", use_container_width=True):
        nav_to(view, symbol)


def ask_about(question: str, label: str, key: str) -> None:
    """A button that sends a ready-made question to the assistant."""
    if st.button(label, key=key, use_container_width=True):
        st.session_state["pending"] = question
        nav_to("Assistant")
