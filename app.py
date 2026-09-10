"""
Kinetic — local-first investment research terminal.

    streamlit run app.py

Five views, ordered by how often they are used rather than by architecture:
Home (your book), Portfolio, Research (market + forecast), Assistant, Knowledge.
Market data is fetched live on every render; reasoning runs on this machine.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

import config
from src import preferences
from src.market import resolve_symbol
from ui import chat, home, knowledge, portfolio, research
from ui.components import apply_pending_nav, index_summary, model_control
from ui.theme import get_custom_css

VIEWS = {
    "Home": home.render,
    "Portfolio": portfolio.render,
    "Research": research.render,
    "Assistant": chat.render,
    "Knowledge": knowledge.render,
}

st.set_page_config(
    page_title="Kinetic — investment research terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": f"{config.APP_NAME} — {config.APP_TAGLINE}\n\n{config.DISCLAIMER}"},
)

prefs = preferences.load()
st.markdown(
    get_custom_css(
        text_scale=preferences.TEXT_SIZES.get(prefs.text_size, 1.0),
        high_contrast=prefs.high_contrast,
        reduce_motion=prefs.reduce_motion,
    ),
    unsafe_allow_html=True,
)

# A view may have asked to navigate elsewhere; apply it before the nav widget.
apply_pending_nav()


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style="padding: 4px 2px 12px 2px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="color:#CDFF9A; font-size:1.2rem;" aria-hidden="true">⚡</span>
                <span style="font-family:'IBM Plex Sans'; font-size:1.2rem; font-weight:700;
                             color:#FFFFFF; letter-spacing:-0.02em;">KINETIC</span>
            </div>
            <div class="hint" style="margin-top:4px;">
                {('Signed in as ' + prefs.name) if prefs.name else 'Local-first investment research'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    model_control()
    index_summary()

    # -- watchlist: one click to any symbol, from anywhere --------------------
    with st.expander("Watchlist", expanded=bool(prefs.watchlist)):
        for symbol in prefs.watchlist:
            open_column, remove_column = st.columns([3, 1])
            if open_column.button(symbol, key=f"side_open_{symbol}", use_container_width=True):
                st.session_state["symbol"] = symbol
                st.session_state["_pending_view"] = "Research"
                st.rerun()
            if remove_column.button("✕", key=f"side_rm_{symbol}", help=f"Remove {symbol}"):
                preferences.remove_from_watchlist(symbol)
                st.rerun()

        new_symbol = st.text_input("Add a symbol or company", key="watch_add",
                                   placeholder="e.g. infosys")
        if new_symbol:
            resolved = resolve_symbol(new_symbol)
            if resolved:
                preferences.add_to_watchlist(resolved)
                st.rerun()
            else:
                st.warning(f"No instrument found for “{new_symbol}”.")

    # -- profile: what makes the answers personal -----------------------------
    with st.expander("Your profile"):
        name = st.text_input("Name", value=prefs.name)
        currency = st.text_input("Base currency", value=prefs.base_currency,
                                 help="Everything is converted into this using a live FX rate.")
        horizon = st.selectbox("Investing horizon", preferences.HORIZONS,
                               index=preferences.HORIZONS.index(prefs.horizon))
        appetite = st.selectbox("Risk appetite", preferences.RISK_APPETITES,
                                index=preferences.RISK_APPETITES.index(prefs.risk_appetite))
        if st.button("Save profile", use_container_width=True):
            preferences.update(
                name=name,
                base_currency=currency.upper()[:3],
                horizon=horizon,
                risk_appetite=appetite,
            )
            st.rerun()
        st.markdown('<div class="hint">Stored on this machine only.</div>', unsafe_allow_html=True)

    # -- accessibility --------------------------------------------------------
    with st.expander("Display & accessibility"):
        size = st.radio("Text size", list(preferences.TEXT_SIZES),
                        index=list(preferences.TEXT_SIZES).index(prefs.text_size),
                        horizontal=True)
        contrast = st.toggle("High contrast", value=prefs.high_contrast,
                             help="Raises text and border contrast against the dark canvas.")
        motion = st.toggle("Reduce motion", value=prefs.reduce_motion,
                           help="Stops pulsing and blinking indicators.")
        if (size, contrast, motion) != (prefs.text_size, prefs.high_contrast, prefs.reduce_motion):
            preferences.update(text_size=size, high_contrast=contrast, reduce_motion=motion)
            st.rerun()

    st.markdown("---")
    auto_refresh = st.toggle(
        "Auto-refresh market data",
        value=False,
        help=f"Re-runs the current view every {config.AUTO_REFRESH_SEC}s to pull fresh quotes.",
    )


# ─── Top bar ──────────────────────────────────────────────────────────────────
title_column, nav_column, status_column = st.columns([2, 6, 2], vertical_alignment="center")

with title_column:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:8px; padding:4px 0;">
            <span style="color:#CDFF9A; font-size:1.35rem;" aria-hidden="true">⚡</span>
            <span style="font-family:'IBM Plex Sans'; font-size:1.3rem; font-weight:700;
                         color:#FFFFFF; letter-spacing:-0.02em;">KINETIC</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav_column:
    view = st.radio(
        "Main navigation",
        options=list(VIEWS),
        index=list(VIEWS).index(st.session_state.get("view", "Home")),
        horizontal=True,
        label_visibility="collapsed",
        key="view",
    )

with status_column:
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:flex-end; gap:12px;
                    font-family:'IBM Plex Mono'; font-size:0.72rem; color:#9EB5B7; padding-top:4px;">
            <span style="display:flex; align-items:center; gap:5px;">
                <span class="pulse-dot" aria-hidden="true"></span>LIVE
            </span>
            <span>ON-DEVICE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    '<div style="height:1px; background:linear-gradient(90deg, transparent, '
    'rgba(205,255,154,0.25), transparent); margin:6px 0 16px 0;"></div>',
    unsafe_allow_html=True,
)


# ─── View ─────────────────────────────────────────────────────────────────────
VIEWS[view]()


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="footer-disclaimer">
        <div class="footer-tag"><span class="pulse-dot" aria-hidden="true"></span>
            <span>KINETIC · RUNS ENTIRELY ON THIS MACHINE</span></div>
        <div style="text-align:right; max-width:760px; overflow:hidden; text-overflow:ellipsis;
                    white-space:nowrap;">{config.DISCLAIMER}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(interval=config.AUTO_REFRESH_SEC * 1000, key="market_autorefresh")
    except ImportError:
        pass
