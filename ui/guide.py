"""How Kinetic works — shown inside the Home view, not as a separate tab."""

from __future__ import annotations

import streamlit as st

import config
from src.llm import engine
from src.rag import stats
from ui.components import hint


def system_status() -> None:
    """A compact readout of which parts of the stack are live."""
    counts = stats()
    ready = engine().is_loaded
    rows = [
        ("Market data", True, "Yahoo Finance — live, no key required"),
        ("News", True, "Yahoo Finance" + (" + NewsAPI" if config.NEWS_API_KEY else "")),
        ("Vector index", counts["documents"] + counts["market_feed"] > 0,
         f"{counts['documents']} document + {counts['market_feed']} live chunks"),
        ("Local model", ready,
         f"{config.LLM_MODEL.split('/')[-1]} — {'loaded' if ready else 'not loaded'}"),
    ]
    body = "".join(
        f"<tr><th scope='row' style='text-align:left'>{name}</th>"
        f"<td style=\"color: {'#CDFF9A' if ok else '#9EB5B7'};\">"
        f"<span aria-hidden='true'>{'●' if ok else '○'}</span> {'READY' if ok else 'PENDING'}</td>"
        f"<td>{detail}</td></tr>"
        for name, ok, detail in rows
    )
    st.markdown(
        "<table class='terminal-table'><caption class='visually-hidden'>System status</caption>"
        "<thead><tr><th scope='col'>Component</th><th scope='col'>State</th>"
        f"<th scope='col'>Detail</th></tr></thead><tbody>{body}</tbody></table>",
        unsafe_allow_html=True,
    )


def how_it_works() -> None:
    """The explanation of the pipeline, for anyone who wants it."""
    st.markdown(
        """
| Stage | What happens |
| --- | --- |
| Retrieve | Your question is embedded and matched against your documents and the live market feed with dense vectors **and** BM25 keyword search; the two rankings are fused and de-duplicated. |
| Ground | The winning passages reach the model labelled `[S1]`, `[S2]`, and it is told to cite them. |
| Act | The model calls live tools — quotes, fundamentals, news, screeners, your portfolio, the forecast engine — whenever it needs a current number. |
| Answer | Text streams to the screen as it is written, and every figure is tagged as live market data or as coming from a named document. |
"""
    )
    hint(
        "Nothing here calls a cloud API. Your documents, your holdings and your questions "
        "stay on this machine — that is why the model runs on it. To check the whole data "
        "stack from a terminal, run <code>python scripts/selfcheck.py</code>."
    )
