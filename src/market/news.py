"""
Live financial news.

Two providers, merged and de-duplicated:
    * Yahoo Finance  — always available, no key, ticker- and keyword-aware
    * NewsAPI.org    — used automatically when NEWS_API_KEY is set

Articles are normalised into one shape so the rest of the app never has to
care which provider a headline came from.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

import requests
import yfinance as yf
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

import config

_news_cache: TTLCache = TTLCache(maxsize=128, ttl=config.NEWS_TTL_SEC)
_cache_lock = threading.RLock()


@dataclass
class Article:
    title: str
    publisher: str
    published: str
    url: str
    summary: str
    provider: str
    symbol: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        parts = [f"{self.title} — {self.publisher}, {self.published}"]
        if self.summary:
            parts.append(self.summary)
        if self.url:
            parts.append(self.url)
        return "\n".join(parts)


def _iso(value: Any) -> str:
    """Normalise Yahoo/NewsAPI timestamps to `YYYY-MM-DD HH:MM UTC`."""
    if not value:
        return ""
    try:
        if isinstance(value, (int, float)):
            stamp = datetime.fromtimestamp(float(value), tz=timezone.utc)
        else:
            stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            stamp = stamp.astimezone(timezone.utc)
        return stamp.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OSError):
        return str(value)


def _clean(text: str, limit: int = 400) -> str:
    """Strip the HTML Yahoo embeds in article summaries."""
    import re

    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _from_yahoo(items: list[dict], symbol: str) -> list[Article]:
    articles: list[Article] = []
    for item in items or []:
        body = item.get("content") or item  # Yahoo moved fields under "content"
        url = (
            (body.get("canonicalUrl") or {}).get("url")
            or (body.get("clickThroughUrl") or {}).get("url")
            or item.get("link", "")
        )
        provider = body.get("provider") or {}
        title = body.get("title") or ""
        if not title:
            continue
        articles.append(
            Article(
                title=title,
                publisher=provider.get("displayName") or item.get("publisher") or "Yahoo Finance",
                published=_iso(body.get("pubDate") or item.get("providerPublishTime")),
                url=url,
                summary=_clean(body.get("summary") or body.get("description") or ""),
                provider="Yahoo Finance",
                symbol=symbol,
            )
        )
    return articles


def _yahoo_news(query: str, limit: int) -> list[Article]:
    """Ticker news when `query` is a symbol, keyword news otherwise."""
    articles: list[Article] = []
    try:
        articles += _from_yahoo(yf.Ticker(query).news or [], query.upper())
    except Exception:
        pass
    if len(articles) < limit:
        try:
            search = yf.Search(query, news_count=limit, max_results=1)
            articles += _from_yahoo(search.news or [], "")
        except Exception:
            pass
    return articles


def _newsapi_news(query: str, limit: int) -> list[Article]:
    if not config.NEWS_API_KEY:
        return []
    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "apiKey": config.NEWS_API_KEY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": limit,
            },
            timeout=config.HTTP_TIMEOUT_SEC,
        )
        payload = response.json()
    except Exception:
        return []
    if payload.get("status") != "ok":
        return []
    return [
        Article(
            title=item.get("title") or "",
            publisher=(item.get("source") or {}).get("name", "NewsAPI"),
            published=_iso(item.get("publishedAt")),
            url=item.get("url", ""),
            summary=_clean(item.get("description") or ""),
            provider="NewsAPI",
        )
        for item in payload.get("articles", [])
        if item.get("title")
    ]


@cached(_news_cache, key=lambda query, limit=None: hashkey("news", query, limit), lock=_cache_lock)
def get_news(query: str, limit: int | None = None) -> list[Article]:
    """
    Recent headlines for a ticker or a topic, newest first.

    Args:
        query: a ticker ("NVDA") or a search phrase ("semiconductor exports").
        limit: maximum number of articles (defaults to config.NEWS_LIMIT).
    """
    query = query.strip()
    limit = limit or config.NEWS_LIMIT
    if not query:
        return []

    merged = _yahoo_news(query, limit) + _newsapi_news(query, limit)

    seen: set[str] = set()
    unique: list[Article] = []
    for article in merged:
        key = article.url or article.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(article)

    unique.sort(key=lambda a: a.published, reverse=True)
    return unique[:limit]
