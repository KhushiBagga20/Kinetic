"""
Dashboard — the live market view.

Every figure on this page is fetched at render time from Yahoo Finance:
index levels, the candle chart, the screener tables and the news feed. There
is no bundled sample data anywhere in the app.
"""

from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

import config
from src import indicators
from src.market import (
    get_history,
    get_movers,
    get_news,
    get_quote,
    get_quotes,
    resolve_symbol,
    session,
)
from src.rag import ingest_market_feed
from ui.components import chips, format_money, hint, metric_tile, panel_header

PERIODS = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
SCREENERS = {"Gainers": "day_gainers", "Losers": "day_losers", "Most active": "most_actives"}


def _compact(value: float | None) -> str:
    """Index levels are long; drop decimals once they stop carrying meaning."""
    if value is None:
        return "—"
    if abs(value) >= 10_000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _index_ribbon() -> None:
    quotes = get_quotes(config.INDEX_SYMBOLS)
    if not quotes:
        hint("Index data is unavailable right now — the market data provider did not respond.")
        return
    columns = st.columns(len(quotes))
    for column, quote in zip(columns, quotes):
        with column:
            change = quote.change_percent or 0.0
            metric_tile(
                quote.name.replace(" Index", "")[:18],
                _compact(quote.price),
                f"{change:+.2f}%",
                positive=change >= 0,
            )


def _price_chart(symbol: str, history, currency: str) -> None:
    close = history["Close"]
    figure = go.Figure()
    figure.add_trace(
        go.Candlestick(
            x=history.index,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=close,
            name=symbol,
            increasing_line_color="#CDFF9A",
            decreasing_line_color="#DF4100",
            increasing_fillcolor="rgba(205,255,154,0.35)",
            decreasing_fillcolor="rgba(223,65,0,0.35)",
        )
    )
    for window, colour in ((20, "#9EB5B7"), (50, "#627C80")):
        if len(close) > window:
            figure.add_trace(
                go.Scatter(
                    x=history.index,
                    y=close.rolling(window).mean(),
                    name=f"SMA {window}",
                    line=dict(color=colour, width=1.2),
                )
            )
    figure.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,28,31,0.5)",
        font=dict(family="IBM Plex Mono", color="#9EB5B7", size=11),
        xaxis=dict(gridcolor="rgba(32,61,67,0.6)", rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor="rgba(32,61,67,0.6)", title=currency),
        legend=dict(orientation="h", y=1.06, x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _quote_header(quote) -> None:
    change = quote.change_percent or 0.0
    columns = st.columns(5)
    with columns[0]:
        metric_tile("Last price", f"{quote.price:,.2f} {quote.currency}" if quote.price else "—",
                    f"{quote.change:+,.2f} ({change:+.2f}%)" if quote.change is not None else "",
                    positive=change >= 0)
    with columns[1]:
        metric_tile("Day range",
                    f"{quote.day_low:,.2f} – {quote.day_high:,.2f}" if quote.day_low else "—")
    with columns[2]:
        metric_tile("52-week range",
                    f"{quote.year_low:,.2f} – {quote.year_high:,.2f}" if quote.year_low else "—")
    with columns[3]:
        metric_tile("Volume", f"{quote.volume:,.0f}" if quote.volume else "—")
    with columns[4]:
        metric_tile("Market cap", format_money(quote.market_cap, quote.currency))


def _news_feed(symbol: str) -> None:
    articles = get_news(symbol)
    if not articles:
        hint("No headlines returned for this symbol in the last news window.")
        return
    for article in articles:
        st.markdown(
            f"""
            <div class="news-card">
                <div class="news-title">{html.escape(article.title)}</div>
                <div class="news-meta">{html.escape(article.publisher)} · {article.published} ·
                    <a href="{article.url}" target="_blank">open</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _movers() -> None:
    tabs = st.tabs(list(SCREENERS))
    for tab, (label, key) in zip(tabs, SCREENERS.items()):
        with tab:
            rows = get_movers(key, count=8)
            if not rows:
                hint("The screener did not return rows right now.")
                continue
            body = "".join(
                f"<tr><td><strong>{row['symbol']}</strong></td>"
                f"<td>{html.escape(row['name'][:34])}</td>"
                f"<td>{row['price']:,.2f} {row['currency']}</td>"
                f"<td style=\"color: {'#CDFF9A' if (row['change_percent'] or 0) >= 0 else '#DF4100'};\">"
                f"{row['change_percent']:+.2f}%</td></tr>"
                for row in rows
            )
            st.markdown(
                f'<table class="terminal-table"><thead><tr><th>Symbol</th><th>Name</th>'
                f'<th>Price</th><th>Change</th></tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True,
            )


def render() -> None:
    panel_header("Live market", "QUOTES · CANDLES · NEWS · SCREENERS, FETCHED ON EVERY RENDER")

    _index_ribbon()
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    search_column, period_column, action_column = st.columns([3, 2, 2], vertical_alignment="bottom")
    with search_column:
        query = st.text_input(
            "Symbol or company name",
            value=st.session_state.get("symbol", config.DEFAULT_SYMBOL),
            help="Type a ticker (RELIANCE.NS, AAPL) or a company name — it is resolved live.",
        )
    with period_column:
        period_label = st.radio("Period", list(PERIODS), index=2, horizontal=True, label_visibility="collapsed")
    with action_column:
        capture = st.button("Capture to knowledge base", use_container_width=True,
                            help="Index this symbol's live quote, fundamentals and headlines so the assistant can retrieve them.")

    symbol = resolve_symbol(query) if query else None
    if not symbol:
        st.warning(f"No tradable instrument found for “{query}”. Try a ticker such as MSFT or a full company name.")
        return
    st.session_state.symbol = symbol

    quote = get_quote(symbol)
    if quote is None:
        st.warning(f"No live quote available for {symbol} right now.")
        return

    if capture:
        with st.spinner(f"Indexing live data for {symbol}…"):
            written = ingest_market_feed(symbol)
        st.success(f"Indexed {written} live passages for {symbol}. Ask the assistant about it.")

    st.markdown(
        f"<div style='margin: 10px 0 6px 0;'><span class='stock-symbol'>{symbol}</span> "
        f"<span class='stock-company'>{html.escape(quote.name)}</span></div>",
        unsafe_allow_html=True,
    )
    state = session(symbol)
    chips([
        ("live", f"{state['exchange'] or quote.exchange or 'market'} · {state['label']}"),
        ("live", f"fetched {quote.as_of}"),
    ])
    _quote_header(quote)

    history = get_history(symbol, period=PERIODS[period_label])
    if history.empty:
        hint("No candles returned for this period.")
        return

    chart_column, signal_column = st.columns([3, 1])
    with chart_column:
        _price_chart(symbol, history, quote.currency)
    with signal_column:
        st.markdown("**Technical read**")
        computed = indicators.compute_all(history)
        for name, result in computed.items():
            if result["value"] is None:
                continue
            st.markdown(
                f'<div class="leg-row"><span class="leg-name">{name.replace("_", " ")}</span>'
                f'<span>{result["value"]}</span></div><div class="hint">{result["note"]}</div>',
                unsafe_allow_html=True,
            )

    news_column, movers_column = st.columns([3, 2])
    with news_column:
        st.markdown("**Live headlines**")
        _news_feed(symbol)
    with movers_column:
        st.markdown("**Market movers**")
        _movers()
