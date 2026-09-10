"""
Forecast — the ensemble signal, with every component shown.

The point of this view is that nothing is a black box: each leg's score, its
weight, and the specific observations behind it are on screen, alongside the
volatility-implied range that bounds how much any of it is worth.
"""

from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

import config
from src.llm import engine
from src.market import get_history, get_quote, resolve_symbol
from src.prediction import forecast
from ui.components import chips, hint, meter, panel_header, signal_pill, steps

TONE = {"BULL": "lime", "BEAR": "orange", "NEUT": "neutral"}


def _projection_chart(symbol: str, result) -> None:
    history = get_history(symbol, period="3mo")
    if history.empty or result.expected_low is None:
        return
    close = history["Close"]
    last_date = close.index[-1]
    future = [last_date + (last_date - close.index[-2]) * step for step in range(1, result.horizon_days + 1)]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=close.index, y=close, name="Close", line=dict(color="#CDFF9A", width=1.6))
    )
    for bound, colour, label in (
        (result.expected_high, "rgba(205,255,154,0.55)", "1σ high"),
        (result.expected_low, "rgba(223,65,0,0.55)", "1σ low"),
    ):
        figure.add_trace(
            go.Scatter(
                x=[last_date] + future,
                y=[float(close.iloc[-1])] + [bound] * len(future),
                name=label,
                line=dict(color=colour, width=1.2, dash="dot"),
            )
        )
    figure.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,28,31,0.5)",
        font=dict(family="IBM Plex Mono", color="#9EB5B7", size=11),
        xaxis=dict(gridcolor="rgba(32,61,67,0.6)"),
        yaxis=dict(gridcolor="rgba(32,61,67,0.6)", title=result.currency),
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _leg_panel(result) -> None:
    for key, leg in result.legs.items():
        weight = f"{leg.weight * 100:.0f}%" if leg.available else "excluded"
        score = f"{leg.score:+.2f}" if leg.available else "no data"
        tone = "lime" if leg.score > 0.05 else "orange" if leg.score < -0.05 else "neutral"
        st.markdown(
            f'<div class="leg-row"><span class="leg-name">{leg.name}</span>'
            f'<span>{score} · weight {weight}</span></div>',
            unsafe_allow_html=True,
        )
        meter(abs(leg.score) * 100 if leg.available else 0, tone)
        with st.expander(f"What drove “{leg.name}”", expanded=False):
            if not leg.notes:
                st.caption("No observations recorded for this leg.")
            for note in leg.notes:
                st.markdown(f"- {note}")


def _narrate(result) -> None:
    """Ask the local model to write the analyst note for this forecast."""
    llm = engine()
    prompt = (
        "Write a short research note (max 180 words) explaining this signal to an "
        "investor. Reference the specific numbers you were given, name which leg "
        "drove the score, and state one thing that would invalidate the read. Do "
        "not give buy or sell advice.\n\n" + result.to_text()
    )
    slot = st.empty()
    text = ""
    for piece in llm.stream([{"role": "user", "content": prompt}], max_tokens=420):
        if piece.channel == "answer":
            text += piece.text
            slot.markdown(
                f'<div class="stream-answer">{html.escape(text)}<span class="caret"></span></div>',
                unsafe_allow_html=True,
            )
    slot.markdown(f'<div class="stream-answer">{html.escape(text)}</div>', unsafe_allow_html=True)


def render() -> None:
    panel_header(
        "Ensemble forecast",
        f"TECHNICAL {config.WEIGHT_TECHNICAL:.0%} · SENTIMENT {config.WEIGHT_SENTIMENT:.0%} · "
        f"FUNDAMENTAL {config.WEIGHT_FUNDAMENTAL:.0%} · DOCUMENTS {config.WEIGHT_DOCUMENTS:.0%}",
    )

    input_column, horizon_column, run_column = st.columns([3, 2, 1], vertical_alignment="bottom")
    with input_column:
        query = st.text_input("Symbol or company", value=st.session_state.get("symbol", config.DEFAULT_SYMBOL))
    with horizon_column:
        horizon = st.slider("Horizon (trading sessions)", 5, 30, config.FORECAST_HORIZON_DAYS)
    with run_column:
        run = st.button("Run", use_container_width=True, type="primary")

    if not run and "forecast" not in st.session_state:
        steps(
            [
                ("Pick an instrument", "Any ticker or company name. Indices and crypto work too."),
                ("Four legs are scored", "Technical indicators, live headline sentiment, live fundamentals and your own indexed documents — each on a −1 to +1 scale."),
                ("Read the range, not the number", "The projection is the 1σ band implied by realised volatility: roughly two thirds of historical outcomes fall inside it."),
            ]
        )
        return

    if run:
        symbol = resolve_symbol(query)
        if not symbol:
            st.warning(f"No instrument found for “{query}”.")
            return
        st.session_state.symbol = symbol
        with st.spinner(f"Scoring {symbol} against live market data…"):
            st.session_state.forecast = forecast(symbol, horizon_days=horizon)

    result = st.session_state.get("forecast")
    if result is None:
        st.warning("No forecast could be produced — live data was unavailable.")
        return

    quote = get_quote(result.symbol)
    st.markdown(
        f"<div style='margin: 12px 0 4px;'>{signal_pill(result.signal)} "
        f"<span class='stock-symbol' style='margin-left:10px;'>{result.symbol}</span> "
        f"<span class='stock-company'>{html.escape(result.name)}</span></div>",
        unsafe_allow_html=True,
    )
    chips([("live", f"generated {result.as_of}"), ("doc", result.data_quality)])

    columns = st.columns(4)
    with columns[0]:
        st.markdown('<div class="metric-label">Direction score</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{result.direction:+.2f}</div>', unsafe_allow_html=True)
        meter(abs(result.direction) * 100, "lime" if result.direction >= 0 else "orange")
        hint("−1 to +1, weighted across the active legs")
    with columns[1]:
        st.markdown('<div class="metric-label">Confidence</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{result.confidence:.0f}%</div>', unsafe_allow_html=True)
        meter(result.confidence, "lime")
        hint("How much the legs agree, and how complete the data is")
    with columns[2]:
        st.markdown('<div class="metric-label">Risk</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{result.risk_score}/10</div>', unsafe_allow_html=True)
        meter(result.risk_score * 10, "orange")
        hint(f"{result.risk_label} — volatility, drawdown and beta")
    with columns[3]:
        st.markdown('<div class="metric-label">Last price</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{result.price:,.2f}</div>' if result.price else "—",
            unsafe_allow_html=True,
        )
        if quote and quote.change_percent is not None:
            hint(f"{quote.change_percent:+.2f}% today · {result.currency}")

    if result.expected_low is not None:
        st.markdown(
            f"**{result.horizon_days}-session 1σ range:** "
            f"{result.expected_low:,.2f} – {result.expected_high:,.2f} {result.currency} "
            f"— about two thirds of historical moves of this size fall inside this band."
        )
        _projection_chart(result.symbol, result)

    breakdown_column, drivers_column = st.columns([3, 2])
    with breakdown_column:
        st.markdown("**Signal breakdown**")
        _leg_panel(result)
    with drivers_column:
        st.markdown("**Key drivers**")
        for driver in result.drivers:
            st.markdown(f"- {driver}")
        st.markdown("**Analyst note**")
        if engine().is_loaded:
            if st.button("Write it with the local model", use_container_width=True):
                _narrate(result)
        else:
            hint("Load the local model (sidebar) to have Gemma 4 write the note for this signal.")

    st.info(config.DISCLAIMER, icon="⚠️")
