"""
Technical Indicators — calculates RSI, MACD, Bollinger Bands, SMA/EMA crossovers.

Uses the `ta` (Technical Analysis) library + pandas/numpy for calculations.
All indicators are computed on yfinance historical data.

Each indicator returns a signal: BULLISH (+1), NEUTRAL (0), or BEARISH (-1)
along with a confidence weight.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

import config


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """
    Calculate Relative Strength Index (RSI).

    RSI > 70 → Overbought (BEARISH signal)
    RSI < 30 → Oversold (BULLISH signal)
    RSI 30-70 → Neutral

    Args:
        data: DataFrame with 'Close' column (from yfinance).
        period: RSI calculation period (default 14 days).

    Returns:
        Dict with 'value', 'signal' (-1/0/+1), 'description'.
    """
    if len(data) < period + 1:
        return {"value": None, "signal": 0, "description": "Insufficient data for RSI"}

    close = data["Close"]
    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]

    if np.isnan(current_rsi):
        return {"value": None, "signal": 0, "description": "RSI calculation failed"}

    if current_rsi > 70:
        signal = -1
        desc = f"RSI = {current_rsi:.1f} — OVERBOUGHT (may suggest selling pressure)"
    elif current_rsi < 30:
        signal = 1
        desc = f"RSI = {current_rsi:.1f} — OVERSOLD (may suggest buying opportunity)"
    else:
        signal = 0
        desc = f"RSI = {current_rsi:.1f} — NEUTRAL range"

    return {"value": round(current_rsi, 2), "signal": signal, "description": desc}


def calculate_macd(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Dict[str, Any]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD above signal line → BULLISH
    MACD below signal line → BEARISH

    Args:
        data: DataFrame with 'Close' column.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).

    Returns:
        Dict with 'macd', 'signal_line', 'histogram', 'signal', 'description'.
    """
    if len(data) < slow + signal_period:
        return {
            "macd": None, "signal_line": None, "histogram": None,
            "signal": 0, "description": "Insufficient data for MACD",
        }

    close = data["Close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_hist = histogram.iloc[-1]

    if current_macd > current_signal:
        signal = 1
        desc = f"MACD ({current_macd:.3f}) ABOVE signal ({current_signal:.3f}) — BULLISH momentum"
    elif current_macd < current_signal:
        signal = -1
        desc = f"MACD ({current_macd:.3f}) BELOW signal ({current_signal:.3f}) — BEARISH momentum"
    else:
        signal = 0
        desc = "MACD and signal line converging — NEUTRAL"

    # Check for crossover (stronger signal)
    if len(macd_line) >= 2:
        prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
        curr_diff = current_macd - current_signal
        if prev_diff < 0 and curr_diff > 0:
            desc += " [BULLISH CROSSOVER detected]"
            signal = 1
        elif prev_diff > 0 and curr_diff < 0:
            desc += " [BEARISH CROSSOVER detected]"
            signal = -1

    return {
        "macd": round(current_macd, 4),
        "signal_line": round(current_signal, 4),
        "histogram": round(current_hist, 4),
        "signal": signal,
        "description": desc,
    }


def calculate_bollinger_bands(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> Dict[str, Any]:
    """
    Calculate Bollinger Bands.

    Price near upper band → BEARISH (overbought)
    Price near lower band → BULLISH (oversold)
    Price in middle → NEUTRAL

    Args:
        data: DataFrame with 'Close' column.
        period: Moving average period (default 20).
        std_dev: Standard deviation multiplier (default 2.0).

    Returns:
        Dict with 'upper', 'middle', 'lower', 'bandwidth', 'signal', 'description'.
    """
    if len(data) < period:
        return {
            "upper": None, "middle": None, "lower": None,
            "signal": 0, "description": "Insufficient data for Bollinger Bands",
        }

    close = data["Close"]
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    current_price = close.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    current_middle = sma.iloc[-1]
    bandwidth = (current_upper - current_lower) / current_middle * 100

    # Price position relative to bands (0 = lower, 1 = upper)
    band_position = (current_price - current_lower) / (current_upper - current_lower)

    if band_position > 0.8:
        signal = -1
        desc = f"Price near UPPER band ({band_position:.0%}) — may suggest overbought"
    elif band_position < 0.2:
        signal = 1
        desc = f"Price near LOWER band ({band_position:.0%}) — may suggest oversold"
    else:
        signal = 0
        desc = f"Price in MIDDLE of bands ({band_position:.0%}) — neutral"

    return {
        "upper": round(current_upper, 2),
        "middle": round(current_middle, 2),
        "lower": round(current_lower, 2),
        "bandwidth": round(bandwidth, 2),
        "band_position": round(band_position, 3),
        "signal": signal,
        "description": desc,
    }


def calculate_sma_crossover(
    data: pd.DataFrame,
    short_period: int = 20,
    long_period: int = 50,
) -> Dict[str, Any]:
    """
    Calculate SMA Crossover signals.

    Short SMA above long SMA → BULLISH (Golden Cross)
    Short SMA below long SMA → BEARISH (Death Cross)

    Args:
        data: DataFrame with 'Close' column.
        short_period: Short-term SMA period (default 20).
        long_period: Long-term SMA period (default 50).

    Returns:
        Dict with 'sma_short', 'sma_long', 'signal', 'description'.
    """
    if len(data) < long_period:
        return {
            "sma_short": None, "sma_long": None,
            "signal": 0, "description": "Insufficient data for SMA crossover",
        }

    close = data["Close"]
    sma_short = close.rolling(window=short_period).mean()
    sma_long = close.rolling(window=long_period).mean()

    current_short = sma_short.iloc[-1]
    current_long = sma_long.iloc[-1]

    if current_short > current_long:
        signal = 1
        desc = f"SMA{short_period} ({current_short:.2f}) ABOVE SMA{long_period} ({current_long:.2f}) — BULLISH trend"
    else:
        signal = -1
        desc = f"SMA{short_period} ({current_short:.2f}) BELOW SMA{long_period} ({current_long:.2f}) — BEARISH trend"

    # Check for recent crossover
    if len(sma_short) >= 2 and len(sma_long) >= 2:
        prev_diff = sma_short.iloc[-2] - sma_long.iloc[-2]
        curr_diff = current_short - current_long
        if prev_diff < 0 and curr_diff > 0:
            desc += " [GOLDEN CROSS — bullish crossover]"
        elif prev_diff > 0 and curr_diff < 0:
            desc += " [DEATH CROSS — bearish crossover]"

    return {
        "sma_short": round(current_short, 2),
        "sma_long": round(current_long, 2),
        "signal": signal,
        "description": desc,
    }


def calculate_volume_analysis(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze volume trends to confirm price movements.

    Rising price + rising volume → Strong BULLISH
    Falling price + rising volume → Strong BEARISH
    Price move + declining volume → Weak signal

    Args:
        data: DataFrame with 'Close' and 'Volume' columns.

    Returns:
        Dict with volume analysis results.
    """
    if len(data) < 20:
        return {"signal": 0, "description": "Insufficient data for volume analysis"}

    close = data["Close"]
    volume = data["Volume"]

    # Average volume (20-day)
    avg_volume = volume.rolling(window=20).mean().iloc[-1]
    current_volume = volume.iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

    # Price trend (5-day)
    price_change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100

    if price_change > 0 and volume_ratio > 1.2:
        signal = 1
        desc = f"Rising price (+{price_change:.1f}%) with HIGH volume ({volume_ratio:.1f}x avg) — strong BULLISH"
    elif price_change < 0 and volume_ratio > 1.2:
        signal = -1
        desc = f"Falling price ({price_change:.1f}%) with HIGH volume ({volume_ratio:.1f}x avg) — strong BEARISH"
    elif price_change > 0 and volume_ratio < 0.8:
        signal = 0
        desc = f"Rising price (+{price_change:.1f}%) but LOW volume ({volume_ratio:.1f}x avg) — weak signal"
    elif price_change < 0 and volume_ratio < 0.8:
        signal = 0
        desc = f"Falling price ({price_change:.1f}%) with LOW volume ({volume_ratio:.1f}x avg) — weak signal"
    else:
        signal = 0
        desc = f"Volume near average ({volume_ratio:.1f}x) — no strong signal"

    return {
        "current_volume": int(current_volume),
        "avg_volume": int(avg_volume),
        "volume_ratio": round(volume_ratio, 2),
        "price_change_5d": round(price_change, 2),
        "signal": signal,
        "description": desc,
    }


def run_all_technical_indicators(data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Run all technical indicators on the given data.

    Args:
        data: DataFrame with OHLCV columns from yfinance.

    Returns:
        Dict mapping indicator name → results dict.
    """
    return {
        "rsi": calculate_rsi(data),
        "macd": calculate_macd(data),
        "bollinger_bands": calculate_bollinger_bands(data),
        "sma_crossover": calculate_sma_crossover(data),
        "volume_analysis": calculate_volume_analysis(data),
    }


def get_technical_score(indicators: Dict[str, Dict[str, Any]]) -> Tuple[float, str]:
    """
    Compute a weighted technical score from all indicators.

    Returns:
        Tuple of (score -1.0 to +1.0, description).
        Positive = bullish, negative = bearish, 0 = neutral.
    """
    weights = {
        "rsi": 0.20,
        "macd": 0.25,
        "bollinger_bands": 0.15,
        "sma_crossover": 0.25,
        "volume_analysis": 0.15,
    }

    total_score = 0.0
    total_weight = 0.0
    descriptions = []

    for name, weight in weights.items():
        result = indicators.get(name, {})
        signal = result.get("signal", 0)
        total_score += signal * weight
        total_weight += weight
        if result.get("description"):
            descriptions.append(result["description"])

    normalized = total_score / total_weight if total_weight > 0 else 0

    return normalized, "\n".join(descriptions)
