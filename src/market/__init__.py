"""Live market data. Every value returned here comes from a network call."""

import logging

# yfinance logs a stack-trace-like block whenever a symbol does not resolve.
# Symbol resolution probes unknown symbols by design, so keep the console clean.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


from src.market.quotes import (
    Quote,
    get_fundamentals,
    get_fx_rate,
    get_history,
    get_movers,
    get_quote,
    get_quotes,
    prefetch,
    resolve_symbol,
    search_symbols,
    session,
)
from src.market.news import Article, get_news

__all__ = [
    "Article",
    "Quote",
    "get_fundamentals",
    "get_fx_rate",
    "get_history",
    "get_movers",
    "get_news",
    "get_quote",
    "get_quotes",
    "prefetch",
    "resolve_symbol",
    "search_symbols",
    "session",
]
