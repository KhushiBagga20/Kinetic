"""Research — the market dashboard and the forecast engine, on one symbol."""

from __future__ import annotations

import streamlit as st

from ui import dashboard, forecast


def render() -> None:
    market_tab, forecast_tab = st.tabs(["Live market", "Forecast"])
    with market_tab:
        dashboard.render()
    with forecast_tab:
        forecast.render()
