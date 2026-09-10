"""
Home — the personalised view.

It opens on the user's own book and watchlist rather than a generic market
screen, tells them what changed since they last looked, and puts the next
useful action one click away.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

import config
from src import portfolio, preferences
from src.llm import engine
from src.market import get_quotes, session
from ui.components import (
    arrow,
    ask_about,
    chips,
    hint,
    metric_tile,
    model_control,
    nav_to,
    panel_header,
    steps,
)
from ui.guide import how_it_works, system_status


def _time_of_day() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _greeting(prefs: preferences.Preferences) -> None:
    name = prefs.greeting_name
    title = f"{_time_of_day()}{',  ' + html.escape(name) if name else ''}"
    marker = session(config.DEFAULT_SYMBOL)
    st.markdown(
        f"""
        <div style="margin: 2px 0 10px 0;">
            <div style="font-family: var(--k-font-sans); font-size: 1.5rem; font-weight: 700;
                        color: #FFFFFF; letter-spacing: -0.02em;">{title}</div>
            <div class="hint">{marker['exchange'] or 'Market'} is
                <strong style="color:#CDFF9A;">{marker['label']}</strong> ·
                {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _book_summary(rows: list) -> dict:
    if not rows:
        return {}

    totals = portfolio.summary(rows)
    base = totals["base_currency"]
    movers = [r for r in rows if r.day_change_percent is not None]
    best = max(movers, key=lambda r: r.day_change_percent, default=None)
    worst = min(movers, key=lambda r: r.day_change_percent, default=None)

    columns = st.columns(4)
    with columns[0]:
        metric_tile("Your book", f"{totals['market_value']:,.0f} {base}")
    with columns[1]:
        metric_tile(
            "Today",
            f"{totals['day_change']:+,.0f} {base}",
            f"{totals['day_change_percent']:+.2f}%",
            positive=totals["day_change"] >= 0,
        )
    with columns[2]:
        metric_tile(
            "Best today",
            best.symbol if best else "—",
            f"{best.day_change_percent:+.2f}%" if best else "",
            positive=True if best and best.day_change_percent >= 0 else False,
        )
    with columns[3]:
        metric_tile(
            "Weakest today",
            worst.symbol if worst else "—",
            f"{worst.day_change_percent:+.2f}%" if worst else "",
            positive=True if worst and worst.day_change_percent >= 0 else False,
        )
    return totals


def _attention(rows: list, totals: dict) -> None:
    """Only surface a position when there is a reason to look at it."""
    flags: list[tuple[str, str]] = []

    for row in rows:
        if row.day_change_percent is not None and abs(row.day_change_percent) >= 3:
            direction = "up" if row.day_change_percent > 0 else "down"
            flags.append((row.symbol, f"moved {direction} {abs(row.day_change_percent):.1f}% today"))
        elif row.unrealised_percent is not None and row.unrealised_percent <= -20:
            flags.append((row.symbol, f"down {abs(row.unrealised_percent):.0f}% against your cost"))

    if totals.get("largest_weight", 0) >= 40:
        flags.append((totals["largest_position"], f"is {totals['largest_weight']:.0f}% of the whole book"))

    if not flags:
        hint("Nothing in your book moved sharply today.")
        return

    st.markdown("**Worth a look**")
    for symbol, reason in flags[:4]:
        row_columns = st.columns([4, 1])
        row_columns[0].markdown(
            f"<div class='leg-row'><span class='leg-name'>{symbol}</span>"
            f"<span>{reason}</span></div>",
            unsafe_allow_html=True,
        )
        if row_columns[1].button("Open", key=f"attn_{symbol}", use_container_width=True):
            nav_to("Research", symbol)


def _watchlist(prefs: preferences.Preferences) -> None:
    st.markdown("**Your watchlist**")
    if not prefs.watchlist:
        hint("Nothing on the watchlist yet — add symbols from the sidebar.")
        return

    quotes = get_quotes(prefs.watchlist)
    if not quotes:
        hint("The watchlist quotes did not come back — the data provider may be rate-limiting.")
        return

    for quote in quotes:
        up = (quote.change_percent or 0) >= 0
        colour = "#CDFF9A" if up else "#DF4100"
        line, button = st.columns([4, 1])
        line.markdown(
            f"<div class='leg-row'><span class='leg-name'>{quote.symbol}</span>"
            f"<span>{quote.price:,.2f} {quote.currency} "
            f"<span style='color:{colour}'><span aria-hidden='true'>{arrow(up)}</span> "
            f"{quote.change_percent:+.2f}%</span></span></div>",
            unsafe_allow_html=True,
        )
        if button.button("Open", key=f"watch_{quote.symbol}", use_container_width=True):
            nav_to("Research", quote.symbol)


def _first_run(prefs: preferences.Preferences) -> None:
    st.markdown(
        "Kinetic is an investment research terminal that runs entirely on this machine. "
        "It reads live market data, searches your own documents, and answers with a model "
        "that never sends your questions — or your holdings — anywhere."
    )
    steps(
        [
            ("Tell it who you are", "Open <strong>Your profile</strong> in the sidebar and add your name, currency and horizon. Answers are written for you, not for a generic investor."),
            ("Add what you own", "In <strong>Portfolio</strong>, enter your holdings. They are priced live and stored in a local file that is never uploaded."),
            ("Load the model", "Press <strong>LOAD MODEL</strong> in the sidebar when you want to chat — about a minute, roughly 15 GB. Everything else works without it."),
            ("Ask a real question", "“Is my portfolio exposed to a rupee fall?” — it will read your holdings, pull today's data and tell you, with sources."),
        ]
    )
    setup_column, status_column = st.columns([3, 2])
    with setup_column:
        with st.form("first_run_profile"):
            st.markdown("**Set up in ten seconds**")
            name = st.text_input("What should Kinetic call you?", value=prefs.name)
            horizon = st.selectbox("Investing horizon", preferences.HORIZONS,
                                   index=preferences.HORIZONS.index(prefs.horizon))
            if st.form_submit_button("Save and continue", type="primary"):
                preferences.update(name=name, horizon=horizon)
                st.rerun()
    with status_column:
        model_control(key="home")


def render() -> None:
    prefs = preferences.load()
    holdings = portfolio.load_holdings()

    panel_header(
        "Home",
        f"{prefs.risk_appetite.upper()} · {prefs.horizon.upper()} · BASE {prefs.base_currency}"
        if prefs.name
        else "LOCAL-FIRST INVESTMENT RESEARCH",
    )
    _greeting(prefs)

    if not holdings and not prefs.name:
        _first_run(prefs)
        with st.expander("How Kinetic answers a question"):
            how_it_works()
            system_status()
        return

    if holdings:
        with st.spinner("Pricing your book…"):
            rows = portfolio.positions()
        totals = _book_summary(rows)
        chips([("live", f"{len(rows)} holdings priced live"),
               ("doc", f"base currency {prefs.base_currency}")])
    else:
        rows, totals = [], {}
        st.info("No holdings yet. Add them in **Portfolio** to make this page yours.", icon="📌")

    left, right = st.columns([3, 2])
    with left:
        if rows:
            _attention(rows, totals)
        st.markdown("**Ask about your position**")
        ask_column_one, ask_column_two = st.columns(2)
        with ask_column_one:
            ask_about("How is my portfolio doing today, and what drove the move?",
                      "How is my book today?", key="home_ask_book")
            ask_about("What are the biggest moves in the market right now, and do any of them touch my holdings?",
                      "What's moving, and does it touch me?", key="home_ask_market")
        with ask_column_two:
            ask_about("What is my biggest concentration risk right now?",
                      "Where am I over-exposed?", key="home_ask_risk")
            ask_about("Summarise today's headlines for my holdings and flag what matters.",
                      "News on what I own", key="home_ask_news")
    with right:
        _watchlist(prefs)
        st.markdown("---")
        if not engine().is_loaded:
            model_control(key="home")

    with st.expander("How Kinetic answers a question"):
        how_it_works()
        system_status()
