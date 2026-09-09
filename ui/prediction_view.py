"""
Prediction View — market prediction reports with technical analysis charts.

Features:
    - Ticker-based prediction report generation
    - Signal badges (BULLISH/BEARISH/NEUTRAL)
    - Technical indicator breakdown
    - Sentiment analysis display
    - Prominent risk disclaimer
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

from src.prediction.ensemble import get_predictor
from src.prediction.risk import format_prediction_report, assess_risk
from src.tools.stock_lookup import get_historical_data

import config


def render_prediction():
    """Render the market prediction tab."""

    # ── Header ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="glass-card">
        <h2 style="color: #63b3ed; margin: 0;">🔮 Market Prediction Engine</h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0;">
            Multi-signal ensemble analysis combining technical indicators,
            news sentiment, and document-based fundamentals.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Disclaimer (always visible at top) ────────────────────────────
    st.markdown(f"""
    <div class="disclaimer-banner">
        {config.DISCLAIMER_TEXT}
    </div>
    """, unsafe_allow_html=True)

    # ── Ticker Input ──────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input(
            "Enter stock ticker",
            value="AAPL",
            placeholder="e.g., AAPL, GOOGL, RELIANCE.NS",
            key="prediction_ticker",
        )
    with col2:
        st.write("")
        st.write("")
        run_prediction = st.button("🚀 Run Prediction", key="run_pred_btn")

    if not ticker:
        st.info("Enter a stock ticker above to generate a prediction report.")
        return

    ticker = ticker.strip().upper()

    if run_prediction or f"pred_report_{ticker}" in st.session_state:
        # Generate or retrieve cached prediction
        if run_prediction:
            with st.spinner(f"🔍 Analyzing {ticker}... This may take a moment."):
                predictor = get_predictor()
                report = predictor.predict(ticker)
                st.session_state[f"pred_report_{ticker}"] = report
        else:
            report = st.session_state[f"pred_report_{ticker}"]

        # ── Signal Display ────────────────────────────────────────────
        _render_signal_header(report)

        # ── Detailed Breakdown ────────────────────────────────────────
        tab_overview, tab_technical, tab_sentiment, tab_fundamental = st.tabs([
            "📋 Overview", "📊 Technical", "📰 Sentiment", "📄 Fundamental"
        ])

        with tab_overview:
            _render_overview(report)

        with tab_technical:
            _render_technical_details(report, ticker)

        with tab_sentiment:
            _render_sentiment_details(report)

        with tab_fundamental:
            _render_fundamental_details(report)

        # ── Full Text Report ──────────────────────────────────────────
        with st.expander("📄 Full Text Report"):
            st.code(format_prediction_report(report), language="text")

        # ── Bottom Disclaimer ─────────────────────────────────────────
        st.markdown(f"""
        <div class="disclaimer-banner">
            {config.DISCLAIMER_TEXT}
        </div>
        """, unsafe_allow_html=True)


def _render_signal_header(report: dict):
    """Render the main signal header with badge."""
    signal = report.get("signal", "NEUTRAL")
    confidence = report.get("confidence", 0)
    risk_level = report.get("risk_level", "UNKNOWN")
    ticker = report.get("ticker", "N/A")

    # Signal badge class
    if "BULLISH" in signal:
        badge_class = "signal-bullish"
    elif "BEARISH" in signal:
        badge_class = "signal-bearish"
    else:
        badge_class = "signal-neutral"

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Signal</div>
            <div style="margin: 12px 0;">
                <span class="{badge_class}">{signal}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Confidence</div>
            <div class="metric-value">{confidence:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        risk_color = {"LOW": "#48bb78", "MEDIUM": "#ecc94b", "HIGH": "#fc8181"}.get(
            risk_level, "#a0aec0"
        )
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Risk Level</div>
            <div class="metric-value" style="color: {risk_color};">{risk_level}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_overview(report: dict):
    """Render the overview tab."""
    # Key factors
    key_factors = report.get("key_factors", [])
    if key_factors:
        st.markdown("### 📋 Key Contributing Factors")
        for i, factor in enumerate(key_factors, 1):
            st.markdown(f"**{i}.** {factor}")

    # Score breakdown gauge
    st.markdown("### ⚖️ Signal Breakdown")

    tech_score = report.get("technical", {}).get("score", 0)
    sent_score = report.get("sentiment", {}).get("score", 0)
    fund_score = report.get("fundamental", {}).get("score", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        _render_score_gauge("Technical (40%)", tech_score)
    with col2:
        _render_score_gauge("Sentiment (30%)", sent_score)
    with col3:
        _render_score_gauge("Fundamental (30%)", fund_score)

    # Risk assessment
    risk = assess_risk(report)
    risk_factors = risk.get("risk_factors", [])
    if risk_factors:
        st.markdown("### 🛡️ Risk Factors")
        for factor in risk_factors:
            st.warning(factor)


def _render_score_gauge(label: str, score: float):
    """Render a mini score gauge."""
    color = "#48bb78" if score > 0 else "#fc8181" if score < 0 else "#a0aec0"
    direction = "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color}; font-size: 1.5rem;">
            {score:+.3f}
        </div>
        <div style="color: {color}; font-size: 0.85rem;">{direction}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_technical_details(report: dict, ticker: str):
    """Render the technical analysis tab."""
    tech = report.get("technical", {})
    details = tech.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    indicators = details.get("indicators", {})

    st.markdown("### 📊 Technical Indicators")

    for name, result in indicators.items():
        if not isinstance(result, dict):
            continue

        signal = result.get("signal", 0)
        desc = result.get("description", "N/A")

        emoji = "🟢" if signal > 0 else "🔴" if signal < 0 else "⚪"
        label = name.replace("_", " ").title()

        st.markdown(f"**{emoji} {label}**: {desc}")

    # Technical chart
    st.markdown("### 📈 Technical Chart")
    try:
        data = get_historical_data(ticker, period="3mo")
        if data is not None and not data.empty:
            _render_technical_chart(data, ticker, indicators)
    except Exception as e:
        st.warning(f"Could not render technical chart: {e}")


def _render_technical_chart(data: pd.DataFrame, ticker: str, indicators: dict):
    """Render a technical analysis chart with indicators."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=[f"{ticker} Price + Bollinger Bands", "MACD", "RSI"],
    )

    # Price + Bollinger Bands
    close = data["Close"]
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20

    fig.add_trace(go.Scatter(x=data.index, y=close, name="Close",
                             line=dict(color="#63b3ed", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=upper, name="Upper BB",
                             line=dict(color="rgba(160,174,192,0.4)", dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=lower, name="Lower BB",
                             line=dict(color="rgba(160,174,192,0.4)", dash="dash"),
                             fill="tonexty", fillcolor="rgba(99,179,237,0.05)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=sma20, name="SMA 20",
                             line=dict(color="rgba(236,201,75,0.6)", width=1)), row=1, col=1)

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line

    colors = ["#48bb78" if v >= 0 else "#fc8181" for v in histogram]
    fig.add_trace(go.Bar(x=data.index, y=histogram, name="MACD Hist",
                         marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=macd_line, name="MACD",
                             line=dict(color="#63b3ed", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=signal_line, name="Signal",
                             line=dict(color="#ecc94b", width=1.5)), row=2, col=1)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta).where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    fig.add_trace(go.Scatter(x=data.index, y=rsi, name="RSI",
                             line=dict(color="#b794f4", width=2)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(252,129,129,0.5)",
                  annotation_text="Overbought", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(72,187,120,0.5)",
                  annotation_text="Oversold", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#94a3b8"),
        height=700,
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=20),
    )

    fig.update_xaxes(gridcolor="rgba(255,255,255,0.03)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.03)")

    st.plotly_chart(fig, use_container_width=True)


def _render_sentiment_details(report: dict):
    """Render the sentiment analysis tab."""
    sent = report.get("sentiment", {})
    details = sent.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    score = sent.get("score", 0)
    desc = details.get("description", "N/A")
    compound = details.get("aggregate_compound", 0)

    st.markdown("### 📰 News Sentiment Analysis")
    st.markdown(f"**Overall:** {desc}")
    st.markdown(f"**Aggregate Compound Score:** `{compound:+.4f}`")

    # Individual headlines
    individual = details.get("individual", [])
    if individual:
        st.markdown("### 📝 Headline Sentiment Breakdown")
        for item in individual:
            headline = item.get("headline", "N/A")
            compound_score = item.get("compound", 0)

            if compound_score > 0.1:
                emoji = "🟢"
            elif compound_score < -0.1:
                emoji = "🔴"
            else:
                emoji = "⚪"

            st.markdown(f"{emoji} **{compound_score:+.3f}** — {headline}")
    else:
        st.info("No individual headline data available.")


def _render_fundamental_details(report: dict):
    """Render the fundamental analysis tab."""
    fund = report.get("fundamental", {})
    details = fund.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    score = fund.get("score", 0)
    desc = details.get("description", "N/A")
    doc_count = details.get("documents_found", 0)
    sources = details.get("sources", [])

    st.markdown("### 📄 Fundamental Analysis (from Documents)")

    if doc_count == 0:
        st.info(
            "No relevant documents found. Upload financial documents "
            "(annual reports, fact sheets) to enable fundamental analysis."
        )
        return

    st.markdown(f"**Documents analyzed:** {doc_count} chunks")
    st.markdown(f"**Fundamental score:** `{score:+.3f}`")
    st.markdown(f"**Assessment:** {desc}")

    if sources:
        st.markdown("**Source files:**")
        unique_sources = list(set(sources))
        for src in unique_sources:
            st.markdown(f"  - 📁 {src}")
