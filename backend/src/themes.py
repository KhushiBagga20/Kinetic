"""
Theme detection — what is the market talking about today?

Instead of asking the user to type "oil prices" or "rupee weakness", the
themes are found automatically from today's live headlines for their own
holdings and the wider market:

    1. the local model reads the headlines and names the themes (when loaded)
    2. a keyword map spots well-known themes in the same headlines (always)
    3. a short baseline list of macro themes is always checked as well

Every theme is then tested against the portfolio in `src/exposure.py`.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import config
from src.market import Article, get_news

# Well-known market themes and the words that signal them in a headline.
THEME_KEYWORDS: dict[str, list[str]] = {
    "interest rate changes": ["rate", "rates", "rbi", "fed", "repo", "yield", "yields", "bond", "inflation", "monetary"],
    "oil and energy prices": ["oil", "crude", "brent", "opec", "natural gas", "energy", "fuel"],
    "rupee and currency moves": ["rupee", "dollar", "currency", "forex", "fx"],
    "AI and technology spending": ["ai", "artificial intelligence", "chip", "chips", "semiconductor", "cloud", "data center", "software"],
    "consumer demand slowdown": ["consumer", "demand", "retail", "spending", "fmcg", "sales slump"],
    "government regulation and policy": ["regulation", "regulator", "sebi", "policy", "government", "tax", "ban", "probe", "antitrust"],
    "trade tariffs and exports": ["tariff", "tariffs", "export", "exports", "imports", "trade war", "sanction", "sanctions"],
    "banking and credit conditions": ["bank", "banks", "loan", "loans", "credit", "npa", "lending", "deposit", "deposits"],
    "earnings season results": ["earnings", "results", "quarterly", "profit", "revenue", "guidance"],
    "geopolitical tension": ["war", "conflict", "tension", "tensions", "geopolitical", "missile", "attack", "border"],
    "commodity and metal prices": ["gold", "silver", "steel", "copper", "metal", "metals", "aluminium", "commodity"],
    "mergers and deals": ["acquire", "acquires", "acquisition", "merger", "deal", "stake", "buyout"],
}


def gather_headlines(symbols: list[str], per_symbol: int = 6) -> list[Article]:
    """Today's headlines for every symbol plus the broad market, de-duplicated."""
    queries = list(dict.fromkeys(symbols)) + ["stock market today"]
    with ThreadPoolExecutor(max_workers=min(8, len(queries))) as pool:
        batches = list(pool.map(lambda q: get_news(q, limit=per_symbol), queries))

    seen: set[str] = set()
    unique: list[Article] = []
    for batch in batches:
        for article in batch:
            key = article.title.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(article)
    return unique


def _mentions(text: str, keyword: str) -> bool:
    """Whole-word match, so 'ai' does not match 'said'."""
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def keyword_themes(headlines: list[Article]) -> list[dict[str, Any]]:
    """Known themes that appear in today's headlines, most mentioned first."""
    found = []
    for theme, keywords in THEME_KEYWORDS.items():
        titles = [
            article.title
            for article in headlines
            if any(_mentions(f"{article.title} {article.summary}".lower(), k) for k in keywords)
        ]
        if titles:
            found.append({"theme": theme, "source": "news", "headline_count": len(titles), "headlines": titles[:3]})
    return sorted(found, key=lambda item: item["headline_count"], reverse=True)


def model_themes(headlines: list[Article], limit: int) -> list[str]:
    """
    Ask the local model to name today's themes. Returns [] when the model is
    not loaded or its answer cannot be read — the keyword themes still work.
    """
    from src.llm import engine

    llm = engine()
    if not llm.is_loaded or not headlines:
        return []

    listing = "\n".join(f"- {article.title}" for article in headlines[:40])
    messages = [
        {
            "role": "system",
            "content": (
                "You read financial headlines and name the market themes behind them. "
                "Reply with a JSON array of short theme phrases (2 to 6 words each), nothing else."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Today's headlines:\n{listing}\n\n"
                f"Name up to {limit} distinct themes that could move stock prices, such as "
                '"rising crude oil prices" or "RBI rate cut expectations". JSON array only.'
            ),
        },
    ]
    try:
        text = llm.write(messages, max_tokens=200)
    except Exception:
        return []

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [str(item).strip() for item in items if isinstance(item, str) and 2 < len(item.strip()) < 80][:limit]


def detect_themes(symbols: list[str], limit: int | None = None) -> list[dict[str, Any]]:
    """
    The themes worth testing the portfolio against right now.

    Model-named themes come first (most specific to today), then news themes
    from the keyword map, then the baseline macro themes to fill the list.
    """
    limit = limit or config.AUTO_THEMES
    headlines = gather_headlines(symbols)

    candidates: list[dict[str, Any]] = []
    for theme in model_themes(headlines, limit):
        candidates.append({"theme": theme, "source": "model", "headline_count": 0, "headlines": []})
    candidates += keyword_themes(headlines)
    for theme in config.BASELINE_THEMES:
        candidates.append({"theme": theme, "source": "baseline", "headline_count": 0, "headlines": []})

    seen: set[str] = set()
    themes: list[dict[str, Any]] = []
    for item in candidates:
        key = item["theme"].lower()
        if key not in seen:
            seen.add(key)
            themes.append(item)
    return themes[:limit]
