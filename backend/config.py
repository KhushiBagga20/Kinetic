"""
Kinetic — central configuration.

Every tunable lives here and every value can be overridden from the
environment (.env), so nothing operational is hardcoded in the code base.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    raw = _str(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = Path(_str("KINETIC_DOCUMENTS_DIR", str(BASE_DIR / "data" / "documents")))
VECTOR_DIR = Path(_str("KINETIC_VECTOR_DIR", str(BASE_DIR / "data" / "vector_store")))

# Your holdings live in this file and nowhere else. It is git-ignored, it is
# never uploaded, and no part of the app sends it over a network.
PORTFOLIO_FILE = Path(_str("KINETIC_PORTFOLIO_FILE", str(BASE_DIR / "data" / "portfolio.json")))

DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)


# ─── Local LLM (MLX on Apple Silicon) ─────────────────────────────────────────
# The model is never loaded at import time. It loads on the first explicit
# request (the "Load model" control in the UI, or LLM_AUTOLOAD=true).
LLM_MODEL = _str("KINETIC_LLM_MODEL", "mlx-community/gemma-4-26b-a4b-it-4bit")
LLM_AUTOLOAD = _bool("KINETIC_LLM_AUTOLOAD", False)
LLM_MAX_TOKENS = _int("KINETIC_LLM_MAX_TOKENS", 1536)
LLM_TEMPERATURE = _float("KINETIC_LLM_TEMPERATURE", 0.2)
LLM_TOP_P = _float("KINETIC_LLM_TOP_P", 0.95)
LLM_TOP_K = _int("KINETIC_LLM_TOP_K", 64)
LLM_THINKING = _bool("KINETIC_LLM_THINKING", False)
LLM_MAX_TOOL_STEPS = _int("KINETIC_LLM_MAX_TOOL_STEPS", 4)
LLM_HISTORY_TURNS = _int("KINETIC_LLM_HISTORY_TURNS", 6)


# ─── RAG pipeline ─────────────────────────────────────────────────────────────
EMBEDDING_MODEL = _str("KINETIC_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_BATCH_SIZE = _int("KINETIC_EMBEDDING_BATCH_SIZE", 64)

CHUNK_SIZE = _int("KINETIC_CHUNK_SIZE", 900)          # characters
CHUNK_OVERLAP = _int("KINETIC_CHUNK_OVERLAP", 180)    # keeps numbers with labels

RETRIEVAL_K = _int("KINETIC_RETRIEVAL_K", 5)          # chunks handed to the model
RETRIEVAL_CANDIDATES = _int("KINETIC_RETRIEVAL_CANDIDATES", 24)  # per retriever leg
RRF_K = _int("KINETIC_RRF_K", 60)                     # reciprocal-rank-fusion constant
MMR_LAMBDA = _float("KINETIC_MMR_LAMBDA", 0.7)        # 1.0 = pure relevance
MIN_RELEVANCE = _float("KINETIC_MIN_RELEVANCE", 0.15) # cosine floor, drops noise

COLLECTION_DOCUMENTS = _str("KINETIC_COLLECTION_DOCUMENTS", "kinetic_documents")
COLLECTION_MARKET = _str("KINETIC_COLLECTION_MARKET", "kinetic_market_feed")


# ─── Live market data ─────────────────────────────────────────────────────────
QUOTE_TTL_SEC = _int("KINETIC_QUOTE_TTL_SEC", 30)
HISTORY_TTL_SEC = _int("KINETIC_HISTORY_TTL_SEC", 300)
NEWS_TTL_SEC = _int("KINETIC_NEWS_TTL_SEC", 300)
FUNDAMENTALS_TTL_SEC = _int("KINETIC_FUNDAMENTALS_TTL_SEC", 900)
SCREENER_TTL_SEC = _int("KINETIC_SCREENER_TTL_SEC", 120)

NEWS_LIMIT = _int("KINETIC_NEWS_LIMIT", 8)
HISTORY_PERIOD = _str("KINETIC_HISTORY_PERIOD", "6mo")
AUTO_REFRESH_SEC = _int("KINETIC_AUTO_REFRESH_SEC", 60)

# Index symbols shown on the dashboard ribbon (Yahoo Finance symbols).
INDEX_SYMBOLS = _list("KINETIC_INDEX_SYMBOLS", "^NSEI,^BSESN,^NSEBANK,^INDIAVIX,^GSPC,BTC-USD")

# Everything in a portfolio is converted to this currency using a live FX rate.
BASE_CURRENCY = _str("KINETIC_BASE_CURRENCY", "INR")
DEFAULT_SYMBOL = _str("KINETIC_DEFAULT_SYMBOL", "RELIANCE.NS")

# Optional API keys — every feature degrades gracefully without them.
NEWS_API_KEY = _str("NEWS_API_KEY", "")
ALPHA_VANTAGE_API_KEY = _str("ALPHA_VANTAGE_API_KEY", "")
FMP_API_KEY = _str("FMP_API_KEY", "")

HTTP_TIMEOUT_SEC = _int("KINETIC_HTTP_TIMEOUT_SEC", 10)


# ─── Prediction engine ────────────────────────────────────────────────────────
WEIGHT_TECHNICAL = _float("KINETIC_WEIGHT_TECHNICAL", 0.40)
WEIGHT_SENTIMENT = _float("KINETIC_WEIGHT_SENTIMENT", 0.25)
WEIGHT_FUNDAMENTAL = _float("KINETIC_WEIGHT_FUNDAMENTAL", 0.25)
WEIGHT_DOCUMENTS = _float("KINETIC_WEIGHT_DOCUMENTS", 0.10)
WEIGHT_MARKET = _float("KINETIC_WEIGHT_MARKET", 0.15)   # the broad market's own trend
MIN_CONFIDENCE = _float("KINETIC_MIN_CONFIDENCE", 35.0)
FORECAST_HORIZON_DAYS = _int("KINETIC_FORECAST_HORIZON_DAYS", 10)


# Simulation and backtest (see src/simulation.py).
SIMULATION_PATHS = _int("KINETIC_SIMULATION_PATHS", 2000)      # Monte Carlo paths per forecast
SIMULATION_HISTORY = _str("KINETIC_SIMULATION_HISTORY", "2y")  # history the paths are drawn from
BACKTEST_STEP = _int("KINETIC_BACKTEST_STEP", 5)               # sessions between backtest checkpoints


# ─── Automation ───────────────────────────────────────────────────────────────
# The background loop keeps every page's data ready so nobody has to search.
# Quotes refresh on the fast cycle; news, themes, exposure, forecasts and the
# written briefing refresh on the slow cycle.
AUTOMATION_ENABLED = _bool("KINETIC_AUTOMATION", True)
AUTO_FAST_SEC = _int("KINETIC_AUTO_FAST_SEC", 60)
AUTO_SLOW_SEC = _int("KINETIC_AUTO_SLOW_SEC", 300)
AUTO_THEMES = _int("KINETIC_AUTO_THEMES", 6)                   # themes detected per cycle
AUTO_LOAD_MODEL = _bool("KINETIC_AUTO_LOAD_MODEL", True)       # load Gemma in the background at start

# Macro themes that are always checked, alongside the ones found in today's news.
BASELINE_THEMES = _list(
    "KINETIC_BASELINE_THEMES",
    "interest rate changes,oil and energy prices,rupee and currency moves,"
    "AI and technology spending,consumer demand slowdown,government regulation and policy",
)


# ─── MCP server ───────────────────────────────────────────────────────────────
MCP_HOST = _str("KINETIC_MCP_HOST", "127.0.0.1")
MCP_PORT = _int("KINETIC_MCP_PORT", 8765)


# ─── Presentation ─────────────────────────────────────────────────────────────
APP_NAME = "KINETIC"
APP_TAGLINE = "Local-first investment research terminal"

DISCLAIMER = (
    "Kinetic is a research tool, not personalised financial advice. Signals are "
    "generated by statistical models over public market data and your own "
    "documents. Markets carry risk; past performance does not predict future "
    "returns. Verify every number before acting on it."
)
