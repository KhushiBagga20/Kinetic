"""
Live quotes, history, fundamentals and screeners — sourced from Yahoo Finance.

Every function is cached for a few seconds so a page render never hammers the
API, and every result carries the timestamp it was fetched at, so the UI and
the model can always state how fresh a number is.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

import config

# One lock guards every cache: quotes are fetched from several threads at once
# so a page never waits on symbols in sequence.
_cache_lock = threading.RLock()

_quote_cache: TTLCache = TTLCache(maxsize=512, ttl=config.QUOTE_TTL_SEC)
_info_cache: TTLCache = TTLCache(maxsize=512, ttl=config.FUNDAMENTALS_TTL_SEC)
_history_cache: TTLCache = TTLCache(maxsize=256, ttl=config.HISTORY_TTL_SEC)
_screen_cache: TTLCache = TTLCache(maxsize=32, ttl=config.SCREENER_TTL_SEC)
_search_cache: TTLCache = TTLCache(maxsize=256, ttl=config.FUNDAMENTALS_TTL_SEC)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        value = float(value)
        return None if value != value else value  # drop NaN
    except (TypeError, ValueError):
        return None


# Yahoo reports the session per instrument, which is what actually matters:
# the NSE can be open while US markets are shut.
SESSION_LABELS = {
    "REGULAR": "open",
    "CLOSED": "closed",
    "PRE": "pre-market",
    "PREPRE": "pre-market (early)",
    "POST": "after-hours",
    "POSTPOST": "after-hours (late)",
}


@dataclass
class Quote:
    """A live snapshot of one instrument."""

    symbol: str
    name: str
    price: float | None
    previous_close: float | None
    change: float | None
    change_percent: float | None
    currency: str
    exchange: str
    quote_type: str
    volume: float | None
    market_cap: float | None
    day_low: float | None
    day_high: float | None
    year_low: float | None
    year_high: float | None
    market_state: str
    as_of: str
    source: str = "Yahoo Finance (live)"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        """Compact, unit-explicit rendering for the language model."""
        cur = self.currency
        lines = [f"{self.name} ({self.symbol}) — live quote"]
        if self.price is not None:
            lines.append(f"price: {self.price:,.2f} {cur}")
        if self.change is not None and self.change_percent is not None:
            lines.append(f"change vs previous close: {self.change:+,.2f} {cur} ({self.change_percent:+.2f}%)")
        if self.previous_close is not None:
            lines.append(f"previous close: {self.previous_close:,.2f} {cur}")
        if self.day_low is not None and self.day_high is not None:
            lines.append(f"day range: {self.day_low:,.2f} - {self.day_high:,.2f} {cur}")
        if self.year_low is not None and self.year_high is not None:
            lines.append(f"52-week range: {self.year_low:,.2f} - {self.year_high:,.2f} {cur}")
        if self.volume:
            lines.append(f"volume: {self.volume:,.0f} shares")
        if self.market_cap:
            lines.append(f"market cap: {self.market_cap:,.0f} {cur}")
        if self.market_state:
            lines.append(f"exchange session: {SESSION_LABELS.get(self.market_state, self.market_state)}")
        lines.append(f"source: {self.source}, fetched {self.as_of}")
        return "\n".join(lines)


@cached(_info_cache, key=lambda symbol: hashkey("info", symbol), lock=_cache_lock)
def _info(symbol: str) -> dict[str, Any]:
    """Yahoo's full profile for a symbol (slow, cached longer)."""
    try:
        return dict(yf.Ticker(symbol).info or {})
    except Exception:
        return {}


@cached(_quote_cache, key=lambda symbol: hashkey("quote", symbol), lock=_cache_lock)
def get_quote(symbol: str) -> Quote | None:
    """Fetch the current price and session statistics for one symbol."""
    symbol = symbol.strip().upper()
    if not symbol:
        return None
    try:
        fast = yf.Ticker(symbol).fast_info
        price = _number(fast.get("lastPrice"))
        previous = _number(fast.get("previousClose"))
        if price is None and previous is None:
            return None
        change = price - previous if price is not None and previous else None
        change_pct = (change / previous * 100) if change is not None and previous else None
        info = _info(symbol)
        return Quote(
            symbol=symbol,
            name=info.get("shortName") or info.get("longName") or symbol,
            price=price,
            previous_close=previous,
            change=change,
            change_percent=change_pct,
            currency=fast.get("currency") or info.get("currency") or "USD",
            exchange=fast.get("exchange") or info.get("fullExchangeName") or "",
            quote_type=fast.get("quoteType") or info.get("quoteType") or "",
            volume=_number(fast.get("lastVolume")),
            market_cap=_number(fast.get("marketCap")),
            day_low=_number(fast.get("dayLow")),
            day_high=_number(fast.get("dayHigh")),
            year_low=_number(fast.get("yearLow")),
            year_high=_number(fast.get("yearHigh")),
            market_state=str(info.get("marketState", "")).upper(),
            as_of=_now(),
        )
    except Exception:
        return None


def prefetch(symbols: list[str], with_fundamentals: bool = False) -> None:
    """
    Warm the caches for several symbols at once.

    Yahoo answers each symbol in roughly a second, so a five-holding portfolio
    priced in sequence takes five. Fetching them together makes the page feel
    instant, and the shared cache lock keeps it safe.
    """
    symbols = [s for s in dict.fromkeys(symbols) if s]
    if not symbols:
        return
    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as pool:
        # Profiles first: they are the slow half, and warming them means the
        # quote pass that follows only has to fetch prices.
        if with_fundamentals:
            list(pool.map(_info, symbols))
        list(pool.map(get_quote, symbols))


def get_quotes(symbols: list[str]) -> list[Quote]:
    """Fetch several quotes in parallel, skipping any symbol that fails."""
    prefetch(symbols)
    return [q for q in (get_quote(s) for s in symbols) if q is not None]


@cached(_history_cache, key=lambda symbol, period=None, interval="1d": hashkey("hist", symbol, period, interval), lock=_cache_lock)
def get_history(symbol: str, period: str | None = None, interval: str = "1d") -> pd.DataFrame:
    """Historical OHLCV candles. Returns an empty frame when unavailable."""
    try:
        frame = yf.Ticker(symbol.strip().upper()).history(
            period=period or config.HISTORY_PERIOD, interval=interval, auto_adjust=True
        )
        return frame if frame is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_fundamentals(symbol: str) -> dict[str, Any]:
    """Live valuation, profitability, growth, leverage and analyst metrics."""
    info = _info(symbol.strip().upper())
    if not info:
        return {}
    fields = {
        "name": info.get("shortName") or info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "market_cap": _number(info.get("marketCap")),
        "trailing_pe": _number(info.get("trailingPE")),
        "forward_pe": _number(info.get("forwardPE")),
        "peg_ratio": _number(info.get("trailingPegRatio") or info.get("pegRatio")),
        "price_to_book": _number(info.get("priceToBook")),
        "profit_margin": _number(info.get("profitMargins")),
        "operating_margin": _number(info.get("operatingMargins")),
        "revenue_growth": _number(info.get("revenueGrowth")),
        "earnings_growth": _number(info.get("earningsGrowth")),
        "return_on_equity": _number(info.get("returnOnEquity")),
        "debt_to_equity": _number(info.get("debtToEquity")),
        "current_ratio": _number(info.get("currentRatio")),
        "free_cash_flow": _number(info.get("freeCashflow")),
        "dividend_yield": _number(info.get("dividendYield")),
        "beta": _number(info.get("beta")),
        "target_mean_price": _number(info.get("targetMeanPrice")),
        "recommendation": info.get("recommendationKey"),
        "analyst_count": _number(info.get("numberOfAnalystOpinions")),
        "business_summary": (info.get("longBusinessSummary") or "")[:1200],
        "as_of": _now(),
    }
    return {k: v for k, v in fields.items() if v not in (None, "", [])}


@cached(_search_cache, key=lambda text, limit=8: hashkey("search", text, limit), lock=_cache_lock)
def search_symbols(text: str, limit: int = 8) -> list[dict[str, Any]]:
    """Live symbol lookup, so users can type a company name instead of a ticker."""
    text = text.strip()
    if not text:
        return []
    try:
        results = yf.Search(text, max_results=limit).quotes or []
    except Exception:
        return []
    return [
        {
            "symbol": item.get("symbol", ""),
            "name": item.get("shortname") or item.get("longname") or "",
            "type": item.get("quoteType", ""),
            "exchange": item.get("exchDisp") or item.get("exchange", ""),
        }
        for item in results
        if item.get("symbol")
    ]


def resolve_symbol(text: str) -> str | None:
    """
    Turn free text into a tradable symbol.

    "AAPL" stays "AAPL"; "nvidia" and "reliance industries" are resolved
    through Yahoo's live search index rather than a hardcoded mapping.
    """
    text = text.strip()
    if not text:
        return None
    direct = text.upper()
    if get_quote(direct) is not None:
        return direct
    for match in search_symbols(text, limit=5):
        if match["type"].upper() in {"EQUITY", "ETF", "INDEX", "CRYPTOCURRENCY", "MUTUALFUND"}:
            return match["symbol"]
    return None


@cached(_screen_cache, key=lambda kind="day_gainers", count=8: hashkey("screen", kind, count), lock=_cache_lock)
def get_movers(kind: str = "day_gainers", count: int = 8) -> list[dict[str, Any]]:
    """
    Live screener results (day_gainers, day_losers, most_actives, ...).

    Nothing is stored locally: the universe is whatever Yahoo returns now.
    """
    try:
        payload = yf.screen(kind, count=count) or {}
    except Exception:
        return []
    rows = []
    for item in payload.get("quotes", [])[:count]:
        rows.append(
            {
                "symbol": item.get("symbol", ""),
                "name": item.get("shortName") or item.get("longName") or item.get("symbol", ""),
                "price": _number(item.get("regularMarketPrice")),
                "change_percent": _number(item.get("regularMarketChangePercent")),
                "volume": _number(item.get("regularMarketVolume")),
                "currency": item.get("currency", "USD"),
            }
        )
    return [r for r in rows if r["symbol"]]


def session(symbol: str) -> dict[str, Any]:
    """
    The live trading session for one instrument's exchange.

    Asked per symbol rather than per region, because a portfolio can hold NSE
    and Nasdaq listings whose sessions do not overlap.
    """
    info = _info(symbol.strip().upper())
    state = str(info.get("marketState", "")).upper()
    return {
        "symbol": symbol.upper(),
        "exchange": info.get("fullExchangeName") or info.get("exchange") or "",
        "timezone": info.get("exchangeTimezoneShortName") or "",
        "state": state,
        "label": SESSION_LABELS.get(state, state.lower() or "unknown"),
        "as_of": _now(),
    }


@cached(_quote_cache, key=lambda base, quote: hashkey("fx", base, quote), lock=_cache_lock)
def get_fx_rate(base: str, quote: str) -> float | None:
    """Live exchange rate, e.g. get_fx_rate("USD", "INR"). 1.0 for same currency."""
    base, quote = base.strip().upper(), quote.strip().upper()
    if not base or not quote or base == quote:
        return 1.0
    for symbol in (f"{base}{quote}=X", f"{base}{quote[:3]}=X"):
        try:
            rate = _number(yf.Ticker(symbol).fast_info.get("lastPrice"))
        except Exception:
            rate = None
        if rate:
            return rate
    inverse = get_fx_rate(quote, base) if quote != base else None
    return (1 / inverse) if inverse else None
