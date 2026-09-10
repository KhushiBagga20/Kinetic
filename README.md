# Kinetic

An investment research terminal for people who cannot hand their portfolio to a
chatbot.

It answers questions by combining **live market data**, fetched at the moment
you ask, with **your own documents and your own holdings**, retrieved from a
local vector index — and it writes the answer with a model running on your own
machine. No API keys, and nothing leaves the laptop: not your positions, not
your filings, not your questions.

```
┌────────────┐   ┌──────────────────────┐   ┌─────────────────────────┐
│  question  │ → │  hybrid retrieval    │ → │  Gemma 4 (MLX, local)   │ → streamed answer
└────────────┘   │  dense + BM25 → RRF  │   │  native tool calling    │
                 └──────────┬───────────┘   └───────────┬─────────────┘
                            │                           │
                   ChromaDB │ your documents   live tools│ quotes · fundamentals
                            │ live snapshots             │ news · screeners · forecast
```

## What it does

| View | What it gives you |
| --- | --- |
| **Home** | Your book, priced live: value, today's move, your best and weakest position, what is worth a look (a sharp move, a position far under water, a concentration above 40%), and your watchlist — every row one click from full research. |
| **Portfolio** | Holdings with live P&L, weights after FX conversion, sector mix, and an **exposure check**: describe an event in plain words and each holding's live profile is embedded on-device and matched against it, so "rupee weakness" finds the right positions without a keyword rule. |
| **Research** | Live index ribbon, live quotes, candles with moving averages, technical read-out, live headlines and live screener tables — plus the forecast engine, on the same symbol. Any symbol can be captured into the vector store in one click. |
| **Assistant** | A streaming chat that retrieves before it answers, reads your actual holdings when you say "my", calls live tools when it needs a current number, and labels every figure as live data or as coming from a named document. |
| **Knowledge** | Upload and manage the corpus, capture live snapshots, browse what is indexed, and run the retriever on its own to see exactly which passages a query returns. |

The forecast engine is a four-leg ensemble — technical, news sentiment,
fundamentals, your documents — with per-leg scores, a confidence read, a 1–10
risk score and a volatility-implied range. It lives in the Research view.

## Personal, and private by construction

Your name, currency, horizon, risk appetite and watchlist live in
`data/preferences.json`; your holdings live in `data/portfolio.json`. Both are
git-ignored, read only by this process, and never uploaded — the profile is also
given to the model, so answers are written for you rather than for a generic
investor. Text size, contrast and motion are adjustable from the sidebar, every
figure carries a ▲/▼ glyph as well as a colour, and focus rings are visible for
keyboard navigation.

## Requirements

- macOS on Apple Silicon (the model runs on MLX)
- Python 3.11+
- ~15 GB of free unified memory while the model is loaded

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The model weights are pulled from Hugging Face the first time they are needed
(`mlx-community/gemma-4-26b-a4b-it-4bit`, about 14 GB). Everything except the
chat and the written analyst note works before the model is loaded.

Optional: `cp .env.example .env` to change the model, the retrieval settings,
the forecast weights or the index symbols. Adding `NEWS_API_KEY` widens the
news feed beyond Yahoo Finance; it is not required.

## The RAG pipeline

```
load → chunk → embed → store → retrieve → ground
```

1. **Load** — PDF, TXT, MD, CSV, HTML and JSON (`src/rag/ingest.py`).
2. **Chunk** — a finance-aware splitter (`src/rag/chunking.py`): table rows are
   never split mid-row, the nearest heading is attached to every chunk as a
   breadcrumb, and an overlap tail keeps a number attached to its label.
3. **Embed** — `all-MiniLM-L6-v2` locally, L2-normalised (`src/rag/embeddings.py`).
4. **Store** — ChromaDB on disk, two collections: your documents, and a live
   market feed of timestamped quote/fundamental/news snapshots (`src/rag/store.py`).
5. **Retrieve** — dense search and BM25 run in parallel, are fused with
   Reciprocal Rank Fusion, filtered by a relevance floor and diversified with
   MMR (`src/rag/retriever.py`).
6. **Ground** — passages reach the model numbered `[S1]`, `[S2]`, and it is
   instructed to cite them.

Because live snapshots are indexed alongside static documents, retrieval stays
current: "what is the market saying about this right now" pulls evidence
captured minutes ago, not text from a filing last quarter.

## The model

`src/llm.py` wraps Gemma 4 (26B A4B, 4-bit) on MLX. It is loaded lazily — the
app starts instantly and the weights only enter memory when you press **LOAD
MODEL** (or set `KINETIC_LLM_AUTOLOAD=true`). The wrapper speaks Gemma's native
chat format, which gives token streaming, a separate reasoning channel and
native tool calls parsed straight from the token stream.

## Tools

Eleven tools back both the assistant and the MCP server, from one registry
(`src/tools.py`): `resolve_ticker`, `get_stock_quote`, `get_price_history`,
`get_company_fundamentals`, `get_market_news`, `get_market_movers`,
`search_documents`, `index_live_market_data`, `get_portfolio`,
`get_portfolio_exposure`, `get_forecast`.

Serve them to any MCP client:

```bash
python -m src.mcp_server          # stdio
python -m src.mcp_server --http   # HTTP on 127.0.0.1:8765
```

## Command line

```bash
python scripts/ingest.py                      # index data/documents/
python scripts/ingest.py report.pdf           # index specific files
python scripts/ingest.py --live NVDA AAPL     # capture live snapshots
python scripts/ingest.py --status             # what is indexed
python scripts/selfcheck.py                   # verify the whole stack, model excluded
```

`selfcheck.py` exercises live quotes, symbol resolution, history, news, the
screener, ingestion, hybrid retrieval, the forecast engine and every tool, and
reports the latency of each. It never loads the model.

Unit tests (no network, no weights):

```bash
python -m pytest tests -q
```

## Layout

```
app.py                  Streamlit shell and navigation
config.py               every setting, all overridable from .env
src/
  llm.py                MLX Gemma engine: streaming, tool-call parsing
  agent.py              retrieve → reason → act loop, emitted as events
  tools.py              tool registry shared by the agent and MCP
  portfolio.py          local holdings, live pricing, semantic exposure
  preferences.py        profile and accessibility settings, stored locally
  indicators.py         RSI, MACD, moving averages, bands, volatility
  prediction.py         the four-leg ensemble forecast
  mcp_server.py         MCP entry point
  market/               live quotes, history, fundamentals, news, screeners, FX
  rag/                  chunking, embeddings, ChromaDB store, hybrid retriever
ui/                     one module per view, plus the shared theme
scripts/ingest.py       command-line ingestion
scripts/selfcheck.py    end-to-end verification, model excluded
tests/                  unit tests: chunking, BM25, tool calls, agent, portfolio
```

## Disclaimer

Kinetic is a research tool, not personalised financial advice. Signals are
generated by statistical models over public market data and your own documents.
Markets carry risk; past performance does not predict future returns. Verify
every number before acting on it.
