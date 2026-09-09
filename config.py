"""
Centralized configuration for the Personal Investment Research Agent.
All settings, paths, and API keys are managed here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load environment variables ──────────────────────────────────────────────
load_dotenv()

# ─── Project Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "documents"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# ─── API Keys (add your keys in .env) ────────────────────────────────────────
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# ─── RAG Pipeline Settings (tuned for low latency) ───────────────────────────
RAG_CHUNK_SIZE = 800            # chars per chunk — keeps financial tables intact
RAG_CHUNK_OVERLAP = 200         # overlap — prevents splitting mid-number
RAG_RETRIEVAL_K = 3             # top-k docs — minimal for fast retrieval
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, ~14ms/query
CHROMA_COLLECTION_NAME = "financial_docs"

# ─── LLM Settings ────────────────────────────────────────────────────────────
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.1           # low temp for factual financial answers
LLM_CONTEXT_WINDOW = 4096

# ─── Live Data Settings ──────────────────────────────────────────────────────
LIVE_REFRESH_INTERVAL_SEC = 120  # auto-refresh every 2 minutes
NEWS_CACHE_TTL_SEC = 300         # cache news for 5 minutes
STOCK_CACHE_TTL_SEC = 60         # cache stock prices for 1 minute
MAX_NEWS_RESULTS = 5             # top N news headlines per query

# ─── Prediction Engine Settings ──────────────────────────────────────────────
TECHNICAL_WEIGHT = 0.40
SENTIMENT_WEIGHT = 0.30
FUNDAMENTAL_WEIGHT = 0.30
MIN_CONFIDENCE_THRESHOLD = 40   # below this → "INSUFFICIENT DATA"
LOOKBACK_DAYS = 90              # historical data window for indicators

# ─── MCP Server Settings (Bonus) ─────────────────────────────────────────────
MCP_SERVER_HOST = "localhost"
MCP_SERVER_PORT = 8765

# ─── Disclaimer ──────────────────────────────────────────────────────────────
DISCLAIMER_TEXT = (
    "⚠️ DISCLAIMER: This is a model-generated report based on historical data "
    "and technical indicators. It carries inherent risks and does not guarantee "
    "future performance. Past performance is not indicative of future results. "
    "Please consult a certified financial advisor before making any investment "
    "decisions. The creators of this tool are not responsible for any financial "
    "losses incurred."
)
