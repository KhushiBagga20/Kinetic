"""
Prediction View — Quantitative Multi-Signal Ensemble Prediction Engine.

Features:
    - Multi-signal algorithmic prediction (Technical 40% + Sentiment 30% + Fundamental 30%)
    - Institutional signal cards (BULLISH/BEARISH/NEUTRAL) with confidence and risk meters
    - Technical indicator breakdown matrix with 3-panel Plotly charting
    - News sentiment analysis with compound scoring
    - Document-backed fundamental verification
    - Institutional risk assessment and SEC-compliant disclaimer
"""

from textwrap import dedent
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from src.prediction.ensemble import get_predictor
from src.prediction.risk import format_prediction_report, assess_risk
from src.tools.stock_lookup import get_historical_data
import config


def _md(html: str):
    """Render HTML cleanly without CommonMark indentation bugs."""
    st.markdown(dedent(html), unsafe_allow_html=True)


def render_prediction():
    """Render the quantitative market prediction tab."""

    # ── Section Header ────────────────────────────────────────────────
    _md("""
    <div class="terminal-panel-header" style="margin-top: 4px;">
        <div class="terminal-panel-title">
            <span style="color: #CDFF9A;">●</span>
            <span>Quantitative Prediction Engine // Multi-Signal Ensemble</span>
        </div>
        <div class="terminal-panel-meta">
            WEIGHTS: TECH (40%) • SENTIMENT (30%) • FUNDAMENTALS (30%)
        </div>
    </div>
    """)

    # ── Disclaimer Banner ─────────────────────────────────────────────
    _md(f"""
    <div class="disclaimer-banner">
        <div>
            <strong>CRITICAL RISK NOTICE:</strong> {config.DISCLAIMER_TEXT}
        </div>
    </div>
    """)

    # ── Ticker Command Bar ────────────────────────────────────
    col1, col2 = st.columns([4, 1])
    with col1:
        ticker = st.text_input(
            "Target Equity Symbol",
            value="AAPL",
            placeholder="e.g. AAPL, NVDA, TSLA, MSFT",
            key="prediction_ticker",
            label_visibility="collapsed",
        )
    with col2:
        run_prediction = st.button("⚡ EXECUTE MODEL", key="run_pred_btn")

    # Quick Ticker Shortcuts
    _md("""
    <div style="display: flex; align-items: center; gap: 8px; margin: -6px 0 16px 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #627C80;">
        <span>SUGGESTED TARGETS:</span>
        <span style="color: #9EB5B7;">AAPL</span> •
        <span style="color: #9EB5B7;">NVDA</span> •
        <span style="color: #9EB5B7;">MSFT</span> •
        <span style="color: #9EB5B7;">TSLA</span>
    </div>
    """)

    if not ticker:
        st.info("Enter an equity ticker to execute the ensemble model.")
        return

    ticker = ticker.strip().upper()

    if run_prediction or f"pred_report_{ticker}" in st.session_state:
        if run_prediction:
            with st.spinner(f"Running quantitative synthesis for {ticker}..."):
                predictor = get_predictor()
                report = predictor.predict(ticker)
                st.session_state[f"pred_report_{ticker}"] = report
        else:
            report = st.session_state[f"pred_report_{ticker}"]

        # ── Primary Signal & Metric Dashboard ─────────────────────────
        _render_signal_header(report)

        # ── Analytical Deep Dive Tabs ─────────────────────────────────
        tab_overview, tab_technical, tab_sentiment, tab_fundamental = st.tabs([
            "📋 ENSEMBLE SYNTHESIS",
            "📊 TECHNICAL MATRIX",
            "📰 SENTIMENT INTELLIGENCE",
            "📄 FUNDAMENTAL AUDIT",
        ])

        with tab_overview:
            _render_overview(report)

        with tab_technical:
            _render_technical_details(report, ticker)

        with tab_sentiment:
            _render_sentiment_details(report)

        with tab_fundamental:
            _render_fundamental_details(report)

        # ── Full Monospace Report Expander ────────────────────────────
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        with st.expander("📄 VIEW INSTITUTIONAL RAW TELEMETRY REPORT"):
            st.code(format_prediction_report(report), language="text")

        # ── Bottom Compliance Banner ──────────────────────────────────
        _md("""
        <div class="disclaimer-banner" style="margin-top: 24px;">
            <div>
                <strong>COMPLIANCE MEMORANDUM:</strong> Algorithmic market forecasts are probabilistic models and carry intrinsic financial variance. Past indicator correlations do not guarantee future performance.
            </div>
        </div>
        """)


def _render_signal_header(report: dict):
    """Render the primary signal telemetry header with institutional meters."""
    signal = report.get("signal", "NEUTRAL").upper()
    confidence = report.get("confidence", 0)
    risk_level = report.get("risk_level", "UNKNOWN").upper()
    ticker = report.get("ticker", "N/A")

    is_bullish = "BULLISH" in signal
    is_bearish = "BEARISH" in signal

    if is_bullish:
        signal_color = "#CDFF9A"
        signal_bg = "rgba(205, 255, 154, 0.12)"
        signal_border = "#CDFF9A"
        signal_dot = "▲"
    elif is_bearish:
        signal_color = "#DF4100"
        signal_bg = "rgba(223, 65, 0, 0.12)"
        signal_border = "#DF4100"
        signal_dot = "▼"
    else:
        signal_color = "#9EB5B7"
        signal_bg = "rgba(158, 181, 183, 0.12)"
        signal_border = "rgba(158, 181, 183, 0.4)"
        signal_dot = "■"

    risk_color = {
        "LOW": "#CDFF9A",
        "MEDIUM": "#9EB5B7",
        "HIGH": "#DF4100",
    }.get(risk_level, "#9EB5B7")

    col1, col2, col3 = st.columns(3)

    with col1:
        _md(f"""
        <div class="metric-card" style="border-top: 3px solid {signal_color};">
            <div class="metric-label">Ensemble Output Signal</div>
            <div style="margin: 10px 0;">
                <span class="signal-pill" style="background: {signal_bg}; border: 1px solid {signal_border}; color: {signal_color};">
                    <span>{signal_dot}</span>
                    <span>{signal}</span>
                </span>
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80;">TARGET: {ticker} // HORIZON: 5-30 DAYS</div>
        </div>
        """)

    with col2:
        _md(f"""
        <div class="metric-card" style="border-top: 3px solid #CDFF9A;">
            <div class="metric-label">Model Confidence Rating</div>
            <div class="metric-value" style="color: #CDFF9A;">{confidence:.1f}%</div>
            <div style="background: rgba(205, 255, 154, 0.1); border-radius: 4px; height: 4px; width: 100%; margin-top: 8px; overflow: hidden;">
                <div style="background: #CDFF9A; height: 100%; width: {min(max(confidence, 0), 100)}%;"></div>
            </div>
        </div>
        """)

    with col3:
        _md(f"""
        <div class="metric-card" style="border-top: 3px solid {risk_color};">
            <div class="metric-label">Calculated Volatility Risk</div>
            <div class="metric-value" style="color: {risk_color};">{risk_level}</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80; margin-top: 6px;">
                EVALUATED BY RISK ENGINE
            </div>
        </div>
        """)


def _render_overview(report: dict):
    """Render the overview tab with factor analysis and component gauges."""
    col_factors, col_breakdown = st.columns([5, 4])

    with col_factors:
        _md("""
        <div class="terminal-panel" style="height: 100%;">
            <div class="terminal-panel-header">
                <div class="terminal-panel-title">Key Determinant Factors</div>
                <div class="terminal-panel-meta">PRIMARY ATTRIBUTION</div>
            </div>
        """)

        key_factors = report.get("key_factors", [])
        if key_factors:
            for i, factor in enumerate(key_factors, 1):
                _md(f"""
                <div style="display: flex; gap: 10px; margin-bottom: 10px; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.88rem; line-height: 1.45;">
                    <span style="font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; color: #CDFF9A; font-weight: 700;">[{i:02d}]</span>
                    <span style="color: #F0F6F5;">{factor}</span>
                </div>
                """)
        else:
            _md("<p style='color: #627C80;'>No primary factors generated.</p>")

        _md("</div>")

    with col_breakdown:
        _md("""
        <div class="terminal-panel">
            <div class="terminal-panel-header">
                <div class="terminal-panel-title">Sub-Model Contribution</div>
                <div class="terminal-panel-meta">WEIGHT DISTRIBUTION</div>
            </div>
        """)

        tech_score = report.get("technical", {}).get("score", 0)
        sent_score = report.get("sentiment", {}).get("score", 0)
        fund_score = report.get("fundamental", {}).get("score", 0)

        _render_mini_gauge("TECHNICAL ANALYSIS", tech_score, "40%")
        _render_mini_gauge("NEWS SENTIMENT", sent_score, "30%")
        _render_mini_gauge("DOCUMENT FUNDAMENTALS", fund_score, "30%")

        _md("</div>")

    # Risk factors summary
    risk = assess_risk(report)
    risk_factors = risk.get("risk_factors", [])
    if risk_factors:
        factors_html = "".join([
            f"<div style=\"font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; color: #FFA585; margin: 4px 0;\">• {rf}</div>"
            for rf in risk_factors
        ])
        _md(f"""
        <div style="margin-top: 14px; background: rgba(42, 42, 42, 0.4); border: 1px solid rgba(223, 65, 0, 0.35); border-left: 3px solid #DF4100; border-radius: 8px; padding: 14px 18px;">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #DF4100; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">
                ⚠️ ACTIVE RISK PARAMETERS IDENTIFIED:
            </div>
            {factors_html}
        </div>
        """)


def _render_mini_gauge(label: str, score: float, weight: str):
    """Render a clean quantitative signal gauge with progress bar."""
    is_pos = score > 0.05
    is_neg = score < -0.05
    color = "#CDFF9A" if is_pos else "#DF4100" if is_neg else "#9EB5B7"
    state = "BULLISH" if is_pos else "BEARISH" if is_neg else "NEUTRAL"
    bar_width = min(abs(score) * 100, 100)

    _md(f"""
    <div style="margin-bottom: 12px; padding: 8px 10px; background: rgba(32, 61, 67, 0.3); border-radius: 6px; border: 1px solid rgba(205, 255, 154, 0.06);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #9EB5B7; text-transform: uppercase;">{label} ({weight})</span>
            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: {color}; font-weight: 600;">{score:+.3f} // {state}</span>
        </div>
        <div style="background: rgba(0, 0, 0, 0.4); border-radius: 3px; height: 4px; width: 100%; overflow: hidden;">
            <div style="background: {color}; height: 100%; width: {bar_width}%; margin-left: {'auto' if is_neg else '0'};"></div>
        </div>
    </div>
    """)


def _render_technical_details(report: dict, ticker: str):
    """Render technical indicators as a clean matrix and multi-panel chart."""
    tech = report.get("technical", {})
    details = tech.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    indicators = details.get("indicators", {})

    table_rows_html = ""
    for name, result in indicators.items():
        if not isinstance(result, dict):
            continue
        signal = result.get("signal", 0)
        desc = result.get("description", "N/A")
        label = name.replace("_", " ").upper()

        if signal > 0:
            sig_badge = '<span style="color: #CDFF9A; font-weight: 700;">BULLISH ▲</span>'
        elif signal < 0:
            sig_badge = '<span style="color: #DF4100; font-weight: 700;">BEARISH ▼</span>'
        else:
            sig_badge = '<span style="color: #9EB5B7; font-weight: 500;">NEUTRAL ■</span>'

        table_rows_html += f"""
        <tr>
            <td style="font-weight: 600; color: #FFFFFF;">{label}</td>
            <td>{sig_badge}</td>
            <td style="color: #9EB5B7;">{desc}</td>
        </tr>
        """

    _md(f"""
    <div class="terminal-panel">
        <div class="terminal-panel-header">
            <div class="terminal-panel-title">Technical Indicator Matrix</div>
            <div class="terminal-panel-meta">PERIOD: 3-MONTH DAILY AGGREGATION</div>
        </div>
        <table class="terminal-table">
            <thead>
                <tr>
                    <th>INDICATOR</th>
                    <th>SIGNAL</th>
                    <th>INTERPRETATION</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>
    """)

    # 3-Panel Technical Subplot Chart
    _md("""
    <div class="terminal-panel-header" style="margin-top: 18px;">
        <div class="terminal-panel-title">Indicator Oscillators & Bands</div>
        <div class="terminal-panel-meta">BOLLINGER (20,2) // MACD (12,26,9) // RSI (14)</div>
    </div>
    """)

    try:
        data = get_historical_data(ticker, period="3mo")
        if data is not None and not data.empty:
            _render_technical_chart(data, ticker)
    except Exception as e:
        st.warning(f"Could not load technical indicator chart: {e}")


def _render_technical_chart(data: pd.DataFrame, ticker: str):
    """Render a 3-row institutional subplot chart with Bollinger Bands, MACD, and RSI."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.52, 0.24, 0.24],
        subplot_titles=[
            f"{ticker} // PRICE & BOLLINGER BANDS",
            "MACD (12, 26, 9)",
            "RSI (14)",
        ],
    )

    close = data["Close"]
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20

    # Panel 1: Price & Bollinger Bands
    fig.add_trace(go.Scatter(
        x=data.index, y=upper, name="Upper BB",
        line=dict(color="rgba(158,181,183,0.3)", width=1, dash="dot"),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=lower, name="Lower BB",
        line=dict(color="rgba(158,181,183,0.3)", width=1, dash="dot"),
        fill="tonexty", fillcolor="rgba(205, 255, 154, 0.04)",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=sma20, name="SMA 20",
        line=dict(color="rgba(205, 255, 154, 0.5)", width=1.2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=close, name="Close",
        line=dict(color="#CDFF9A", width=2),
    ), row=1, col=1)

    # Panel 2: MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line

    colors = ["#CDFF9A" if v >= 0 else "#DF4100" for v in histogram]
    fig.add_trace(go.Bar(
        x=data.index, y=histogram, name="MACD Hist",
        marker_color=colors, opacity=0.75,
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=macd_line, name="MACD",
        line=dict(color="#FFFFFF", width=1.5),
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=signal_line, name="Signal",
        line=dict(color="rgba(205, 255, 154, 0.7)", width=1.5, dash="dash"),
    ), row=2, col=1)

    # Panel 3: RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta).where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    fig.add_trace(go.Scatter(
        x=data.index, y=rsi, name="RSI",
        line=dict(color="#CDFF9A", width=1.8),
    ), row=3, col=1)

    fig.add_hline(y=70, line_dash="dash", line_color="rgba(223, 65, 0, 0.6)",
                  annotation_text="OVERBOUGHT (70)", annotation_font_size=9,
                  annotation_font_color="#DF4100", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(205, 255, 154, 0.6)",
                  annotation_text="OVERSOLD (30)", annotation_font_size=9,
                  annotation_font_color="#CDFF9A", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(19, 36, 39, 0.4)",
        font=dict(family="IBM Plex Mono, monospace", color="#9EB5B7", size=10),
        height=660,
        showlegend=False,
        hovermode="x unified",
        margin=dict(l=40, r=40, t=30, b=20),
    )

    fig.update_xaxes(
        gridcolor="rgba(205, 255, 154, 0.05)",
        linecolor="rgba(205, 255, 154, 0.12)",
    )
    fig.update_yaxes(
        gridcolor="rgba(205, 255, 154, 0.05)",
        linecolor="rgba(205, 255, 154, 0.12)",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_sentiment_details(report: dict):
    """Render institutional news sentiment wire and compound scores."""
    sent = report.get("sentiment", {})
    details = sent.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    score = sent.get("score", 0)
    desc = details.get("description", "N/A")
    compound = details.get("aggregate_compound", 0)

    col1, col2 = st.columns(2)
    with col1:
        _md(f"""
        <div class="metric-card">
            <div class="metric-label">Aggregate Compound Score</div>
            <div class="metric-value" style="color: {'#CDFF9A' if compound >= 0 else '#DF4100'};">
                {compound:+.4f}
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80;">RANGE: -1.0 TO +1.0 (VADER ALGORITHM)</div>
        </div>
        """)
    with col2:
        _md(f"""
        <div class="metric-card">
            <div class="metric-label">Sentiment Classification</div>
            <div class="metric-value" style="font-size: 1.3rem; color: #FFFFFF;">{desc.upper()}</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80;">WEIGHT CONTRIBUTION: 30%</div>
        </div>
        """)

    # Individual headline audit
    individual = details.get("individual", [])
    if individual:
        headlines_html = ""
        for item in individual[:8]:
            headline = item.get("headline", "N/A")
            c_score = item.get("compound", 0)

            if c_score > 0.05:
                badge = f'<span style="color: #CDFF9A; font-weight: 700;">+{c_score:.3f} ▲</span>'
            elif c_score < -0.05:
                badge = f'<span style="color: #DF4100; font-weight: 700;">{c_score:.3f} ▼</span>'
            else:
                badge = f'<span style="color: #9EB5B7; font-weight: 500;">{c_score:+.3f} ■</span>'

            headlines_html += f"""
            <div style="display: flex; align-items: flex-start; gap: 14px; padding: 10px 0; border-bottom: 1px solid rgba(205, 255, 154, 0.06); font-family: 'IBM Plex Sans', sans-serif; font-size: 0.88rem;">
                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; min-width: 80px;">{badge}</div>
                <div style="color: #F0F6F5; line-height: 1.4;">{headline}</div>
            </div>
            """

        _md(f"""
        <div class="terminal-panel" style="margin-top: 14px;">
            <div class="terminal-panel-header">
                <div class="terminal-panel-title">Parsed News Headlines & Sentiment Attribution</div>
                <div class="terminal-panel-meta">AUDIT TRAIL</div>
            </div>
            {headlines_html}
        </div>
        """)
    else:
        st.info("No individual news headlines available for sentiment breakdown.")


def _render_fundamental_details(report: dict):
    """Render fundamental document analysis from the vector store."""
    fund = report.get("fundamental", {})
    details = fund.get("details", {})

    if isinstance(details, dict) and "error" in details:
        st.error(details["error"])
        return

    score = fund.get("score", 0)
    desc = details.get("description", "N/A")
    doc_count = details.get("documents_found", 0)
    sources = details.get("sources", [])

    col1, col2 = st.columns(2)
    with col1:
        _md(f"""
        <div class="metric-card">
            <div class="metric-label">Document Chunks Retrieved</div>
            <div class="metric-value" style="color: #CDFF9A;">{doc_count}</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80;">VECTOR STORE: CHROMADB HYBRID SEARCH</div>
        </div>
        """)
    with col2:
        _md(f"""
        <div class="metric-card">
            <div class="metric-label">Fundamental Composite Score</div>
            <div class="metric-value" style="color: {'#CDFF9A' if score >= 0 else '#DF4100'};">
                {score:+.3f}
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80;">EVALUATION: {desc.upper()}</div>
        </div>
        """)

    if doc_count == 0:
        _md("""
        <div class="glass-card" style="margin-top: 14px; text-align: center; padding: 24px;">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #627C80;">
                NO AUDITED DOCUMENTS FOUND FOR THIS TICKER IN THE LOCAL VECTOR STORE<br>
                <span style="font-size: 0.74rem; color: #435E62;">Upload 10-K, earnings releases, or equity research PDF/TXT files in the Research Agent tab to populate this index.</span>
            </div>
        </div>
        """)
        return

    if sources:
        sources_html = "".join([
            f'<div style="font-family: \'IBM Plex Mono\', monospace; font-size: 0.78rem; color: #CDFF9A; padding: 6px 0;">📄 {s}</div>'
            for s in list(set(sources))
        ])
        _md(f"""
        <div class="terminal-panel" style="margin-top: 14px;">
            <div class="terminal-panel-header">
                <div class="terminal-panel-title">Referenced Corpus Filenames</div>
                <div class="terminal-panel-meta">DOCUMENT SOURCE ATTRIBUTION</div>
            </div>
            {sources_html}
        </div>
        """)
