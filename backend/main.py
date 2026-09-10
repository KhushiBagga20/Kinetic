"""
Kinetic backend — one FastAPI process in front of the local research engine.

    cd backend && uvicorn main:app --reload --port 8000

It owns the market data, the vector store, the portfolio file and the local
model. The browser talks to it over JSON, and to the chat endpoint over
Server-Sent Events so answers can stream token by token.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from api import automation, chat, knowledge, market, portfolio, system
from src.scheduler import automation as automation_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the automation loop with the server, and stop it with the server."""
    if config.AUTOMATION_ENABLED:
        automation_loop().start()
    yield
    automation_loop().stop()


app = FastAPI(
    title="Kinetic",
    description="Local-first investment research. Live market data, private documents, on-device reasoning.",
    version="1.1.0",
    lifespan=lifespan,
)

# The frontend runs on its own dev server; in production it is served from the
# same origin, so this only matters while developing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (system.router, market.router, portfolio.router, knowledge.router, chat.router, automation.router):
    app.include_router(router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": config.APP_NAME, "tagline": config.APP_TAGLINE}
