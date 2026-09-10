"""System endpoints — model lifecycle, preferences, and a health summary."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

import config
from src import preferences
from src.llm import engine
from src.rag import stats

from .schemas import PreferencesRequest

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def status() -> dict[str, Any]:
    """Everything the interface needs to describe the state of the machine."""
    llm = engine()
    return {
        "model": llm.status(),
        "index": stats(),
        "providers": {
            "market": "Yahoo Finance (live)",
            "news": "Yahoo Finance" + (" + NewsAPI" if config.NEWS_API_KEY else ""),
        },
        "settings": {
            "base_currency": config.BASE_CURRENCY,
            "default_symbol": config.DEFAULT_SYMBOL,
            "index_symbols": config.INDEX_SYMBOLS,
            "retrieval_k": config.RETRIEVAL_K,
            "weights": {
                "technical": config.WEIGHT_TECHNICAL,
                "sentiment": config.WEIGHT_SENTIMENT,
                "fundamental": config.WEIGHT_FUNDAMENTAL,
                "documents": config.WEIGHT_DOCUMENTS,
            },
        },
        "disclaimer": config.DISCLAIMER,
    }


@router.post("/model/load")
def load_model() -> dict[str, Any]:
    """Blocking on purpose: the interface shows a progress state until it returns."""
    engine().load()
    return engine().status()


@router.post("/model/unload")
def unload_model() -> dict[str, Any]:
    engine().unload()
    return engine().status()


@router.get("/preferences")
def read_preferences() -> dict[str, Any]:
    prefs = preferences.load()
    return {
        **prefs.as_dict(),
        "options": {
            "horizons": preferences.HORIZONS,
            "risk_appetites": preferences.RISK_APPETITES,
            "text_sizes": list(preferences.TEXT_SIZES),
        },
    }


@router.put("/preferences")
def write_preferences(request: PreferencesRequest) -> dict[str, Any]:
    changes = {k: v for k, v in request.model_dump().items() if v is not None}
    preferences.update(**changes)
    return read_preferences()
