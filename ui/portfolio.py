"""
Portfolio — your holdings, priced live, analysed on-device.

The file behind this view lives on your disk and is read by nothing else.
That is the whole reason Kinetic runs a 26B model locally: you can ask about
your actual money without handing it to anyone.
"""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from src import portfolio
from src.market import resolve_symbol
from ui.components import (
    arrow,
    ask_about,
    chips,
    hint,
    metric_tile,
    nav_to,
    panel_header,
    steps,
)


def _totals(summary: dict) -> None:
    base = summary["base_currency"]
    columns = st.columns(4)
    with columns[0]:
        metric_tile("Market value", f"{summary['market_value']:,.0f} {base}")
    with columns[1]:
        metric_tile(
            "Unrealised P&L",
            f"{summary['unrealised']:+,.0f} {base}",
            f"{summary['unrealised_percent']:+.2f}% on cost",
            positive=summary["unrealised"] >= 0,
        )
    with columns[2]:
        metric_tile(
            "Today",
            f"{summary['day_change']:+,.0f} {base}",
            f"{summary['day_change_percent']:+.2f}%",
            positive=summary["day_change"] >= 0,
        )
    with columns[3]:
        metric_tile(
            "Concentration",
            f"{summary['largest_weight']:.0f}%",
            f"in {summary['largest_position']}",
        )


def _positions_table(rows: list) -> None:
    body = []
    for row in rows:
        up = (row.unrealised or 0) >= 0
        colour = "#CDFF9A" if up else "#DF4100"
        price = f"{row.price:,.2f}" if row.price is not None else "—"
        pnl = f"{row.unrealised:+,.0f} ({row.unrealised_percent:+.1f}%)" if row.unrealised is not None else "—"
        day = f"{row.day_change_percent:+.2f}%" if row.day_change_percent is not None else "—"
        body.append(
            f"<tr><th scope='row' style='text-align:left'>{row.symbol}</th>"
            f"<td>{html.escape(row.name[:26])}</td>"
            f"<td>{row.quantity:g}</td>"
            f"<td>{row.average_cost:,.2f}</td>"
            f"<td>{price} {row.currency}</td>"
            f"<td style='color:{colour}'><span aria-hidden='true'>{arrow(up)}</span> {pnl}</td>"
            f"<td>{day}</td>"
            f"<td>{row.weight:.1f}%</td></tr>"
        )
    st.markdown(
        "<table class='terminal-table'><caption class='visually-hidden'>Your holdings priced live</caption>"
        "<thead><tr><th scope='col'>Symbol</th><th scope='col'>Name</th><th scope='col'>Qty</th>"
        "<th scope='col'>Avg cost</th><th scope='col'>Last</th><th scope='col'>Unrealised</th>"
        "<th scope='col'>Today</th><th scope='col'>Weight</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>",
        unsafe_allow_html=True,
    )


def _allocation_chart(rows: list, summary: dict) -> None:
    figure = go.Figure(
        go.Pie(
            labels=[row.symbol for row in rows],
            values=[row.value_in_base or 0 for row in rows],
            hole=0.62,
            marker=dict(
                colors=["#CDFF9A", "#8FD97A", "#5FB39B", "#3E8E96", "#2C6B78", "#203D43"],
                line=dict(color="#0E1C1F", width=2),
            ),
            textinfo="label+percent",
            hovertemplate="%{label}: %{value:,.0f} " + summary["base_currency"] + "<extra></extra>",
        )
    )
    figure.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=6, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono", color="#9EB5B7", size=11),
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _editor(rows: list) -> None:
    """Add, change or remove holdings."""
    with st.form("add_holding", clear_on_submit=True):
        st.markdown("**Add a holding**")
        symbol_column, quantity_column, cost_column, button_column = st.columns([3, 2, 2, 2])
        query = symbol_column.text_input("Symbol or company name", placeholder="RELIANCE.NS or infosys")
        quantity = quantity_column.number_input("Quantity", min_value=0.0, step=1.0, format="%.4f")
        cost = cost_column.number_input("Average cost per unit", min_value=0.0, step=1.0, format="%.2f")
        submitted = button_column.form_submit_button("Add", use_container_width=True, type="primary")

    if submitted:
        if not query or quantity <= 0:
            st.warning("Enter a symbol and a quantity greater than zero.")
        else:
            symbol = resolve_symbol(query)
            if not symbol:
                st.warning(f"No tradable instrument found for “{query}”.")
            else:
                portfolio.add_holding(symbol, quantity, cost)
                st.success(f"Added {quantity:g} × {symbol}.")
                st.rerun()

    if rows:
        st.markdown("**Remove a holding**")
        columns = st.columns(min(len(rows), 5))
        for index, row in enumerate(rows):
            if columns[index % len(columns)].button(f"Remove {row.symbol}", key=f"rm_{row.symbol}"):
                portfolio.remove_holding(row.symbol)
                st.rerun()


def _exposure_panel(rows: list) -> None:
    st.markdown("**Exposure check**")
    hint(
        "Describe an event in plain words. Each holding's live profile — business "
        "summary, sector and today's headlines — is embedded on this machine and "
        "compared against it, so matches are semantic rather than keyword-based."
    )
    topic = st.text_input(
        "Event, sector or theme",
        placeholder="e.g. crude oil prices rising, or IT services demand slowdown",
        key="exposure_topic",
    )
    if not topic:
        return

    with st.spinner("Comparing your holdings against that theme…"):
        matches = portfolio.exposure(topic)
    if not matches:
        st.info("No holding shows meaningful exposure to that theme.")
        return

    base = config.BASE_CURRENCY
    for match in matches:
        st.markdown(
            f"<div class='leg-row'><span class='leg-name'>{match['symbol']} — "
            f"{html.escape(match['name'][:34])}</span>"
            f"<span>{match['weight']:.1f}% of book · {match['value_in_base']:,.0f} {base}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='meter'><div class='meter-fill meter-lime' "
            f"style='width:{min(100, match['relevance'] * 160):.0f}%'></div></div>"
            f"<div class='hint'>relevance {match['relevance']:.2f} · {match['sector']}</div>",
            unsafe_allow_html=True,
        )

    ask_about(
        f"How is my portfolio exposed to {topic}? Use my holdings and today's news.",
        "Ask the assistant to explain this",
        key="exposure_ask",
    )


def render() -> None:
    panel_header(
        "Your portfolio",
        f"STORED LOCALLY · {config.PORTFOLIO_FILE.name} · BASE {config.BASE_CURRENCY}",
    )

    with st.spinner("Pricing your holdings against the live market…"):
        rows = portfolio.positions()

    if not rows:
        steps(
            [
                ("Add what you own", "Symbol, quantity and your average cost. Indian listings use <code>.NS</code> (NSE) or <code>.BO</code> (BSE) — type the company name and Kinetic resolves it."),
                ("It prices itself live", "Every position is marked to the live market and converted into one currency using a live FX rate."),
                ("Then ask about it", "The assistant can read this book, so “is my portfolio exposed to this?” becomes a real question with a real answer."),
            ]
        )
        hint(
            f"Holdings are written to <code>{config.PORTFOLIO_FILE}</code> on this machine. "
            "Nothing in Kinetic uploads that file — it is why the model runs on your laptop."
        )
        _editor(rows)
        return

    totals = portfolio.summary(rows)
    _totals(totals)
    chips(
        [("live", f"priced {totals['as_of']}")]
        + [("doc", f"{name} {share:.0f}%") for name, share in list(totals["sectors"].items())[:4]]
    )

    table_column, chart_column = st.columns([3, 2])
    with table_column:
        _positions_table(rows)
        hint("Weights are share of market value in the base currency, after FX conversion.")
    with chart_column:
        _allocation_chart(rows, totals)

    st.markdown("**Open a holding**")
    columns = st.columns(min(len(rows), 5))
    for index, row in enumerate(rows):
        if columns[index % len(columns)].button(row.symbol, key=f"open_{row.symbol}", use_container_width=True):
            nav_to("Research", row.symbol)

    left, right = st.columns([3, 2])
    with left:
        _exposure_panel(rows)
    with right:
        st.markdown("**Ask about this book**")
        ask_about("How is my portfolio doing today, and which position is dragging it?",
                  "How am I doing today?", key="pf_ask_today")
        ask_about("What is my biggest concentration risk, given my holdings and their sectors?",
                  "Where is my risk concentrated?", key="pf_ask_risk")
        ask_about("Summarise today's news for each of my holdings and flag anything that matters.",
                  "What's in the news for my holdings?", key="pf_ask_news")
        st.markdown("---")
        with st.expander("Manage holdings"):
            _editor(rows)
        st.markdown(
            f"<div class='hint'>Stored at <code>{config.PORTFOLIO_FILE}</code>. "
            "Never uploaded, never synced.</div>",
            unsafe_allow_html=True,
        )
