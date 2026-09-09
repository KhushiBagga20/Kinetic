# Kinetic — Personal Investment Research Agent

A local, low-latency AI-driven financial research assistant and market intelligence platform. Built with an ensemble prediction algorithm, hybrid RAG pipeline, real-time market data dashboard, and MLX Apple Silicon local LLM integration.

---

## ⚡ Features

- 📊 **Real-time Market Dashboard**: Live stock prices, interactive candlestick charts with technical overlays (SMA, EMA, RSI, MACD, Bollinger Bands), and financial news via yfinance.
- 🤖 **Interactive Research Agent**: Multi-tool conversational agent capable of querying documents, retrieving real-time stock quotes, and fetching targeted market news.
- 📈 **Ensemble Market Prediction Engine**:
  - **Technical Analysis (40%)**: Trend, momentum, volatility, volume signals.
  - **Sentiment Analysis (30%)**: VADER sentiment analyzer on recent news.
  - **RAG & Fundamentals (30%)**: Document retrieval and fundamental metrics.
  - **Confidence & Risk Grading**: Outputs safety risk score (1–10) with risk warnings.
- ⚡ **Low-Latency RAG Pipeline**: In-memory vector store powered by ChromaDB and Sentence-Transformers (`all-MiniLM-L6-v2`), supporting PDF and text ingestion.
- 🍎 **Apple Silicon Ready (MLX)**: Optimized architecture with clean plug-and-play local LLM inference via Apple's MLX framework.
- 🔌 **Model Context Protocol (MCP)**: Built-in stdio-based MCP server exposing financial tools to external agents.

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/KhushiBagga20/Kinetic.git
cd Kinetic

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your API keys (optional, standard stock data works out-of-the-box with yfinance):
- `ALPHA_VANTAGE_API_KEY`: For backup stock & indicator data.
- `NEWS_API_KEY`: For live targeted financial news sentiment.
- `FMP_API_KEY`: For financial statements & ratios.

### 3. Run the Application

```bash
streamlit run app.py
```

---

## 🏗️ Architecture

```
Kinetic/
├── app.py                      # Main Streamlit application
├── config.py                   # Centralized configuration & environment loader
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables template
├── src/
│   ├── agent/                  # Research Agent & prompt orchestration
│   ├── llm/                    # Local LLM wrapper (MLX / HuggingFace fallback)
│   ├── mcp/                    # Model Context Protocol (MCP) server
│   ├── prediction/             # Technical, Sentiment, and Ensemble algorithms
│   ├── rag/                    # Fast document loader, splitter, ChromaDB vector store
│   └── tools/                  # Stock lookup, news fetcher, document retriever
└── ui/
    ├── dashboard.py            # Market dashboard & charts
    ├── chat.py                 # Conversational agent interface
    ├── prediction_view.py      # Algorithmic prediction interface
    └── styles.py               # Custom UI styling & themes
```

---

## ⚠️ Disclaimer

*This application is for research and educational purposes only. Market predictions and agent outputs are algorithmically generated and carry risk. None of the information presented constitutes financial or investment advice.*
