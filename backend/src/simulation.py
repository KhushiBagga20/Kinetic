"""
Price simulation and backtest — the honest half of the forecast.

Two questions, answered from real price history only:

    monte_carlo   "Where could the price be in N sessions?"
                  Thousands of possible futures are built by replaying chunks
                  of the stock's own past daily returns (a block bootstrap),
                  scaled to today's volatility. The spread of those futures is
                  the range; the share that end higher is the probability of a
                  gain.

    backtest      "Would this signal have been right before?"
                  Walk forward through history. At each checkpoint compute the
                  technical score using only the data available *then*, and
                  check what the price actually did next. The hit rate becomes
                  a skill number that decides how much the forecast is trusted.

Nothing here is a guarantee. It is a statistical description of what has
happened, used to frame what might happen.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

import config
from src import indicators


def log_returns(history: pd.DataFrame) -> np.ndarray:
    """Daily log returns from a candle frame. Empty if there is too little data."""
    if history is None or history.empty or "Close" not in history:
        return np.array([])
    close = history["Close"].dropna().to_numpy(dtype=float)
    close = close[close > 0]
    if len(close) < 2:
        return np.array([])
    return np.diff(np.log(close))


def ewma_volatility(returns: np.ndarray, decay: float = 0.94) -> float:
    """
    Daily volatility where recent days count more (the RiskMetrics method).

    A plain average over two years reacts slowly; this one notices when the
    market has turned calm or rough this week.
    """
    if len(returns) == 0:
        return 0.0
    seed = returns[:20] if len(returns) >= 20 else returns
    variance = float(np.var(seed))
    for value in returns:
        variance = decay * variance + (1 - decay) * value * value
    return float(math.sqrt(variance))


# ─── Monte Carlo ──────────────────────────────────────────────────────────────

def monte_carlo(
    price: float | None,
    returns: np.ndarray,
    horizon: int,
    drift_per_day: float = 0.0,
    paths: int | None = None,
    block: int = 5,
    seed: int = 7,
) -> dict[str, Any]:
    """
    Simulate `paths` possible price paths over `horizon` sessions.

    Returns percentile bands for every day (for the fan chart), a few sample
    paths, and the probabilities people actually ask about. An empty dict
    means there was not enough history to simulate honestly.
    """
    paths = paths or config.SIMULATION_PATHS
    horizon = max(1, int(horizon))
    if not price or price <= 0 or len(returns) < 30:
        return {}

    rng = np.random.default_rng(seed)

    # The historical average return is mostly noise, so it is removed; any
    # drift comes from the signals instead, and is kept deliberately small.
    centred = returns - returns.mean()

    # Rescale so the simulated days are as volatile as the market is *now*.
    historical_vol = float(centred.std()) or 1e-9
    current_vol = ewma_volatility(returns)
    scaled = centred * (current_vol / historical_vol)

    # Block bootstrap: copy runs of `block` consecutive real days, so calm
    # stretches and rough stretches stay together the way they really happen.
    block = max(1, min(block, len(scaled)))
    blocks_needed = math.ceil(horizon / block)
    starts = rng.integers(0, len(scaled) - block + 1, size=(paths, blocks_needed))
    picks = starts[..., None] + np.arange(block)
    steps = scaled[picks].reshape(paths, -1)[:, :horizon] + drift_per_day

    curves = price * np.exp(np.cumsum(steps, axis=1))  # shape: (paths, horizon)
    final = curves[:, -1]

    levels = (5, 16, 25, 50, 75, 84, 95)
    table = np.percentile(curves, levels, axis=0)  # shape: (levels, horizon)

    bands = [{"day": 0, **{f"p{q}": round(price, 4) for q in levels}}]
    for day in range(horizon):
        bands.append(
            {"day": day + 1, **{f"p{q}": round(float(table[i, day]), 4) for i, q in enumerate(levels)}}
        )

    return {
        "paths": paths,
        "horizon": horizon,
        "start_price": round(price, 4),
        "daily_volatility": round(current_vol, 6),
        "drift_per_day": round(drift_per_day, 6),
        "probability_up": round(float((final > price).mean()), 4),
        "probability_up_5": round(float((final >= price * 1.05).mean()), 4),
        "probability_down_5": round(float((final <= price * 0.95).mean()), 4),
        "expected_price": round(float(final.mean()), 4),
        "median_price": round(float(np.median(final)), 4),
        "low_5": round(float(np.percentile(final, 5)), 4),
        "high_95": round(float(np.percentile(final, 95)), 4),
        "low_16": round(float(np.percentile(final, 16)), 4),
        "high_84": round(float(np.percentile(final, 84)), 4),
        "bands": bands,
        # A handful of individual futures, so the chart shows paths, not just a cone.
        "sample_paths": [[round(price, 4)] + [round(float(v), 4) for v in row] for row in curves[:24]],
    }


# ─── Walk-forward backtest ────────────────────────────────────────────────────

def _no_backtest(note: str) -> dict[str, Any]:
    return {"available": False, "skill": 0.0, "note": note}


def backtest(history: pd.DataFrame, horizon: int, step: int | None = None, warmup: int = 60) -> dict[str, Any]:
    """
    Replay the technical signal over past data, with no peeking ahead.

    At each checkpoint only the candles up to that day are used to score, and
    the score is then compared with the move over the next `horizon` sessions.
    """
    step = max(1, step or config.BACKTEST_STEP)
    if history is None or history.empty or "Close" not in history:
        return _no_backtest("No price history to test against")
    history = history.dropna(subset=["Close"])
    close = history["Close"].to_numpy(dtype=float)
    if len(close) < warmup + horizon + 20:
        return _no_backtest("Not enough history for a fair backtest")

    scores, forward, inside_band = [], [], []
    for end in range(warmup, len(close) - horizon, step):
        window = history.iloc[:end]
        score = indicators.technical_score(indicators.compute_all(window))
        start, future = close[end - 1], close[end - 1 + horizon]
        if start <= 0 or future <= 0:
            continue
        move = math.log(future / start)

        # Would the range we drew that day have contained what happened?
        band = ewma_volatility(log_returns(window)[-250:]) * math.sqrt(horizon)

        scores.append(score)
        forward.append(future / start - 1)
        inside_band.append(abs(move) <= band)

    if len(scores) < 10:
        return _no_backtest("Too few checkpoints for a fair backtest")

    scores_arr, forward_arr = np.array(scores), np.array(forward)
    calls = np.abs(scores_arr) >= 0.05  # a near-zero score is "no view", not a call
    call_count = int(calls.sum())
    hits = np.sign(scores_arr[calls]) == np.sign(forward_arr[calls])
    hit_rate = float(hits.mean()) if call_count else 0.5

    bullish = forward_arr[scores_arr >= 0.05]
    bearish = forward_arr[scores_arr <= -0.05]
    correlation = (
        float(np.corrcoef(scores_arr, forward_arr)[0, 1])
        if scores_arr.std() > 0 and forward_arr.std() > 0
        else 0.0
    )

    # Skill: 50% is a coin flip (no skill), 65% or better is full trust.
    # Few calls means little evidence, so skill is also scaled by sample size.
    skill = max(0.0, min(1.0, (hit_rate - 0.5) / 0.15)) * min(1.0, call_count / 30)

    return {
        "available": True,
        "checkpoints": len(scores),
        "calls": call_count,
        "hit_rate": round(hit_rate, 4),
        "base_rate_up": round(float((forward_arr > 0).mean()), 4),
        "band_coverage": round(float(np.mean(inside_band)), 4),
        "correlation": round(correlation, 4),
        "avg_return_bullish": round(float(bullish.mean()), 5) if len(bullish) else None,
        "avg_return_bearish": round(float(bearish.mean()), 5) if len(bearish) else None,
        "skill": round(skill, 4),
        "horizon": horizon,
        "note": (
            f"Technical signal was right {hit_rate * 100:.0f}% of the time over "
            f"{call_count} past {horizon}-session calls"
        ),
    }
