"""
FastMCP Server — serves tools via MCP protocol (Bonus Feature).

Exposes the stock lookup and document retrieval tools as MCP endpoints.
The agent can connect to this server via MultiServerMCPClient.

Usage:
    # Terminal 1: Start the MCP server
    python -m src.mcp.server

    # Terminal 2: Run the Streamlit app (agent auto-connects)
    streamlit run app.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import config

try:
    from fastmcp import FastMCP
except ImportError:
    print(
        "❌ FastMCP not installed. Install with: pip install fastmcp\n"
        "   This is an optional bonus feature."
    )
    sys.exit(1)


# ─── Create MCP Server ──────────────────────────────────────────────────────
mcp = FastMCP(
    name="FinancialToolsServer",
    description="MCP server exposing financial research tools (stock lookup, document retrieval)",
)


@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """
    Get the current live stock price and key market data for a given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'RELIANCE.NS').
                For Indian stocks, append '.NS' for NSE or '.BO' for BSE.

    Returns:
        Formatted string with current price, change, volume, market cap.
        All prices include currency units (USD/INR).
    """
    from src.tools.stock_lookup import get_stock_price as _get_stock

    return _get_stock.invoke({"ticker": ticker})


@mcp.tool()
def get_market_news(query: str) -> str:
    """
    Get recent market news for a given stock ticker or financial topic.

    Args:
        query: A stock ticker or financial topic (e.g., 'AAPL', 'inflation').

    Returns:
        Formatted list of top 5 recent news headlines with sources and dates.
    """
    from src.tools.news_fetcher import get_market_news as _get_news

    return _get_news.invoke({"query": query})


@mcp.tool()
def retrieve_financial_docs(query: str) -> str:
    """
    Retrieve relevant information from uploaded financial documents via RAG.

    Args:
        query: Natural language question about financial document content.

    Returns:
        Top 3 relevant document excerpts with source attribution.
    """
    from src.tools.document_retriever import retrieve_financial_docs as _retrieve

    return _retrieve.invoke({"query": query})


# ─── Run server ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Starting FastMCP server on {config.MCP_SERVER_HOST}:{config.MCP_SERVER_PORT}")
    print(f"   Tools available: get_stock_price, get_market_news, retrieve_financial_docs")
    print(f"   Connect with MultiServerMCPClient in your agent.")
    mcp.run(
        transport="sse",
        host=config.MCP_SERVER_HOST,
        port=config.MCP_SERVER_PORT,
    )
