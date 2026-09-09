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
    page_title="Kinetic — Investment Research Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": (
            "**Kinetic** — Personal Investment Research Agent\n\n"
            "Built with Streamlit, LangChain, ChromaDB, and yfinance.\n\n"
            "This is not personalized financial advice."
        ),
    },
)

# ─── Apply Custom CSS ────────────────────────────────────────────────────────
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 16px 0;">
        <h1 style="
            background: linear-gradient(135deg, #63b3ed, #90cdf4, #bee3f8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        ">⚡ Kinetic</h1>
        <p style="color: #94a3b8; font-size: 0.85rem; margin: 4px 0 0 0;">
            Personal Investment Research Agent
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        options=["📊 Dashboard", "🤖 Research Agent", "🔮 Prediction"],
        index=0,
        key="nav_radio",
    )

    st.markdown("---")

    # Status indicators
    st.markdown("### ⚙️ System Status")

    # Check API key status
    apis = {
        "yfinance": ("✅", "No key needed"),
        "Alpha Vantage": (
            "✅" if config.ALPHA_VANTAGE_API_KEY else "⚠️",
            "Connected" if config.ALPHA_VANTAGE_API_KEY else "Key missing",
        ),
        "NewsAPI": (
            "✅" if config.NEWS_API_KEY else "⚠️",
            "Connected" if config.NEWS_API_KEY else "Key missing",
        ),
        "FMP": (
            "✅" if config.FMP_API_KEY else "ℹ️",
            "Connected" if config.FMP_API_KEY else "Optional",
        ),
    }

    for name, (icon, status) in apis.items():
        st.markdown(f"{icon} **{name}**: {status}")

    # LLM status
    st.markdown(f"🤖 **LLM**: MLX Placeholder")

    st.markdown("---")
    st.markdown(
        '<p style="color: #718096; font-size: 0.75rem; text-align: center;">'
        'Not personalized financial advice.'
        '</p>',
        unsafe_allow_html=True,
    )


# ─── Main Content Header ─────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚡ Kinetic</h1>
    <p>AI-Powered Investment Research • Live Market Data • Document Analysis</p>
</div>
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
    {config.DISCLAIMER_TEXT}
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
