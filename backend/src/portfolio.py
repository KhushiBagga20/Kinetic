"""
Portfolio — your actual holdings, priced live, and never sent anywhere.

Positions are stored in one local JSON file (`config.PORTFOLIO_FILE`), which is
git-ignored and read only by this process. Nothing in this module makes an
outbound request except the market-data lookups that price the positions, and
those only ever send a ticker symbol.

Beyond profit and loss, the interesting question is exposure: *which of my
holdings does this news actually touch?* That is answered with the same local
embedding model the retriever uses — the topic and each holding's live profile
are embedded on-device and compared.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

import config
from src.market import get_fundamentals, get_fx_rate, get_news, get_quote, prefetch, session


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@dataclass
class Holding:
    """What you own, as you entered it."""

    symbol: str
    quantity: float
    average_cost: float
    currency: str = ""  # currency the cost was paid in; defaults to the quote's

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    """A holding priced against the live market."""

    symbol: str
    name: str
    quantity: float
    average_cost: float
    currency: str
    price: float | None
    market_value: float | None
    cost_basis: float
    unrealised: float | None
    unrealised_percent: float | None
    day_change_percent: float | None
    day_change_value: float | None
    value_in_base: float | None
    weight: float
    sector: str
    market_session: str
    as_of: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Storage ──────────────────────────────────────────────────────────────────

def load_holdings() -> list[Holding]:
    """Read the local portfolio file. Returns an empty list if there is none."""
    path = config.PORTFOLIO_FILE
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        Holding(
            symbol=str(row.get("symbol", "")).upper(),
            quantity=float(row.get("quantity", 0) or 0),
            average_cost=float(row.get("average_cost", 0) or 0),
            currency=str(row.get("currency", "") or ""),
        )
        for row in payload.get("holdings", [])
        if row.get("symbol")
    ]


def save_holdings(holdings: list[Holding]) -> None:
    """Write the portfolio back to disk, and nowhere else."""
    config.PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PORTFOLIO_FILE.write_text(
        json.dumps(
            {
                "base_currency": config.BASE_CURRENCY,
                "updated": _now(),
                "holdings": [h.as_dict() for h in holdings],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def add_holding(symbol: str, quantity: float, average_cost: float) -> list[Holding]:
    """Add a position, or merge into an existing one at a blended cost."""
    symbol = symbol.strip().upper()
    holdings = load_holdings()
    for holding in holdings:
        if holding.symbol == symbol:
            total = holding.quantity + quantity
            if total > 0:
                holding.average_cost = (
                    holding.quantity * holding.average_cost + quantity * average_cost
                ) / total
            holding.quantity = total
            break
    else:
        holdings.append(Holding(symbol=symbol, quantity=quantity, average_cost=average_cost))
    save_holdings(holdings)
    return holdings


def remove_holding(symbol: str) -> list[Holding]:
    holdings = [h for h in load_holdings() if h.symbol != symbol.strip().upper()]
    save_holdings(holdings)
    return holdings


# ─── Live pricing ─────────────────────────────────────────────────────────────

def positions() -> list[Position]:
    """Price every holding against the live market, converted to one currency."""
    holdings = load_holdings()
    if not holdings:
        return []

    # Price every holding concurrently rather than one after another.
    prefetch([h.symbol for h in holdings], with_fundamentals=True)

    rows: list[Position] = []
    for holding in holdings:
        quote = get_quote(holding.symbol)
        fundamentals = get_fundamentals(holding.symbol)
        currency = holding.currency or (quote.currency if quote else config.BASE_CURRENCY)
        cost_basis = holding.quantity * holding.average_cost

        price = quote.price if quote else None
        market_value = price * holding.quantity if price is not None else None
        unrealised = (market_value - cost_basis) if market_value is not None else None
        rate = get_fx_rate(currency, config.BASE_CURRENCY) or 1.0

        rows.append(
            Position(
                symbol=holding.symbol,
                name=quote.name if quote else holding.symbol,
                quantity=holding.quantity,
                average_cost=holding.average_cost,
                currency=currency,
                price=price,
                market_value=market_value,
                cost_basis=cost_basis,
                unrealised=unrealised,
                unrealised_percent=(unrealised / cost_basis * 100) if unrealised is not None and cost_basis else None,
                day_change_percent=quote.change_percent if quote else None,
                day_change_value=(
                    quote.change * holding.quantity if quote and quote.change is not None else None
                ),
                value_in_base=(market_value * rate) if market_value is not None else None,
                weight=0.0,  # filled in below, once the total is known
                sector=str(fundamentals.get("sector", "") or ""),
                market_session=(quote.market_state if quote else ""),
                as_of=_now(),
            )
        )

    total = sum(row.value_in_base or 0.0 for row in rows)
    for row in rows:
        row.weight = ((row.value_in_base or 0.0) / total * 100) if total else 0.0
    return sorted(rows, key=lambda r: r.value_in_base or 0.0, reverse=True)


def summary(rows: list[Position] | None = None) -> dict[str, Any]:
    """
    Portfolio totals, concentration and sector mix, in the base currency.

    Pass `rows` from an earlier `positions()` call to avoid re-pricing the book
    when a view needs both.
    """
    rows = positions() if rows is None else rows
    if not rows:
        return {"holdings": 0, "base_currency": config.BASE_CURRENCY, "as_of": _now()}

    value = sum(r.value_in_base or 0.0 for r in rows)
    cost = sum(
        (r.cost_basis * (get_fx_rate(r.currency, config.BASE_CURRENCY) or 1.0)) for r in rows
    )
    day = sum(
        (r.day_change_value or 0.0) * (get_fx_rate(r.currency, config.BASE_CURRENCY) or 1.0)
        for r in rows
    )

    sectors: dict[str, float] = {}
    for row in rows:
        label = row.sector or "Unclassified"
        sectors[label] = sectors.get(label, 0.0) + (row.value_in_base or 0.0)

    return {
        "holdings": len(rows),
        "base_currency": config.BASE_CURRENCY,
        "market_value": value,
        "cost_basis": cost,
        "unrealised": value - cost,
        "unrealised_percent": ((value - cost) / cost * 100) if cost else 0.0,
        "day_change": day,
        "day_change_percent": (day / (value - day) * 100) if (value - day) else 0.0,
        "largest_position": rows[0].symbol,
        "largest_weight": rows[0].weight,
        "sectors": {k: (v / value * 100 if value else 0.0) for k, v in sorted(
            sectors.items(), key=lambda item: item[1], reverse=True
        )},
        "as_of": _now(),
    }


# ─── Exposure ─────────────────────────────────────────────────────────────────

def _profile(position: Position) -> str:
    """A short live description of a holding, used for semantic matching."""
    fundamentals = get_fundamentals(position.symbol)
    headlines = " ".join(article.title for article in get_news(position.symbol, limit=4))
    return " ".join(
        part
        for part in (
            position.name,
            position.symbol,
            fundamentals.get("sector", ""),
            fundamentals.get("industry", ""),
            (fundamentals.get("business_summary", "") or "")[:400],
            headlines,
        )
        if part
    )


def exposure(topic: str, threshold: float = 0.2) -> list[dict[str, Any]]:
    """
    Which holdings are exposed to a topic — a news event, a sector, a commodity.

    The topic and each holding's live profile (business summary, sector and
    recent headlines) are embedded locally and compared by cosine similarity,
    so this works for phrasings no keyword rule would catch.
    """
    from src.rag.embeddings import embed, embed_query

    rows = positions()
    if not rows or not topic.strip():
        return []

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(8, len(rows))) as pool:
        profiles = list(pool.map(_profile, rows))
    vectors = np.asarray(embed(profiles), dtype=np.float32)
    topic_vector = np.asarray(embed_query(topic), dtype=np.float32)
    scores = vectors @ topic_vector

    matches = []
    for row, score in zip(rows, scores):
        if float(score) < threshold:
            continue
        matches.append(
            {
                "symbol": row.symbol,
                "name": row.name,
                "relevance": round(float(score), 3),
                "weight": round(row.weight, 2),
                "value_in_base": row.value_in_base,
                "sector": row.sector or "Unclassified",
                "day_change_percent": row.day_change_percent,
            }
        )
    return sorted(matches, key=lambda m: m["relevance"], reverse=True)


# ─── Text rendering for the agent ─────────────────────────────────────────────

def to_text() -> str:
    """The portfolio as the model should see it: explicit units, explicit time."""
    rows = positions()
    if not rows:
        return (
            "The portfolio is empty. Holdings can be added in the Portfolio tab; "
            "they are stored locally and never leave this machine."
        )

    totals = summary(rows)
    base = totals["base_currency"]
    lines = [
        f"Portfolio ({totals['holdings']} holdings, valued {totals['as_of']}, base currency {base}):",
        f"- market value: {totals['market_value']:,.2f} {base}",
        f"- cost basis: {totals['cost_basis']:,.2f} {base}",
        f"- unrealised P&L: {totals['unrealised']:+,.2f} {base} ({totals['unrealised_percent']:+.2f}%)",
        f"- today's change: {totals['day_change']:+,.2f} {base} ({totals['day_change_percent']:+.2f}%)",
        f"- largest position: {totals['largest_position']} at {totals['largest_weight']:.1f}% of the book",
        "",
        "Positions:",
    ]
    for row in rows:
        price = f"{row.price:,.2f} {row.currency}" if row.price is not None else "no live price"
        pnl = (
            f"{row.unrealised:+,.2f} {row.currency} ({row.unrealised_percent:+.2f}%)"
            if row.unrealised is not None
            else "unrealised P&L unavailable"
        )
        lines.append(
            f"- {row.symbol} ({row.name}): {row.quantity:g} units at an average cost of "
            f"{row.average_cost:,.2f} {row.currency}; last {price}; {pnl}; "
            f"{row.weight:.1f}% of the book; sector {row.sector or 'unclassified'}"
        )
    if totals.get("sectors"):
        mix = ", ".join(f"{name} {share:.1f}%" for name, share in totals["sectors"].items())
        lines.append(f"\nSector mix: {mix}")
    return "\n".join(lines)
