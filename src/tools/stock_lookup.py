"""
Stock Lookup Tool — live stock/market data lookup.

Provides: ticker → current price, change %, volume, market cap, key stats.

Data sources:
    - Primary: yfinance (no API key required)
    - Fallback: Alpha Vantage (requires ALPHA_VANTAGE_API_KEY)

All prices are returned with explicit currency units (USD/INR).
Cached for 60 seconds to avoid excessive API calls.
"""

import time
from typing import Dict, Any, Optional

import yfinance as yf
from langchain_core.tools import tool
from cachetools import TTLCache

import config


# ─── Cache: stock data TTL = 60s ─────────────────────────────────────────────
_stock_cache = TTLCache(maxsize=100, ttl=config.STOCK_CACHE_TTL_SEC)


def _fetch_stock_yfinance(ticker: str) -> Dict[str, Any]:
    """Fetch stock data from Yahoo Finance."""
    stock = yf.Ticker(ticker)
    info = stock.info

    # Get current price — try multiple fields
    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose", 0)

    # Calculate change
    change = price - prev_close if price and prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0

    return {
        "ticker": ticker.upper(),
        "company_name": info.get("shortName", info.get("longName", ticker)),
        "current_price": round(price, 2),
        "currency": info.get("currency", "USD"),
        "change": round(change, 2),
        "change_percent": round(change_pct, 2),
        "volume": info.get("volume", 0),
        "market_cap": info.get("marketCap", 0),
        "day_high": info.get("dayHigh", 0),
        "day_low": info.get("dayLow", 0),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
        "pe_ratio": info.get("trailingPE", None),
        "dividend_yield": info.get("dividendYield", None),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "source": "Yahoo Finance (live market data)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }


def _fetch_stock_alpha_vantage(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fallback: fetch stock data from Alpha Vantage.
    Requires ALPHA_VANTAGE_API_KEY in .env.
    """
    if not config.ALPHA_VANTAGE_API_KEY:
        return None

    try:
        import requests

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": config.ALPHA_VANTAGE_API_KEY,
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json().get("Global Quote", {})

        if not data:
            return None

        price = float(data.get("05. price", 0))
        prev_close = float(data.get("08. previous close", 0))
        change = float(data.get("09. change", 0))
        change_pct = float(data.get("10. change percent", "0%").rstrip("%"))

        return {
            "ticker": ticker.upper(),
            "company_name": ticker.upper(),
            "current_price": round(price, 2),
            "currency": "USD",
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": int(data.get("06. volume", 0)),
            "market_cap": None,
            "day_high": float(data.get("03. high", 0)),
            "day_low": float(data.get("04. low", 0)),
            "source": "Alpha Vantage (live market data)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
    except Exception:
        return None


@tool
def get_stock_price(ticker: str) -> str:
    """
    Get the current live stock price and key market data for a given ticker symbol.

    Use this tool when the user asks about current stock prices, market data,
    or any real-time financial information for a specific company.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'RELIANCE.NS').
                For Indian stocks, append '.NS' for NSE or '.BO' for BSE.

    Returns:
        A formatted string with the current stock price, change, volume,
        market cap, and other key metrics. All prices include currency
        units (USD for US stocks, INR for Indian stocks).
        Data source is always explicitly stated (live market data).
    """
    ticker = ticker.strip().upper()

    # Check cache
    if ticker in _stock_cache:
        data = _stock_cache[ticker]
        return _format_stock_data(data)

    # Try yfinance first
    try:
        data = _fetch_stock_yfinance(ticker)
        _stock_cache[ticker] = data
        return _format_stock_data(data)
    except Exception as e:
        pass

    # Fallback to Alpha Vantage
    data = _fetch_stock_alpha_vantage(ticker)
    if data:
        _stock_cache[ticker] = data
        return _format_stock_data(data)

    return f"❌ Could not fetch data for ticker '{ticker}'. Please verify the symbol."


def _format_stock_data(data: Dict[str, Any]) -> str:
    """Format stock data into a readable string."""
    currency = data.get("currency", "USD")
    arrow = "🟢 ▲" if data["change"] >= 0 else "🔴 ▼"

    lines = [
        f"📈 {data['company_name']} ({data['ticker']})",
        f"   Price: {currency} {data['current_price']}",
        f"   Change: {arrow} {currency} {data['change']} ({data['change_percent']:+.2f}%)",
        f"   Volume: {data.get('volume', 'N/A'):,}" if data.get('volume') else "",
        f"   Market Cap: {currency} {_format_large_number(data.get('market_cap'))}" if data.get('market_cap') else "",
        f"   Day Range: {currency} {data.get('day_low', 'N/A')} - {currency} {data.get('day_high', 'N/A')}",
        f"   52-Week Range: {currency} {data.get('fifty_two_week_low', 'N/A')} - {currency} {data.get('fifty_two_week_high', 'N/A')}",
        f"   P/E Ratio: {data.get('pe_ratio', 'N/A')}",
        f"   Sector: {data.get('sector', 'N/A')}",
        f"",
        f"   📡 Source: {data['source']}",
        f"   🕐 As of: {data['timestamp']}",
    ]
    return "\n".join(line for line in lines if line)


def _format_large_number(num) -> str:
    """Format large numbers (e.g., market cap) with suffixes."""
    if num is None or num == 0:
        return "N/A"
    if num >= 1e12:
        return f"{num / 1e12:.2f}T"
    elif num >= 1e9:
        return f"{num / 1e9:.2f}B"
    elif num >= 1e6:
        return f"{num / 1e6:.2f}M"
    elif num >= 1e3:
        return f"{num / 1e3:.2f}K"
    return str(num)


def get_stock_data_raw(ticker: str) -> Dict[str, Any]:
    """
    Get raw stock data as a dictionary (for use by prediction engine).
    Not a LangChain tool — used internally.
    """
    ticker = ticker.strip().upper()
    if ticker in _stock_cache:
        return _stock_cache[ticker]

    try:
        data = _fetch_stock_yfinance(ticker)
        _stock_cache[ticker] = data
        return data
    except Exception:
        return {}


def get_historical_data(ticker: str, period: str = "3mo"):
    """
    Get historical price data for technical analysis.
    Returns a pandas DataFrame.

    Args:
        ticker: Stock ticker symbol.
        period: Data period (e.g., '1mo', '3mo', '6mo', '1y', '5y').
    """
    stock = yf.Ticker(ticker.strip().upper())
    return stock.history(period=period)
