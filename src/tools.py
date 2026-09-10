"""
Agent tools — the only way the model touches the outside world.

Each tool returns plain text with explicit units and an explicit source line,
because a financial answer that does not say "USD" or "as of when" is not an
answer. The same registry backs both the in-app agent and the MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import config
from src import market, portfolio, prediction
from src.rag import format_context, retrieve
from src.rag.ingest import ingest_market_feed


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    required: list[str]
    run: Callable[..., str]

    def schema(self) -> dict[str, Any]:
        """OpenAI-style function schema, understood by Gemma's chat template."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }


REGISTRY: dict[str, Tool] = {}


def _fetched_at() -> str:
    """Every tool result states when it was fetched, so the model never has to
    guess a timestamp — and never invents one."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def tool(description: str, parameters: dict[str, dict[str, Any]], required: list[str] | None = None):
    """Register a function as a callable tool."""

    def decorator(function: Callable[..., str]) -> Callable[..., str]:
        REGISTRY[function.__name__] = Tool(
            name=function.__name__,
            description=description,
            parameters=parameters,
            required=required if required is not None else list(parameters),
            run=function,
        )
        return function

    return decorator


def schemas() -> list[dict[str, Any]]:
    return [t.schema() for t in REGISTRY.values()]


def call(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name. Errors come back as text the model can react to."""
    entry = REGISTRY.get(name)
    if entry is None:
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(REGISTRY)}."
    try:
        clean = {k: v for k, v in (arguments or {}).items() if k in entry.parameters}
        return entry.run(**clean)
    except TypeError as exc:
        return f"Error calling {name}: {exc}. Required arguments: {entry.required}."
    except Exception as exc:
        return f"Error calling {name}: {type(exc).__name__}: {exc}"


# ─── Market tools ─────────────────────────────────────────────────────────────

@tool(
    description=(
        "Resolve a company name or partial text into an exchange ticker symbol "
        "using a live symbol search. Call this first whenever the user names a "
        "company rather than a ticker."
    ),
    parameters={"company": {"type": "string", "description": "Company or fund name, e.g. 'nvidia'."}},
)
def resolve_ticker(company: str) -> str:
    matches = market.search_symbols(company, limit=5)
    if not matches:
        return f"No symbol found for '{company}'."
    lines = [f"Symbol matches for '{company}' (live search):"]
    lines += [f"- {m['symbol']}: {m['name']} [{m['type']}, {m['exchange']}]" for m in matches]
    lines.append(f"source: Yahoo Finance symbol search, fetched {_fetched_at()}")
    return "\n".join(lines)


@tool(
    description=(
        "Get the current live price and session statistics for one ticker: last "
        "price, change versus previous close, day and 52-week ranges, volume and "
        "market capitalisation. Prices are returned in the instrument's own "
        "currency (USD for US listings, INR for .NS/.BO listings)."
    ),
    parameters={"symbol": {"type": "string", "description": "Ticker, e.g. 'AAPL', 'RELIANCE.NS', '^GSPC'."}},
)
def get_stock_quote(symbol: str) -> str:
    quote = market.get_quote(symbol)
    if quote is None:
        return f"No live quote available for '{symbol}'. Check the symbol with resolve_ticker."
    return quote.to_text()


@tool(
    description=(
        "Summarise historical price action for a ticker over a period: total "
        "return, high, low, realised volatility and the current technical "
        "indicator readings (RSI, MACD, moving averages, Bollinger position)."
    ),
    parameters={
        "symbol": {"type": "string", "description": "Ticker symbol."},
        "period": {
            "type": "string",
            "description": "Look-back window: 1mo, 3mo, 6mo, 1y, 2y, 5y, max. Defaults to 6mo.",
        },
    },
    required=["symbol"],
)
def get_price_history(symbol: str, period: str = "") -> str:
    from src import indicators

    symbol = symbol.upper()
    history = market.get_history(symbol, period=period or None)
    if history.empty:
        return f"No price history available for '{symbol}'."
    close = history["Close"].dropna()
    total_return = float(close.iloc[-1] / close.iloc[0] - 1) * 100
    computed = indicators.compute_all(history)
    quote = market.get_quote(symbol)
    currency = quote.currency if quote else ""

    lines = [
        f"{symbol} price history over {period or config.HISTORY_PERIOD} "
        f"({len(close)} sessions, {close.index[0]:%Y-%m-%d} to {close.index[-1]:%Y-%m-%d}):",
        f"- first close {float(close.iloc[0]):,.2f} {currency}, last close {float(close.iloc[-1]):,.2f} {currency}",
        f"- total return {total_return:+.2f}%",
        f"- period high {float(close.max()):,.2f} {currency}, period low {float(close.min()):,.2f} {currency}",
    ]
    lines += [f"- {computed[name]['note']}" for name in computed if computed[name]["value"] is not None]
    lines.append(f"source: Yahoo Finance historical candles, fetched {_fetched_at()}")
    return "\n".join(lines)


@tool(
    description=(
        "Get live fundamentals for a company: valuation multiples (P/E, forward "
        "P/E, PEG, price/book), profitability (margins, return on equity), growth "
        "rates, leverage, free cash flow, dividend yield and the analyst consensus "
        "target. Use for questions about whether a company is expensive, growing "
        "or profitable."
    ),
    parameters={"symbol": {"type": "string", "description": "Ticker symbol."}},
)
def get_company_fundamentals(symbol: str) -> str:
    data = market.get_fundamentals(symbol)
    if not data:
        return f"No fundamental data available for '{symbol}'."
    currency = data.get("currency", "")
    percent_fields = {
        "profit_margin", "operating_margin", "revenue_growth",
        "earnings_growth", "return_on_equity", "dividend_yield",
    }
    money_fields = {"market_cap", "free_cash_flow", "target_mean_price"}

    lines = [f"Live fundamentals for {data.get('name', symbol)} ({symbol.upper()}):"]
    for key, value in data.items():
        if key in {"as_of", "name", "business_summary"}:
            continue
        label = key.replace("_", " ")
        if key in percent_fields and isinstance(value, (int, float)):
            lines.append(f"- {label}: {value * 100:.2f}%")
        elif key in money_fields and isinstance(value, (int, float)):
            lines.append(f"- {label}: {value:,.0f} {currency}")
        elif isinstance(value, float):
            lines.append(f"- {label}: {value:,.2f}")
        else:
            lines.append(f"- {label}: {value}")
    lines.append(f"source: Yahoo Finance company profile, fetched {data.get('as_of', '')}")
    return "\n".join(lines)


@tool(
    description=(
        "Fetch recent news headlines for a ticker or a market topic, newest "
        "first, with publisher and publication time. Use for questions about "
        "what is happening now, catalysts, or why a stock moved."
    ),
    parameters={
        "query": {"type": "string", "description": "Ticker such as 'NVDA' or a topic such as 'oil prices'."},
        "limit": {"type": "integer", "description": "How many headlines to return (default 5)."},
    },
    required=["query"],
)
def get_market_news(query: str, limit: int = 5) -> str:
    articles = market.get_news(query, limit=int(limit or 5))
    if not articles:
        return f"No recent news found for '{query}'."
    lines = [f"Live headlines for '{query}' (newest first):"]
    for index, article in enumerate(articles, 1):
        lines.append(f"{index}. {article.title} — {article.publisher}, {article.published}")
        if article.summary:
            lines.append(f"   {article.summary[:220]}")
    lines.append(f"source: Yahoo Finance / NewsAPI live news feed, fetched {_fetched_at()}")
    return "\n".join(lines)


@tool(
    description=(
        "List the biggest movers on the market right now from a live screener. "
        "Use for 'what is moving today' style questions."
    ),
    parameters={
        "kind": {
            "type": "string",
            "description": "One of day_gainers, day_losers, most_actives, undervalued_growth_stocks, growth_technology_stocks.",
        },
        "limit": {"type": "integer", "description": "How many rows (default 8)."},
    },
    required=[],
)
def get_market_movers(kind: str = "day_gainers", limit: int = 8) -> str:
    rows = market.get_movers(kind or "day_gainers", count=int(limit or 8))
    if not rows:
        return f"No screener results available for '{kind}'."
    lines = [f"Live screener '{kind}':"]
    for row in rows:
        lines.append(
            f"- {row['symbol']} ({row['name']}): {row['price']:,.2f} {row['currency']}, "
            f"{row['change_percent']:+.2f}% today"
        )
    lines.append(f"source: Yahoo Finance screener (live), fetched {_fetched_at()}")
    return "\n".join(lines)


# ─── Knowledge tools ──────────────────────────────────────────────────────────

@tool(
    description=(
        "Search the user's indexed knowledge base — their own uploaded financial "
        "documents plus captured live market snapshots — and return the most "
        "relevant passages with source labels. Use this for anything that should "
        "be grounded in the user's filings, fact sheets or notes."
    ),
    parameters={
        "query": {"type": "string", "description": "What to look for, in natural language."},
        "k": {"type": "integer", "description": "Number of passages to return (default 5)."},
    },
    required=["query"],
)
def search_documents(query: str, k: int = 0) -> str:
    passages = retrieve(query, k=int(k or config.RETRIEVAL_K))
    if not passages:
        return (
            "No indexed passages matched that query. The knowledge base may be "
            "empty — documents can be added from the Knowledge tab."
        )
    header = f"Retrieved passages (cite them as [S1], [S2], ...), searched {_fetched_at()}:"
    return f"{header}\n\n" + format_context(passages)


@tool(
    description=(
        "Capture the current quote, fundamentals and headlines for a symbol into "
        "the vector store so they become retrievable evidence. Use when the user "
        "asks to track, watch or remember a symbol."
    ),
    parameters={"symbol": {"type": "string", "description": "Ticker symbol to snapshot."}},
)
def index_live_market_data(symbol: str) -> str:
    written = ingest_market_feed(symbol)
    if not written:
        return f"Could not capture live data for '{symbol}'."
    return f"Indexed {written} live passages for {symbol.upper()} into the market feed collection."


# ─── Portfolio tools ──────────────────────────────────────────────────────────

@tool(
    description=(
        "Read the user's own portfolio: every holding with its quantity, average "
        "cost, live price, unrealised profit or loss, weight in the book and "
        "sector, plus portfolio totals in the base currency. The data is stored "
        "only on this machine. Use it for any question containing 'my', such as "
        "'how is my portfolio doing' or 'what do I hold in banking'."
    ),
    parameters={},
    required=[],
)
def get_portfolio() -> str:
    return portfolio.to_text()


@tool(
    description=(
        "Find which of the user's holdings are exposed to a topic — a news "
        "event, a sector, a commodity, a regulation. Matching is semantic, so "
        "'rupee weakness' or 'AI capex slowdown' will surface the right "
        "positions even when those words appear nowhere in the holdings. Use it "
        "whenever the user asks how something affects them or their portfolio."
    ),
    parameters={
        "topic": {
            "type": "string",
            "description": "The event, sector or theme to test the portfolio against.",
        }
    },
)
def get_portfolio_exposure(topic: str) -> str:
    matches = portfolio.exposure(topic)
    if not matches:
        holdings = portfolio.load_holdings()
        if not holdings:
            return "The portfolio is empty, so there is no exposure to assess."
        return f"No holding shows meaningful exposure to '{topic}'."

    base = config.BASE_CURRENCY
    lines = [f"Portfolio exposure to '{topic}' (semantic match against live company profiles):"]
    for match in matches:
        value = f"{match['value_in_base']:,.0f} {base}" if match["value_in_base"] else "value unavailable"
        day = f"{match['day_change_percent']:+.2f}% today" if match["day_change_percent"] is not None else ""
        lines.append(
            f"- {match['symbol']} ({match['name']}): relevance {match['relevance']:.2f}, "
            f"{match['weight']:.1f}% of the book, {value}, sector {match['sector']}"
            + (f", {day}" if day else "")
        )
    lines.append(f"assessed {_fetched_at()} against live prices and headlines")
    return "\n".join(lines)


# ─── Analysis tool ────────────────────────────────────────────────────────────

@tool(
    description=(
        "Run the Kinetic ensemble forecast for a symbol. Combines technical "
        "indicators, live news sentiment, live fundamentals and the user's own "
        "documents into a directional signal with a confidence score, a risk "
        "score out of 10 and a volatility-implied expected range. Use this when "
        "the user asks what a stock might do, or whether it looks strong or weak."
    ),
    parameters={
        "symbol": {"type": "string", "description": "Ticker symbol."},
        "horizon_days": {"type": "integer", "description": "Trading sessions to project (default 10)."},
    },
    required=["symbol"],
)
def get_forecast(symbol: str, horizon_days: int = 0) -> str:
    result = prediction.forecast(symbol, horizon_days=int(horizon_days) or None)
    if result is None:
        return f"Could not build a forecast for '{symbol}' — no live market data."
    text = result.to_text()
    for leg in result.legs.values():
        for note in leg.notes[:3]:
            text += f"\n  · {leg.name}: {note}"
    return text
