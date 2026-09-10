"""
Request and response shapes.

The domain objects in `src` are plain dataclasses; these convert them into the
JSON the frontend consumes, so the API contract lives in one readable file.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ─── Requests ─────────────────────────────────────────────────────────────────

class HoldingRequest(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    average_cost: float = Field(ge=0)


class TopicRequest(BaseModel):
    topic: str


class SearchRequest(BaseModel):
    query: str
    k: int | None = None


class CaptureRequest(BaseModel):
    symbol: str


class ChatRequest(BaseModel):
    message: str


class PreferencesRequest(BaseModel):
    name: str | None = None
    base_currency: str | None = None
    horizon: str | None = None
    risk_appetite: str | None = None
    watchlist: list[str] | None = None
    text_size: str | None = None
    high_contrast: bool | None = None
    reduce_motion: bool | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def passage_json(passage) -> dict[str, Any]:
    """A retrieved passage, as the interface displays it."""
    return {
        "text": passage.text,
        "label": passage.label,
        "source": passage.source,
        "score": passage.score,
        "collection": passage.collection,
        "kind": "live" if passage.collection.endswith("market_feed") else "document",
        "metadata": passage.metadata,
    }


def forecast_json(result) -> dict[str, Any]:
    """The ensemble forecast, with each leg kept separate for the UI."""
    payload = result.as_dict()
    payload["legs"] = [
        {"key": key, **leg} for key, leg in payload["legs"].items()
    ]
    return payload
