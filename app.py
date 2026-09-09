"""
Personal Investment Research Agent — Main Streamlit Application

Entry point for the financial research agent.
Run with: streamlit run app.py

Features:
    - 📊 Live Market Dashboard (stock prices, charts, news)
    - 🤖 Research Agent (RAG Q&A with document + live data)
    - 🔮 Market Prediction Engine (ensemble technical + sentiment + fundamental)

Disclaimer: This is not personalized financial advice.
"""

import sys
from pathlib import Path

# ── Ensure project root is in path ────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

import config
from ui.styles import get_custom_css
from ui.dashboard import render_dashboard
from ui.chat import render_chat
from ui.prediction_view import render_prediction


# ─── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kinetic // Financial Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": (
            "**Kinetic** — Institutional Financial Intelligence Terminal\n\n"
            "Engine: Hybrid Ensemble (Technical 40% + Sentiment 30% + RAG Fundamentals 30%)\n\n"
            "Hardware Target: Apple Silicon (MLX Accelerated)\n\n"
            "Disclaimer: Not personalized investment advice."
        ),
    },
)

# ─── Apply Custom CSS ────────────────────────────────────────────────────────
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ─── Sidebar: System Telemetry & Utilities ───────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 6px 4px 14px 4px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="color: #CDFF9A; font-size: 1.1rem;">⚡</span>
                <span style="font-family: 'IBM Plex Sans', sans-serif; font-size: 1.15rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em;">KINETIC</span>
            </div>
            <span class="terminal-badge">DRAWER</span>
        </div>
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; color: #627C80; letter-spacing: 0.08em; text-transform: uppercase;">
            System Telemetry & Controls
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Status indicators
    st.markdown("### Provider Telemetry")

    apis = [
        ("yfinance", True, "Real-time"),
        ("Alpha Vantage", bool(config.ALPHA_VANTAGE_API_KEY), "Connected" if config.ALPHA_VANTAGE_API_KEY else "Key Unset"),
        ("NewsAPI", bool(config.NEWS_API_KEY), "Connected" if config.NEWS_API_KEY else "Key Unset"),
        ("FMP", bool(config.FMP_API_KEY), "Connected" if config.FMP_API_KEY else "Optional"),
    ]

    items_html = ""
    for name, is_active, status_text in apis:
        dot_color = "#CDFF9A" if is_active else "#627C80"
        text_color = "#CDFF9A" if is_active else "#9EB5B7"
        items_html += (
            f'<div style="display: flex; align-items: center; justify-content: space-between; '
            f'font-family: \'IBM Plex Mono\', monospace; font-size: 0.73rem; padding: 5px 8px; '
            f'background: rgba(32, 61, 67, 0.35); border-radius: 6px; border: 1px solid rgba(205, 255, 154, 0.06);">'
            f'<span style="color: #F0F6F5;">{name}</span>'
            f'<span style="display: flex; align-items: center; gap: 5px; color: {text_color}; font-weight: 500;">'
            f'<span style="width: 5px; height: 5px; border-radius: 50%; background-color: {dot_color}; display: inline-block;"></span>'
            f'{status_text}</span></div>'
        )

    telemetry_html = (
        f'<div style="display: flex; flex-direction: column; gap: 7px; margin-top: 4px;">'
        f'{items_html}'
        f'<div style="display: flex; align-items: center; justify-content: space-between; '
        f'font-family: \'IBM Plex Mono\', monospace; font-size: 0.73rem; padding: 5px 8px; '
        f'background: rgba(32, 61, 67, 0.35); border-radius: 6px; border: 1px solid rgba(205, 255, 154, 0.06); margin-top: 2px;">'
        f'<span style="color: #F0F6F5;">LLM Engine</span>'
        f'<span style="color: #CDFF9A; font-weight: 600;">MLX Apple Silicon</span>'
        f'</div></div>'
    )
    st.markdown(telemetry_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #627C80; line-height: 1.4; padding: 0 4px;">
        SEC-COMPLIANT RESEARCH PROTOCOL<br>
        NOT PERSONALIZED INVESTMENT ADVICE
    </div>
    """, unsafe_allow_html=True)


# ─── Top Institutional Navigation Bar ─────────────────────────────────────────
top_nav_container = st.container()
with top_nav_container:
    top_col1, top_col2, top_col3 = st.columns([3, 5, 3], vertical_alignment="center")

    with top_col1:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; padding: 4px 0;">
            <span style="color: #CDFF9A; font-size: 1.4rem;">⚡</span>
            <span style="font-family: 'IBM Plex Sans', sans-serif; font-size: 1.35rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em;">KINETIC</span>
            <span class="terminal-badge">v2.4-PRO</span>
        </div>
        """, unsafe_allow_html=True)

    with top_col2:
        page = st.radio(
            "Navigation",
            options=["📊 Dashboard", "🤖 Research Agent", "🔮 Prediction"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_radio",
        )

    with top_col3:
        st.markdown("""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 14px; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #627C80; padding-top: 4px;">
            <span style="display: flex; align-items: center; gap: 5px; color: #9EB5B7;">
                <span class="pulse-dot"></span>
                FEED LIVE
            </span>
            <span>LAT: <strong style="color: #CDFF9A;">&lt;15MS</strong></span>
            <span>RAG: <strong style="color: #CDFF9A;">ACTIVE</strong></span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(205, 255, 154, 0.25), transparent); margin: 6px 0 16px 0;"></div>
    """, unsafe_allow_html=True)


# ─── Page Router ─────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    render_dashboard()
elif page == "🤖 Research Agent":
    render_chat()
elif page == "🔮 Prediction":
    render_prediction()


# ─── Footer Disclaimer ───────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer-disclaimer">
    <div class="footer-tag">
        <span class="pulse-dot"></span>
        <span>KINETIC TERMINAL ARCHITECTURE // v2.4</span>
    </div>
    <div style="text-align: right; max-width: 750px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
        {config.DISCLAIMER_TEXT}
    </div>
</div>
""", unsafe_allow_html=True)


# ─── Auto-Refresh (for Dashboard) ────────────────────────────────────────────
if page == "📊 Dashboard":
    try:
        from streamlit_autorefresh import st_autorefresh
        # Auto-refresh every 2 minutes (120,000 ms)
        st_autorefresh(
            interval=config.LIVE_REFRESH_INTERVAL_SEC * 1000,
            limit=None,
            key="dashboard_autorefresh",
        )
    except ImportError:
        # streamlit-autorefresh not installed — skip auto-refresh
        pass
