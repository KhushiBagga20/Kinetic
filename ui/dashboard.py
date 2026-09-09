"""
Dashboard View — Real-Time Market Intelligence Terminal.

Features:
    - Real-time stock price cards with auto-refresh
    - Institutional interactive candlestick charts (Plotly) with SMA & Volume
    - Real-time financial intelligence news wire
    - Watchlist management with quick-ticker selectors
"""

from textwrap import dedent
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.tools.stock_lookup import get_stock_data_raw, get_historical_data
from src.tools.news_fetcher import get_news_for_sentiment
import config


def render_dashboard():
    """Render the live market dashboard tab."""

    # ── Section Header / Controls ─────────────────────────────────────
    st.markdown("""
    <div class="terminal-panel-header" style="margin-top: 4px;">
        <div class="terminal-panel-title">
            <span style="color: #CDFF9A;">●</span>
            <span>Market Overview & Watchlist</span>
        </div>
        <div class="terminal-panel-meta">
            REFRESH INTERVAL: 120s // SOURCE: NYSE, NASDAQ, GLOBAL
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Watchlist Command Bar ─────────────────────────────────────────
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ticker_input = st.text_input(
            "Watchlist Tickers",
            value="AAPL, NVDA, MSFT, TSLA",
            placeholder="e.g. AAPL, NVDA, MSFT, AMZN, GOOGL",
            key="dashboard_ticker_input",
            label_visibility="collapsed",
        )
    with col_btn:
        refresh = st.button("↻ REFRESH", key="refresh_btn", help="Fetch latest market quotes")

    # Quick Ticker Selector Chips
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin: -6px 0 14px 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #627C80;">
        <span>PRESETS:</span>
        <span style="color: #9EB5B7;">AAPL</span> •
        <span style="color: #9EB5B7;">NVDA</span> •
        <span style="color: #9EB5B7;">MSFT</span> •
        <span style="color: #9EB5B7;">AMZN</span> •
        <span style="color: #9EB5B7;">GOOGL</span>
    </div>
    """, unsafe_allow_html=True)

    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

    if not tickers:
        st.info("Enter stock tickers above to load real-time market data.")
        return

    # ── Stock Price Cards ─────────────────────────────────────────────
    # Display in responsive columns (up to 4 per row)
    displayed_tickers = tickers[:8]
    chunk_size = 4
    for row_idx in range(0, len(displayed_tickers), chunk_size):
        row_tickers = displayed_tickers[row_idx:row_idx + chunk_size]
        cols = st.columns(len(row_tickers))
        for col, t in zip(cols, row_tickers):
            with col:
                _render_stock_card(t)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ── Chart & Intelligence Feed Section (Two Columns) ───────────────
    st.markdown("""
    <div class="terminal-panel-header" style="margin-top: 18px;">
        <div class="terminal-panel-title">
            <span style="color: #CDFF9A;">●</span>
            <span>Technical Charting & Intelligence Wire</span>
        </div>
        <div class="terminal-panel-meta">
            PLOT: CANDLESTICK + 20-SMA + VOLUME
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_chart, col_feed = st.columns([13, 9])

    with col_chart:
        # Chart Toolbar
        c_sub1, c_sub2 = st.columns([2, 3])
        with c_sub1:
            chart_ticker = st.selectbox(
                "Active Ticker",
                tickers,
                key="chart_ticker_select",
                label_visibility="collapsed",
            )
        with c_sub2:
            chart_period = st.select_slider(
                "Time Period",
                options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                value="3mo",
                key="chart_period_slider",
                label_visibility="collapsed",
            )

        if chart_ticker:
            _render_candlestick_chart(chart_ticker, chart_period)

    with col_feed:
        # News Wire
        n_col1, n_col2 = st.columns([2, 3])
        with n_col1:
            news_ticker = st.selectbox(
                "News Wire Ticker",
                tickers,
                key="news_ticker_select",
                label_visibility="collapsed",
            )
        with n_col2:
            st.markdown(f"""
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #627C80; text-align: right; padding-top: 8px;">
                FEED: LIVE // {news_ticker}
            </div>
            """, unsafe_allow_html=True)

        if news_ticker:
            _render_news_feed(news_ticker)


def _render_stock_card(ticker: str):
    """Render an institutional-grade stock quote tile."""
    try:
        data = get_stock_data_raw(ticker)
        if not data:
            st.markdown(f"""
            <div class="stock-tile">
                <div class="stock-symbol">{ticker}</div>
                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; color: #DF4100; margin-top: 6px;">
                    FEED UNAVAILABLE
                </div>
            </div>
            """, unsafe_allow_html=True)
            return

        price = data.get("current_price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_percent", 0)
        currency = data.get("currency", "USD")
        company = data.get("company_name", ticker)

        is_positive = change >= 0
        delta_class = "delta-positive" if is_positive else "delta-negative"
        arrow = "▲" if is_positive else "▼"
        sign = "+" if is_positive else ""

        st.markdown(dedent(f"""
        <div class="stock-tile">
            <div class="stock-tile-top">
                <div>
                    <div class="stock-symbol">{ticker}</div>
                    <div class="stock-company" title="{company}">{company}</div>
                </div>
                <div class="stock-delta-pill {delta_class}">
                    <span>{arrow}</span>
                    <span>{sign}{change_pct:.2f}%</span>
                </div>
            </div>
            <div class="stock-price">{currency} {price:,.2f}</div>
            <div style="display: flex; align-items: center; justify-content: space-between; font-family: 'IBM Plex Mono', monospace; font-size: 0.70rem; color: #627C80; margin-top: 4px;">
                <span>Δ {sign}{change:,.2f}</span>
                <span>VOL: {data.get('volume', 0):,}</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

    except Exception as e:
        st.markdown(dedent(f"""
        <div class="stock-tile">
            <div class="stock-symbol">{ticker}</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #DF4100;">
                ERR: {str(e)[:24]}
            </div>
        </div>
        """), unsafe_allow_html=True)


def _render_candlestick_chart(ticker: str, period: str = "3mo"):
    """Render an institutional candlestick chart with Plotly."""
    try:
        data = get_historical_data(ticker, period=period)
        if data is None or data.empty:
            st.warning(f"No historical chart data available for {ticker}")
            return

        fig = go.Figure()

        # Candlestick: #CDFF9A for up, #DF4100 for down
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            increasing=dict(
                line=dict(color="#CDFF9A", width=1.2),
                fillcolor="rgba(205, 255, 154, 0.25)",
            ),
            decreasing=dict(
                line=dict(color="#DF4100", width=1.2),
                fillcolor="rgba(223, 65, 0, 0.25)",
            ),
            name="Price",
        ))

        # 20-day Simple Moving Average
        sma20 = data["Close"].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=sma20,
            mode="lines",
            line=dict(color="rgba(205, 255, 154, 0.85)", width=1.5),
            name="SMA 20",
        ))

        # Volume bars overlaid on y2
        volume_colors = [
            "rgba(205, 255, 154, 0.22)" if c >= o else "rgba(223, 65, 0, 0.22)"
            for c, o in zip(data["Close"], data["Open"])
        ]
        fig.add_trace(go.Bar(
            x=data.index,
            y=data["Volume"],
            marker_color=volume_colors,
            name="Volume",
            yaxis="y2",
            opacity=0.45,
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(19, 36, 39, 0.35)",
            font=dict(family="IBM Plex Mono, monospace", color="#9EB5B7", size=11),
            height=460,
            hovermode="x unified",
            margin=dict(l=40, r=40, t=20, b=30),
            xaxis=dict(
                gridcolor="rgba(205, 255, 154, 0.05)",
                linecolor="rgba(205, 255, 154, 0.12)",
                rangeslider=dict(visible=False),
                showspikes=True,
                spikemode="across",
                spikesnap="cursor",
                spikedash="solid",
                spikethickness=1,
                spikecolor="rgba(205, 255, 154, 0.25)",
            ),
            yaxis=dict(
                title="",
                gridcolor="rgba(205, 255, 154, 0.05)",
                linecolor="rgba(205, 255, 154, 0.12)",
                side="right",
                tickformat=",.2f",
                showspikes=True,
                spikecolor="rgba(205, 255, 154, 0.25)",
            ),
            yaxis2=dict(
                title="",
                overlaying="y",
                side="left",
                showgrid=False,
                showticklabels=False,
                range=[0, data["Volume"].max() * 4],
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10),
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)[:100]}")


def _render_news_feed(ticker: str):
    """Render the financial intelligence wire for a ticker."""
    try:
        articles = get_news_for_sentiment(ticker)

        if not articles:
            st.markdown(f"""
            <div style="padding: 20px; text-align: center; font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #627C80; background: rgba(32, 61, 67, 0.2); border: 1px dashed rgba(205, 255, 154, 0.1); border-radius: 8px;">
                NO RECENT INTELLIGENCE LOGS FOR {ticker}<br>
                <span style="font-size: 0.72rem; color: #435E62;">VERIFY NEWS_API_KEY IN .ENV</span>
            </div>
            """, unsafe_allow_html=True)
            return

        # Render news feed wire
        st.markdown('<div style="max-height: 460px; overflow-y: auto; padding-right: 4px;">', unsafe_allow_html=True)
        for article in articles[:6]:
            title = article.get("title", "No headline")
            source = article.get("source", "MARKET WIRE")
            date = article.get("published_at", "")
            url = article.get("url", "")

            # Truncate or format date
            date_str = date[:16].replace("T", " ") if "T" in date else date[:16]

            link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">WIRE DETAILS ↗</a>' if url else ''

            st.markdown(dedent(f"""
            <div class="intel-feed-item">
                <div class="news-title">{title}</div>
                <div class="news-meta">
                    <span style="color: #CDFF9A; font-weight: 600;">{source.upper()}</span>
                    <span>•</span>
                    <span>{date_str}</span>
                    {'<span>•</span> ' + link_html if link_html else ''}
                </div>
            </div>
            """), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading news feed: {str(e)[:100]}")
