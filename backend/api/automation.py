"""
Automation endpoints — the results the background loop keeps ready.

The pages call these instead of asking the user to search: the briefing, the
automatic exposure scan, and the loop's own status.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.scheduler import automation

router = APIRouter(prefix="/api/auto", tags=["automation"])


def _latest_or_build() -> dict[str, Any] | None:
    """The newest briefing. Built on the spot only when the loop is not running."""
    loop = automation()
    latest = loop.latest()
    if latest is None and not loop.running:
        latest = loop.rebuild()
    return latest


@router.get("/briefing")
def briefing() -> dict[str, Any]:
    latest = _latest_or_build()
    if latest is None:
        return {"ready": False, "automation": automation().status()}
    return {**latest, "automation": automation().status()}


@router.get("/exposure")
def exposure() -> dict[str, Any]:
    latest = _latest_or_build()
    if latest is None:
        return {"ready": False, "automation": automation().status()}
    return {"ready": True, **latest["exposure"], "automation": automation().status()}


@router.get("/status")
def status() -> dict[str, Any]:
    return automation().status()


@router.post("/refresh")
def refresh() -> dict[str, Any]:
    """Rebuild everything on the next tick instead of waiting for the timer."""
    loop = automation()
    if loop.running:
        loop.refresh_soon()
    else:
        loop.rebuild()
    return loop.status()
