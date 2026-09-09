"""
News Fetcher Tool — fetches recent market news for a given ticker or topic.

Data source: NewsAPI.org (requires NEWS_API_KEY)
Fallback: yfinance news (no key required, less reliable)

Cached for 5 minutes to reduce API calls.
Returns top 5 headlines with source, date, and URL.
"""

import time
from typing import Dict, Any, List, Optional

from langchain_core.tools import tool
from cachetools import TTLCache

import config


# ─── Cache: news TTL = 5 minutes ─────────────────────────────────────────────
_news_cache = TTLCache(maxsize=50, ttl=config.NEWS_CACHE_TTL_SEC)


def _fetch_news_api(query: str) -> List[Dict[str, Any]]:
    """
    Fetch news from NewsAPI.org.
    Requires NEWS_API_KEY in .env.
    """
    if not config.NEWS_API_KEY:
        return []

    try:
        import requests

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": config.NEWS_API_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": config.MAX_NEWS_RESULTS,
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            return []

        articles = []
        for article in data.get("articles", [])[:config.MAX_NEWS_RESULTS]:
            articles.append({
                "title": article.get("title", "No title"),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", "Unknown"),
                "description": article.get("description", "")[:200],
                "url": article.get("url", ""),
            })
        return articles

    except Exception:
        return []


def _fetch_news_yfinance(ticker: str) -> List[Dict[str, Any]]:
    """
    Fallback: fetch news from yfinance.
    No API key required.
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return []

        articles = []
        for item in news[:config.MAX_NEWS_RESULTS]:
            articles.append({
                "title": item.get("title", "No title"),
                "source": item.get("publisher", "Unknown"),
                "published_at": time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.gmtime(item.get("providerPublishTime", 0))
                ) if item.get("providerPublishTime") else "Unknown",
                "description": "",
                "url": item.get("link", ""),
            })
        return articles

    except Exception:
        return []


@tool
def get_market_news(query: str) -> str:
    """
    Get recent market news for a given stock ticker or financial topic.

    Use this tool when the user asks about recent news, market events,
    or developments related to a company or financial topic.

    Args:
        query: A stock ticker symbol (e.g., 'AAPL', 'Tesla') or a
               financial topic (e.g., 'Fed interest rate', 'inflation').

    Returns:
        A formatted list of the top 5 most recent news headlines with
        source publication name, date, and brief description.
        Data source is always stated (live news feed).
    """
    query_key = query.strip().upper()

    # Check cache
    if query_key in _news_cache:
        return _format_news(_news_cache[query_key], query)

    # Try NewsAPI first
    articles = _fetch_news_api(query)

    # Fallback to yfinance
    if not articles:
        articles = _fetch_news_yfinance(query)

    if not articles:
        return (
            f"📰 No recent news found for '{query}'.\n"
            "This may be because the NewsAPI key is not configured or the "
            "ticker/topic has no recent coverage. Please check your .env file."
        )

    _news_cache[query_key] = articles
    return _format_news(articles, query)


def _format_news(articles: List[Dict[str, Any]], query: str) -> str:
    """Format news articles into a readable string."""
    lines = [
        f"📰 Recent News for: {query}",
        f"   ({len(articles)} articles found)",
        "",
    ]

    for i, article in enumerate(articles, 1):
        lines.extend([
            f"  {i}. {article['title']}",
            f"     📌 Source: {article['source']} | 📅 {article['published_at']}",
            f"     {article['description']}" if article["description"] else "",
            f"     🔗 {article['url']}" if article["url"] else "",
            "",
        ])

    lines.append(f"  📡 Source: Live news feed")
    lines.append(f"  🕐 Retrieved: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

    return "\n".join(line for line in lines if line is not None)


def get_news_for_sentiment(query: str) -> List[Dict[str, Any]]:
    """
    Get raw news articles for sentiment analysis (used by prediction engine).
    Not a LangChain tool — used internally.

    Returns:
        List of article dictionaries with title, source, description.
    """
    query_key = query.strip().upper()

    if query_key in _news_cache:
        return _news_cache[query_key]

    articles = _fetch_news_api(query)
    if not articles:
        articles = _fetch_news_yfinance(query)

    if articles:
        _news_cache[query_key] = articles

    return articles
