"""Market data endpoints — every one of them hits the network on request."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

import config
from src import indicators, market
from src.prediction import forecast

from .schemas import forecast_json

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/indices")
def indices() -> list[dict[str, Any]]:
    """The ribbon: whichever indices the user configured."""
    return [quote.as_dict() for quote in market.get_quotes(config.INDEX_SYMBOLS)]


@router.get("/search")
def search(q: str = Query(min_length=1)) -> list[dict[str, Any]]:
    return market.search_symbols(q)


@router.get("/resolve")
def resolve(q: str = Query(min_length=1)) -> dict[str, Any]:
    symbol = market.resolve_symbol(q)
    if not symbol:
        raise HTTPException(404, f"No tradable instrument found for '{q}'")
    return {"symbol": symbol}


@router.get("/movers")
def movers(kind: str = "day_gainers", limit: int = 8) -> list[dict[str, Any]]:
    return market.get_movers(kind, count=limit)


@router.get("/quote/{symbol:path}")
def quote(symbol: str) -> dict[str, Any]:
    result = market.get_quote(symbol)
    if result is None:
        raise HTTPException(404, f"No live quote for '{symbol}'")
    return result.as_dict()


@router.get("/session/{symbol:path}")
def session(symbol: str) -> dict[str, Any]:
    return market.session(symbol)


@router.get("/fundamentals/{symbol:path}")
def fundamentals(symbol: str) -> dict[str, Any]:
    return market.get_fundamentals(symbol)


@router.get("/news/{symbol:path}")
def news(symbol: str, limit: int | None = None) -> list[dict[str, Any]]:
    return [article.as_dict() for article in market.get_news(symbol, limit=limit)]


@router.get("/history/{symbol:path}")
def history(symbol: str, period: str = "6mo") -> dict[str, Any]:
    """OHLCV candles plus the moving averages the chart draws."""
    frame = market.get_history(symbol, period=period)
    if frame.empty:
        raise HTTPException(404, f"No price history for '{symbol}'")

    close = frame["Close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    candles = []
    for index, (stamp, row) in enumerate(frame.iterrows()):
        candles.append(
            {
                "time": stamp.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]) if row.get("Volume") == row.get("Volume") else 0,
                "sma20": None if sma20.iloc[index] != sma20.iloc[index] else round(float(sma20.iloc[index]), 4),
                "sma50": None if sma50.iloc[index] != sma50.iloc[index] else round(float(sma50.iloc[index]), 4),
            }
        )
    return {"symbol": symbol.upper(), "period": period, "candles": candles}


@router.get("/indicators/{symbol:path}")
def technicals(symbol: str, period: str = "6mo") -> dict[str, Any]:
    frame = market.get_history(symbol, period=period)
    if frame.empty:
        raise HTTPException(404, f"No price history for '{symbol}'")
    computed = indicators.compute_all(frame)
    return {
        "score": indicators.technical_score(computed),
        "indicators": [
            {"key": key, **value} for key, value in computed.items() if value["value"] is not None
        ],
    }


@router.get("/forecast/{symbol:path}")
def market_forecast(symbol: str, horizon: int | None = None) -> dict[str, Any]:
    result = forecast(symbol, horizon_days=horizon)
    if result is None:
        raise HTTPException(404, f"Could not build a forecast for '{symbol}'")
    return forecast_json(result)
