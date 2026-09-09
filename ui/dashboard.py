"""
Dashboard View — live stock prices, market news, and interactive charts.

Features:
    - Real-time stock price cards with auto-refresh (every 2-3 min)
    - Interactive candlestick charts (Plotly)
    - Live market news feed
    - Watchlist management
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time

from src.tools.stock_lookup import get_stock_data_raw, get_historical_data
from src.tools.news_fetcher import get_news_for_sentiment

import config


def render_dashboard():
    """Render the live market dashboard tab."""

    # ── Header ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="glass-card">
        <h2 style="color: #63b3ed; margin: 0;">📊 Live Market Dashboard</h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0;">
            Real-time stock prices and market news • Auto-refreshes every 2 minutes
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Watchlist Input ───────────────────────────────────────────────
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        ticker_input = st.text_input(
            "Add tickers (comma-separated)",
            value="AAPL, GOOGL, MSFT, AMZN",
            placeholder="e.g., AAPL, GOOGL, RELIANCE.NS",
            key="dashboard_ticker_input",
        )
    with col_btn:
        st.write("")  # Spacer
        st.write("")
        refresh = st.button("🔄 Refresh", key="refresh_btn")

    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

    if not tickers:
        st.info("Enter stock tickers above to see live data.")
        return

    # ── Stock Price Cards ─────────────────────────────────────────────
    st.markdown("### 📈 Stock Prices")

    cols = st.columns(min(len(tickers), 4))
    for i, ticker in enumerate(tickers[:4]):
        with cols[i % 4]:
            _render_stock_card(ticker)

    # Show remaining tickers in next row
    if len(tickers) > 4:
        cols2 = st.columns(min(len(tickers) - 4, 4))
        for i, ticker in enumerate(tickers[4:8]):
            with cols2[i % 4]:
                _render_stock_card(ticker)

    # ── Chart Section ─────────────────────────────────────────────────
    st.markdown("### 📉 Price Chart")
    chart_ticker = st.selectbox(
        "Select ticker for chart",
        tickers,
        key="chart_ticker_select",
    )

    chart_period = st.select_slider(
        "Time Period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        value="3mo",
        key="chart_period_slider",
    )

    if chart_ticker:
        _render_candlestick_chart(chart_ticker, chart_period)

    # ── News Feed ─────────────────────────────────────────────────────
    st.markdown("### 📰 Market News")
    news_ticker = st.selectbox(
        "Select ticker for news",
        tickers,
        key="news_ticker_select",
    )

    if news_ticker:
        _render_news_feed(news_ticker)


def _render_stock_card(ticker: str):
    """Render a single stock price card."""
    try:
        data = get_stock_data_raw(ticker)
        if not data:
            st.error(f"❌ {ticker}")
            return

        price = data.get("current_price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_percent", 0)
        currency = data.get("currency", "USD")
        company = data.get("company_name", ticker)

        # Color based on change
        change_class = "metric-change-positive" if change >= 0 else "metric-change-negative"
        arrow = "▲" if change >= 0 else "▼"
        change_sign = "+" if change >= 0 else ""

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{company}</div>
            <div class="metric-value">{currency} {price:,.2f}</div>
            <div class="{change_class}">
                {arrow} {change_sign}{change:,.2f} ({change_sign}{change_pct:.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading {ticker}: {str(e)[:50]}")


def _render_candlestick_chart(ticker: str, period: str = "3mo"):
    """Render an interactive candlestick chart using Plotly."""
    try:
        data = get_historical_data(ticker, period=period)
        if data is None or data.empty:
            st.warning(f"No historical data available for {ticker}")
            return

        fig = go.Figure(data=[
            go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                increasing=dict(line=dict(color="#48bb78"), fillcolor="rgba(72,187,120,0.3)"),
                decreasing=dict(line=dict(color="#fc8181"), fillcolor="rgba(252,129,129,0.3)"),
                name="Price",
            )
        ])

        # Add volume bars
        colors = ["rgba(72,187,120,0.3)" if c >= o else "rgba(252,129,129,0.3)"
                   for c, o in zip(data["Close"], data["Open"])]

        fig.add_trace(go.Bar(
            x=data.index,
            y=data["Volume"],
            marker_color=colors,
            name="Volume",
            yaxis="y2",
            opacity=0.4,
        ))

        # Add 20-day SMA
        sma20 = data["Close"].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=sma20,
            mode="lines",
            line=dict(color="rgba(99,179,237,0.6)", width=1.5),
            name="SMA 20",
        ))

        fig.update_layout(
            title=f"{ticker} — {period.upper()} Price Chart",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.03)",
                rangeslider=dict(visible=False),
            ),
            yaxis=dict(
                title="Price",
                gridcolor="rgba(255,255,255,0.03)",
                side="right",
            ),
            yaxis2=dict(
                title="Volume",
                overlaying="y",
                side="left",
                showgrid=False,
                range=[0, data["Volume"].max() * 4],
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            height=500,
            margin=dict(l=60, r=60, t=60, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)[:100]}")


def _render_news_feed(ticker: str):
    """Render the news feed for a ticker."""
    try:
        articles = get_news_for_sentiment(ticker)

        if not articles:
            st.info(f"No recent news found for {ticker}. Ensure your NEWS_API_KEY is set in .env.")
            return

        for article in articles:
            title = article.get("title", "No title")
            source = article.get("source", "Unknown")
            date = article.get("published_at", "Unknown")
            url = article.get("url", "")

            st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{title}</div>
                <div class="news-meta">
                    📌 {source} &nbsp;|&nbsp; 📅 {date}
                    {'&nbsp;|&nbsp; <a href="' + url + '" target="_blank" style="color: #63b3ed;">Read →</a>' if url else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading news: {str(e)[:100]}")
