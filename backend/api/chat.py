"""
Chat endpoint — the agent's events, streamed to the browser.

The agent yields `Event` objects as it retrieves, calls tools and writes. Each
one is forwarded immediately as a Server-Sent Event, so the interface can paint
retrieval, tool activity and the answer as they happen rather than after.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agent import ResearchAgent

from .schemas import ChatRequest, passage_json

router = APIRouter(prefix="/api/chat", tags=["chat"])

# One conversation per running backend: this is a single-user desktop app.
_agent = ResearchAgent()


def _serialise(event) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": event.kind, "text": event.text}
    data = dict(event.data)
    if "passages" in data:
        data["passages"] = [passage_json(p) for p in data["passages"]]
    payload["data"] = data
    return payload


def _stream(message: str) -> Iterator[str]:
    try:
        for event in _agent.stream(message):
            yield f"data: {json.dumps(_serialise(event))}\n\n"
    except Exception as exc:  # a failure mid-stream still has to reach the client
        error = {"kind": "error", "text": f"{type(exc).__name__}: {exc}", "data": {}}
        yield f"data: {json.dumps(error)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/stream")
def stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream(request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
def history() -> dict[str, Any]:
    return {
        "turns": [
            {
                "question": turn.question,
                "answer": turn.answer,
                "tools": turn.tools_used,
                "passages": [passage_json(p) for p in turn.passages],
            }
            for turn in _agent.turns
        ]
    }


@router.post("/reset")
def reset() -> dict[str, str]:
    _agent.reset()
    return {"status": "cleared"}
