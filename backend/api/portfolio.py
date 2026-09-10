"""Portfolio endpoints — reads and writes one local file, nothing more."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

import config
from src import market, portfolio

from .schemas import HoldingRequest, TopicRequest

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
def read() -> dict[str, Any]:
    rows = portfolio.positions()
    return {
        "positions": [row.as_dict() for row in rows],
        "summary": portfolio.summary(rows),
        "file": str(config.PORTFOLIO_FILE),
    }


@router.post("/holdings")
def add(request: HoldingRequest) -> dict[str, Any]:
    symbol = market.resolve_symbol(request.symbol)
    if not symbol:
        raise HTTPException(404, f"No tradable instrument found for '{request.symbol}'")
    portfolio.add_holding(symbol, request.quantity, request.average_cost)
    return read()


@router.delete("/holdings/{symbol:path}")
def remove(symbol: str) -> dict[str, Any]:
    portfolio.remove_holding(symbol)
    return read()


@router.post("/exposure")
def exposure(request: TopicRequest) -> dict[str, Any]:
    """Which holdings does this event actually touch?"""
    return {"topic": request.topic, "matches": portfolio.exposure(request.topic)}
