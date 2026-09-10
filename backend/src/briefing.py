"""
The daily briefing — everything the user would otherwise have to go and look up.

One call assembles, from live data:

    book        value, today's move, best and weakest holding
    attention   holdings with a reason to look (sharp move, deep loss, concentration)
    exposure    today's themes and which holdings they touch (src/exposure.py)
    forecasts   a simulated outlook for every holding (src/prediction.py)
    market      index levels and the day's biggest movers
    note        a short written summary by the local model, when it is loaded

The background loop in `src/scheduler.py` rebuilds this every few minutes, so
the Home page simply shows the latest one.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import config
from src import exposure, portfolio, preferences
from src.market import get_movers, get_quotes
from src.prediction import forecast

MAX_FORECASTS = 8  # holdings forecast per briefing, largest first


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def attention(rows: list[portfolio.Position], totals: dict[str, Any]) -> list[dict[str, str]]:
    """Holdings with a concrete reason to look at them today."""
    flags = []
    for row in rows:
        if row.day_change_percent is not None and abs(row.day_change_percent) >= 3:
            way = "up" if row.day_change_percent > 0 else "down"
            flags.append({"symbol": row.symbol, "kind": "move",
                          "reason": f"moved {way} {abs(row.day_change_percent):.1f}% today"})
        elif row.unrealised_percent is not None and row.unrealised_percent <= -20:
            flags.append({"symbol": row.symbol, "kind": "loss",
                          "reason": f"down {abs(row.unrealised_percent):.0f}% against your cost"})
    if totals.get("largest_weight", 0) >= 40:
        flags.append({"symbol": totals["largest_position"], "kind": "risk",
                      "reason": f"is {totals['largest_weight']:.0f}% of the whole book"})
    return flags


def _compact_forecast(symbol: str) -> dict[str, Any] | None:
    """The part of a forecast the briefing shows: signal, odds and range."""
    try:
        result = forecast(symbol)
    except Exception:
        return None
    if result is None:
        return None
    sim = result.simulation or {}
    return {
        "symbol": result.symbol,
        "name": result.name,
        "price": result.price,
        "currency": result.currency,
        "signal": result.signal,
        "confidence": result.confidence,
        "risk_score": result.risk_score,
        "risk_label": result.risk_label,
        "horizon_days": result.horizon_days,
        "probability_up": result.probability_up,
        "expected_low": result.expected_low,
        "expected_high": result.expected_high,
        "median_price": sim.get("median_price"),
        "skill": result.skill,
    }


def _write_note(context: str) -> str:
    """A short written briefing from the local model, or '' when it is not loaded."""
    from src.llm import engine

    llm = engine()
    if not llm.is_loaded:
        return ""
    prefs = preferences.load()
    messages = [
        {
            "role": "system",
            "content": (
                "You are Kinetic, a private investment research assistant. Write a short morning "
                "briefing in markdown for the user, using only the data given. Lead with the single "
                "most important thing, then at most four bullets. Mention holdings by ticker, keep "
                "every number's unit, never invent a figure, never tell them to buy or sell. "
                "Under 170 words. " + prefs.describe()
            ),
        },
        {"role": "user", "content": context},
    ]
    try:
        return llm.write(messages, max_tokens=420)
    except Exception:
        return ""


def _context_text(payload: dict[str, Any]) -> str:
    """Everything in the briefing, rendered for the model."""
    lines = [portfolio.to_text(), ""]
    if payload["attention"]:
        lines.append("Needs attention: " + "; ".join(f"{f['symbol']} {f['reason']}" for f in payload["attention"]))
    lines.append(exposure.to_text(payload["exposure"]))
    lines.append("\nSimulated outlook per holding (no guarantee):")
    for item in payload["forecasts"]:
        odds = f"{item['probability_up'] * 100:.0f}% chance higher" if item["probability_up"] is not None else "no simulation"
        lines.append(
            f"- {item['symbol']}: {item['signal']}, {odds} in {item['horizon_days']} sessions, "
            f"risk {item['risk_label']}"
        )
    if payload["market"]["indices"]:
        lines.append(
            "\nIndices: " + ", ".join(
                f"{q['name']} {q['change_percent']:+.2f}%" for q in payload["market"]["indices"] if q["change_percent"] is not None
            )
        )
    return "\n".join(lines)


def build(write_note: bool = True) -> dict[str, Any]:
    """Assemble the full briefing from live data."""
    rows = portfolio.positions()
    totals = portfolio.summary(rows)

    # The slow parts run side by side: exposure, forecasts and market data.
    with ThreadPoolExecutor(max_workers=4) as pool:
        exposure_job = pool.submit(exposure.auto_report)
        forecast_jobs = [pool.submit(_compact_forecast, row.symbol) for row in rows[:MAX_FORECASTS]]
        index_job = pool.submit(get_quotes, config.INDEX_SYMBOLS)
        gainers_job = pool.submit(get_movers, "day_gainers", 5)
        losers_job = pool.submit(get_movers, "day_losers", 5)

        try:
            report = exposure_job.result()
        except Exception as exc:
            report = {"themes": [], "holdings": [], "as_of": _now(), "empty": not rows, "error": str(exc)}
        forecasts = [item for item in (job.result() for job in forecast_jobs) if item]
        indices = [quote.as_dict() for quote in index_job.result()]
        gainers, losers = gainers_job.result(), losers_job.result()

    best = max((r for r in rows if r.day_change_percent is not None), key=lambda r: r.day_change_percent, default=None)
    worst = min((r for r in rows if r.day_change_percent is not None), key=lambda r: r.day_change_percent, default=None)

    payload: dict[str, Any] = {
        "ready": True,
        "generated_at": _now(),
        "summary": totals,
        "best": best.as_dict() if best else None,
        "worst": worst.as_dict() if worst else None,
        "attention": attention(rows, totals) if rows else [],
        "exposure": report,
        "forecasts": forecasts,
        "market": {"indices": indices, "gainers": gainers, "losers": losers},
        "note": "",
        "note_status": "model not loaded",
        "disclaimer": config.DISCLAIMER,
    }
    if write_note and rows:
        payload["note"] = _write_note(_context_text(payload))
        payload["note_status"] = "written" if payload["note"] else "model not loaded"
    elif not rows:
        payload["note_status"] = "no holdings"
    return payload
