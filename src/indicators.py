"""
Technical indicators — computed from live OHLCV candles with pandas.

Every function takes the price history DataFrame returned by
`src.market.get_history` and returns a uniform result:

    {"value": float, "signal": -1.0 .. +1.0, "note": "human readable"}

`signal` is a continuous score, not a bucket, so the ensemble can weigh a
mild reading differently from an extreme one.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _close(history: pd.DataFrame) -> pd.Series:
    return history["Close"].dropna()


def _clamp(value: float) -> float:
    return float(max(-1.0, min(1.0, value)))


def _empty(name: str) -> dict[str, Any]:
    return {"value": None, "signal": 0.0, "note": f"{name}: not enough history"}


def rsi(history: pd.DataFrame, period: int = 14) -> dict[str, Any]:
    """Relative Strength Index. Above 70 is stretched, below 30 is washed out."""
    close = _close(history)
    if len(close) < period + 1:
        return _empty("RSI")
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    strength = gain / loss.replace(0, np.nan)
    value = float((100 - 100 / (1 + strength)).iloc[-1])
    if np.isnan(value):
        return _empty("RSI")
    # 50 is neutral; scale the distance from neutral, invert (high RSI = risk).
    signal = _clamp((50 - value) / 25)
    if value > 70:
        note = f"RSI {value:.1f} — overbought, buyers may be exhausted"
    elif value < 30:
        note = f"RSI {value:.1f} — oversold, often a mean-reversion setup"
    else:
        note = f"RSI {value:.1f} — neutral momentum"
    return {"value": round(value, 2), "signal": signal, "note": note}


def macd(history: pd.DataFrame, fast: int = 12, slow: int = 26, span: int = 9) -> dict[str, Any]:
    """MACD histogram: trend strength and direction."""
    close = _close(history)
    if len(close) < slow + span:
        return _empty("MACD")
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    signal_line = line.ewm(span=span, adjust=False).mean()
    histogram = float((line - signal_line).iloc[-1])
    scale = float(close.iloc[-1]) * 0.01 or 1.0
    direction = "above" if histogram > 0 else "below"
    return {
        "value": round(histogram, 4),
        "signal": _clamp(histogram / scale),
        "note": f"MACD histogram {histogram:+.3f} — momentum line {direction} its signal",
    }


def moving_averages(history: pd.DataFrame, fast: int = 20, slow: int = 50) -> dict[str, Any]:
    """Price position relative to its short and long moving averages."""
    close = _close(history)
    if len(close) < slow:
        return _empty("Moving averages")
    fast_ma = float(close.rolling(fast).mean().iloc[-1])
    slow_ma = float(close.rolling(slow).mean().iloc[-1])
    price = float(close.iloc[-1])
    spread = (fast_ma - slow_ma) / slow_ma if slow_ma else 0.0
    above = price > fast_ma
    return {
        "value": round(spread * 100, 2),
        "signal": _clamp(spread * 12 + (0.2 if above else -0.2)),
        "note": (
            f"{fast}-day MA {fast_ma:,.2f} vs {slow}-day MA {slow_ma:,.2f} "
            f"({spread * 100:+.2f}%), price is {'above' if above else 'below'} the short MA"
        ),
    }


def bollinger(history: pd.DataFrame, period: int = 20, width: float = 2.0) -> dict[str, Any]:
    """Where price sits inside its volatility envelope (%B)."""
    close = _close(history)
    if len(close) < period:
        return _empty("Bollinger bands")
    mean = close.rolling(period).mean()
    deviation = close.rolling(period).std()
    upper = float((mean + width * deviation).iloc[-1])
    lower = float((mean - width * deviation).iloc[-1])
    price = float(close.iloc[-1])
    span = upper - lower
    position = (price - lower) / span if span else 0.5
    return {
        "value": round(position, 3),
        "signal": _clamp((0.5 - position) * 2),
        "note": (
            f"Price {price:,.2f} sits at {position * 100:.0f}% of the "
            f"{period}-day band ({lower:,.2f} – {upper:,.2f})"
        ),
    }


def momentum(history: pd.DataFrame, lookback: int = 20) -> dict[str, Any]:
    """Simple rate of change over the lookback window."""
    close = _close(history)
    if len(close) < lookback + 1:
        return _empty("Momentum")
    change = float(close.iloc[-1] / close.iloc[-lookback - 1] - 1)
    return {
        "value": round(change * 100, 2),
        "signal": _clamp(change * 6),
        "note": f"{lookback}-session price change {change * 100:+.2f}%",
    }


def volume_trend(history: pd.DataFrame, period: int = 20) -> dict[str, Any]:
    """Is the recent move backed by participation?"""
    if "Volume" not in history or len(history) < period + 1:
        return _empty("Volume")
    volume = history["Volume"].dropna()
    if len(volume) < period + 1 or volume.tail(period).mean() == 0:
        return _empty("Volume")
    ratio = float(volume.iloc[-1] / volume.tail(period).mean())
    close = _close(history)
    rising = float(close.iloc[-1]) >= float(close.iloc[-2])
    signal = _clamp((ratio - 1) * 0.8) * (1 if rising else -1)
    return {
        "value": round(ratio, 2),
        "signal": signal,
        "note": (
            f"Latest volume is {ratio:.2f}x the {period}-day average on a "
            f"{'up' if rising else 'down'} session"
        ),
    }


def volatility(history: pd.DataFrame, period: int = 20) -> dict[str, Any]:
    """Annualised realised volatility — used for risk, not for direction."""
    close = _close(history)
    if len(close) < period + 1:
        return _empty("Volatility")
    returns = close.pct_change().dropna().tail(period)
    daily = float(returns.std())
    annual = daily * np.sqrt(252)
    return {
        "value": round(annual * 100, 2),
        "signal": 0.0,  # volatility is a risk input, not a direction signal
        "daily": daily,
        "note": f"Realised volatility {annual * 100:.1f}% annualised over {period} sessions",
    }


def drawdown(history: pd.DataFrame) -> dict[str, Any]:
    """Distance below the running peak of the window."""
    close = _close(history)
    if close.empty:
        return _empty("Drawdown")
    peak = float(close.cummax().iloc[-1])
    price = float(close.iloc[-1])
    value = (price / peak - 1) if peak else 0.0
    return {
        "value": round(value * 100, 2),
        "signal": 0.0,
        "note": f"{value * 100:.1f}% from the period high of {peak:,.2f}",
    }


def compute_all(history: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Run the full indicator set over one price history."""
    return {
        "rsi": rsi(history),
        "macd": macd(history),
        "moving_averages": moving_averages(history),
        "bollinger": bollinger(history),
        "momentum": momentum(history),
        "volume": volume_trend(history),
        "volatility": volatility(history),
        "drawdown": drawdown(history),
    }


DIRECTIONAL = ("rsi", "macd", "moving_averages", "bollinger", "momentum", "volume")


def technical_score(indicators: dict[str, dict[str, Any]]) -> float:
    """Average the directional signals into one -1..+1 technical score."""
    signals = [
        indicators[name]["signal"]
        for name in DIRECTIONAL
        if indicators.get(name, {}).get("value") is not None
    ]
    return float(np.mean(signals)) if signals else 0.0
