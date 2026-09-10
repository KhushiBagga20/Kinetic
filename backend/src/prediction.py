"""
Forecast engine — a transparent ensemble over live inputs.

Four independent legs are scored on the same -1..+1 scale and combined with
configurable weights. Weights are renormalised over the legs that actually
returned data, so a missing input never silently drags a score toward zero.

    technical    live OHLCV → RSI, MACD, MA structure, bands, momentum, volume
    sentiment    live headlines → VADER + a finance-specific lexicon
    fundamental  live ratios → valuation, growth, profitability, leverage
    documents    your indexed corpus → retrieved evidence about this symbol

The expected range is not a prediction of the price: it is the 1-sigma band
implied by realised volatility, which is the honest statistical statement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config
from src import indicators
from src.market import get_fundamentals, get_history, get_news, get_quote
from src.rag import retrieve

_vader = SentimentIntensityAnalyzer()

# VADER was trained on general English; these carry specific meaning in markets.
FINANCE_LEXICON = {
    "beat": 2.5, "beats": 2.5, "upgrade": 2.5, "upgraded": 2.5, "outperform": 2.0,
    "record": 1.8, "surge": 2.2, "rally": 2.0, "guidance raised": 2.5, "buyback": 1.5,
    "dividend": 1.0, "profit": 1.5, "growth": 1.2, "expansion": 1.2, "tailwind": 1.5,
    "miss": -2.5, "misses": -2.5, "downgrade": -2.5, "downgraded": -2.5,
    "underperform": -2.0, "plunge": -2.5, "slump": -2.0, "lawsuit": -1.8,
    "probe": -1.5, "investigation": -1.8, "recall": -1.8, "layoff": -1.5,
    "layoffs": -1.5, "bankruptcy": -3.0, "default": -2.5, "impairment": -1.8,
    "headwind": -1.5, "warning": -1.8, "cut": -1.2, "delay": -1.0,
}
_vader.lexicon.update(FINANCE_LEXICON)


def _clamp(value: float) -> float:
    return float(max(-1.0, min(1.0, value)))


@dataclass
class Leg:
    """One scored component of the ensemble."""

    name: str
    score: float = 0.0
    weight: float = 0.0
    available: bool = False
    notes: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Forecast:
    symbol: str
    name: str
    price: float | None
    currency: str
    signal: str
    direction: float
    confidence: float
    risk_score: int
    risk_label: str
    horizon_days: int
    expected_low: float | None
    expected_high: float | None
    legs: dict[str, Leg]
    drivers: list[str]
    data_quality: str
    as_of: str
    disclaimer: str = config.DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["legs"] = {name: asdict(leg) for name, leg in self.legs.items()}
        return payload

    def to_text(self) -> str:
        """Model-readable summary with every number carrying its unit."""
        lines = [
            f"Forecast for {self.name} ({self.symbol}) — generated {self.as_of}",
            f"signal: {self.signal} (direction score {self.direction:+.2f} on -1..+1)",
            f"confidence: {self.confidence:.0f}% | risk: {self.risk_label} ({self.risk_score}/10)",
        ]
        if self.price is not None:
            lines.append(f"last price: {self.price:,.2f} {self.currency}")
        if self.expected_low is not None:
            lines.append(
                f"{self.horizon_days}-session 1-sigma range: "
                f"{self.expected_low:,.2f} – {self.expected_high:,.2f} {self.currency} "
                f"(≈68% of historical outcomes, from realised volatility)"
            )
        for leg in self.legs.values():
            state = f"{leg.score:+.2f} at {leg.weight * 100:.0f}% weight" if leg.available else "no data"
            lines.append(f"- {leg.name}: {state}")
        if self.drivers:
            lines.append("key drivers: " + "; ".join(self.drivers))
        lines.append(f"data quality: {self.data_quality}")
        return "\n".join(lines)


# ─── Legs ─────────────────────────────────────────────────────────────────────

def _technical_leg(history) -> Leg:
    leg = Leg(name="Technical")
    if history is None or history.empty or len(history) < 30:
        leg.notes.append("Insufficient price history for technical analysis")
        return leg
    computed = indicators.compute_all(history)
    leg.score = _clamp(indicators.technical_score(computed))
    leg.available = True
    leg.detail = computed
    leg.notes = [
        computed[name]["note"]
        for name in indicators.DIRECTIONAL
        if computed.get(name, {}).get("value") is not None
    ]
    return leg


def _score_headline(text: str) -> float:
    return float(_vader.polarity_scores(text)["compound"])


def _sentiment_leg(symbol: str) -> Leg:
    leg = Leg(name="News sentiment")
    articles = get_news(symbol)
    if not articles:
        leg.notes.append("No recent headlines found")
        return leg

    scored = []
    for position, article in enumerate(articles):
        text = f"{article.title}. {article.summary}".strip()
        # Newer headlines matter more; weights decay geometrically down the feed.
        weight = 0.85 ** position
        scored.append((_score_headline(text), weight, article))

    total_weight = sum(w for _, w, _ in scored) or 1.0
    leg.score = _clamp(sum(s * w for s, w, _ in scored) / total_weight * 1.6)
    leg.available = True
    leg.detail = {
        "articles": [
            {
                "title": a.title,
                "publisher": a.publisher,
                "published": a.published,
                "url": a.url,
                "sentiment": round(s, 3),
            }
            for s, _, a in scored
        ],
        "headline_count": len(scored),
    }
    positive = sum(1 for s, _, _ in scored if s > 0.15)
    negative = sum(1 for s, _, _ in scored if s < -0.15)
    leg.notes.append(
        f"{len(scored)} live headlines: {positive} positive, {negative} negative, "
        f"{len(scored) - positive - negative} neutral"
    )
    strongest = max(scored, key=lambda item: abs(item[0]))
    if abs(strongest[0]) > 0.3:
        leg.notes.append(f"Strongest tone: \"{strongest[2].title[:110]}\" ({strongest[0]:+.2f})")
    return leg


def _fundamental_leg(symbol: str, price: float | None) -> Leg:
    """Score live valuation, growth, profitability, leverage and analyst view."""
    leg = Leg(name="Fundamentals")
    data = get_fundamentals(symbol)
    if not data:
        leg.notes.append("No fundamental data available for this instrument")
        return leg

    parts: list[float] = []

    growth = data.get("revenue_growth")
    if growth is not None:
        parts.append(_clamp(growth * 4))
        leg.notes.append(f"Revenue growth {growth * 100:+.1f}% year over year")

    earnings = data.get("earnings_growth")
    if earnings is not None:
        parts.append(_clamp(earnings * 2.5))
        leg.notes.append(f"Earnings growth {earnings * 100:+.1f}% year over year")

    margin = data.get("profit_margin")
    if margin is not None:
        parts.append(_clamp((margin - 0.08) * 6))
        leg.notes.append(f"Net profit margin {margin * 100:.1f}%")

    roe = data.get("return_on_equity")
    if roe is not None:
        parts.append(_clamp((roe - 0.12) * 3))
        leg.notes.append(f"Return on equity {roe * 100:.1f}%")

    peg = data.get("peg_ratio")
    if peg is not None and peg > 0:
        # PEG near 1 is fair value; below is cheap for the growth, above is rich.
        parts.append(_clamp((1.5 - peg) * 0.8))
        leg.notes.append(f"PEG ratio {peg:.2f} (growth-adjusted valuation)")

    trailing, forward = data.get("trailing_pe"), data.get("forward_pe")
    if trailing and forward and trailing > 0:
        improvement = (trailing - forward) / trailing
        parts.append(_clamp(improvement * 2))
        leg.notes.append(
            f"P/E {trailing:.1f} trailing vs {forward:.1f} forward — "
            f"{'earnings expected to grow' if improvement > 0 else 'earnings expected to compress'}"
        )

    debt = data.get("debt_to_equity")
    if debt is not None:
        parts.append(_clamp((100 - debt) / 150))
        leg.notes.append(f"Debt to equity {debt:.0f}%")

    target = data.get("target_mean_price")
    if target and price:
        upside = target / price - 1
        parts.append(_clamp(upside * 3))
        leg.notes.append(
            f"Analyst mean target {target:,.2f} implies {upside * 100:+.1f}% "
            f"vs the last price ({int(data.get('analyst_count') or 0)} analysts)"
        )

    if data.get("recommendation"):
        mapping = {"strong_buy": 0.8, "buy": 0.5, "hold": 0.0, "sell": -0.5, "strong_sell": -0.8}
        rating = mapping.get(str(data["recommendation"]).lower())
        if rating is not None:
            parts.append(rating)
            leg.notes.append(f"Consensus rating: {data['recommendation'].replace('_', ' ')}")

    if not parts:
        leg.notes.append("Fundamental fields were empty for this instrument")
        return leg

    leg.score = _clamp(float(np.mean(parts)))
    leg.available = True
    leg.detail = data
    return leg


def _document_leg(symbol: str, company: str) -> Leg:
    """Evidence from the user's own indexed documents."""
    leg = Leg(name="Your documents")
    query = f"{company} {symbol} revenue growth outlook risks guidance"
    # Only evidence that actually names the company counts — a document about
    # something else must not be allowed to move this symbol's score.
    names = {symbol.lower()} | {w.lower() for w in company.split() if len(w) > 3}
    passages = [
        p
        for p in retrieve(query, k=6)
        if p.metadata.get("kind") == "document"
        and any(name in p.text.lower() for name in names)
    ]
    if not passages:
        leg.notes.append("No indexed documents matched this symbol — ingest filings to enable this leg")
        return leg

    scores = [_score_headline(p.text[:900]) for p in passages]
    leg.score = _clamp(float(np.mean(scores)) * 1.4)
    leg.available = True
    leg.detail = {
        "passages": [
            {"source": p.label, "score": p.score, "excerpt": p.text[:300]} for p in passages
        ]
    }
    leg.notes.append(
        f"{len(passages)} matching passage(s) from "
        + ", ".join(sorted({p.source for p in passages}))
    )
    return leg


# ─── Ensemble ─────────────────────────────────────────────────────────────────

def _risk(history, fundamentals: dict[str, Any], confidence: float) -> tuple[int, str, float]:
    """Risk on a 1-10 scale from volatility, drawdown, beta and confidence."""
    computed = indicators.compute_all(history) if history is not None and not history.empty else {}
    annual_vol = (computed.get("volatility") or {}).get("value") or 30.0
    daily_vol = (computed.get("volatility") or {}).get("daily") or 0.02
    down = abs((computed.get("drawdown") or {}).get("value") or 0.0)
    beta = fundamentals.get("beta") or 1.0

    score = 1.0
    score += min(4.0, annual_vol / 15.0)          # 30% vol → +2
    score += min(2.0, down / 15.0)                # 30% off the high → +2
    score += min(1.5, max(0.0, (beta - 1.0)) * 1.5)
    score += 1.5 * (1 - confidence / 100)         # low confidence is itself a risk
    score = int(round(max(1, min(10, score))))
    label = "LOW" if score <= 3 else "MODERATE" if score <= 5 else "ELEVATED" if score <= 7 else "HIGH"
    return score, label, daily_vol


def _classify(direction: float, confidence: float, legs: dict[str, Leg]) -> str:
    active = [leg.score for leg in legs.values() if leg.available]
    conflicting = any(s > 0.15 for s in active) and any(s < -0.15 for s in active)

    if confidence < config.MIN_CONFIDENCE:
        return "INSUFFICIENT EVIDENCE"
    if conflicting and abs(direction) < 0.12:
        return "MIXED SIGNALS"
    if direction >= 0.35:
        return "BULLISH"
    if direction >= 0.12:
        return "LEANING BULLISH"
    if direction <= -0.35:
        return "BEARISH"
    if direction <= -0.12:
        return "LEANING BEARISH"
    return "NEUTRAL"


def forecast(symbol: str, horizon_days: int | None = None) -> Forecast | None:
    """Build a full forecast for one symbol from live data only."""
    symbol = symbol.strip().upper()
    quote = get_quote(symbol)
    if quote is None:
        return None

    horizon = horizon_days or config.FORECAST_HORIZON_DAYS
    history = get_history(symbol)
    fundamentals = get_fundamentals(symbol)

    legs = {
        "technical": _technical_leg(history),
        "sentiment": _sentiment_leg(symbol),
        "fundamental": _fundamental_leg(symbol, quote.price),
        "documents": _document_leg(symbol, quote.name),
    }
    configured = {
        "technical": config.WEIGHT_TECHNICAL,
        "sentiment": config.WEIGHT_SENTIMENT,
        "fundamental": config.WEIGHT_FUNDAMENTAL,
        "documents": config.WEIGHT_DOCUMENTS,
    }

    # Renormalise across the legs that produced data.
    available_weight = sum(w for key, w in configured.items() if legs[key].available)
    for key, leg in legs.items():
        leg.weight = (configured[key] / available_weight) if (leg.available and available_weight) else 0.0

    direction = _clamp(sum(leg.score * leg.weight for leg in legs.values()))

    # Confidence answers "how much do we trust this read?", which is about the
    # legs agreeing and the data being complete — not about the score being big.
    active = [leg.score for leg in legs.values() if leg.available]
    coverage = available_weight / sum(configured.values())
    agreement = 1.0 - min(1.0, float(np.std(active)) if len(active) > 1 else 0.6)
    strength = min(1.0, abs(direction) / 0.4)
    confidence = float(np.clip(100 * (0.5 * agreement + 0.3 * coverage + 0.2 * strength), 0, 95))

    risk_score, risk_label, daily_vol = _risk(history, fundamentals, confidence)

    expected_low = expected_high = None
    if quote.price and daily_vol:
        band = quote.price * daily_vol * math.sqrt(horizon)
        drift = quote.price * direction * daily_vol * horizon * 0.5
        expected_low = round(quote.price + drift - band, 2)
        expected_high = round(quote.price + drift + band, 2)

    drivers: list[str] = []
    for leg in sorted(legs.values(), key=lambda l: abs(l.score) * l.weight, reverse=True):
        if leg.available and leg.notes:
            drivers.append(f"{leg.name}: {leg.notes[0]}")
    missing = [leg.name for leg in legs.values() if not leg.available]

    return Forecast(
        symbol=symbol,
        name=quote.name,
        price=quote.price,
        currency=quote.currency,
        signal=_classify(direction, confidence, legs),
        direction=round(direction, 3),
        confidence=round(confidence, 1),
        risk_score=risk_score,
        risk_label=risk_label,
        horizon_days=horizon,
        expected_low=expected_low,
        expected_high=expected_high,
        legs=legs,
        drivers=drivers[:4],
        data_quality=(
            f"{len(active)}/4 signal legs active"
            + (f"; missing: {', '.join(missing)}" if missing else "")
        ),
        as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )
