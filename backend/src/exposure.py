"""
Automatic exposure — which of my holdings does today's news actually touch,
and is it good or bad for them?

For every detected theme (see `src/themes.py`) and every holding, four things
are measured, all on this machine:

    relevance   how close the company's profile is to the theme (embeddings)
    news link   how much of the company's own news today is about the theme
    tone        whether those headlines read positive or negative (sentiment)
    size        how much of the book the holding is, scaled by its beta

Together they give a score per holding, a direction (tailwind / headwind /
watch) and an impact figure for the whole portfolio.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import numpy as np

from src import portfolio, themes
from src.market import get_fundamentals, get_news

MATCH_THRESHOLD = 0.22   # below this score a holding is not considered exposed
LINK_THRESHOLD = 0.30    # a headline this close to the theme counts as evidence


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _direction(tone: float, has_evidence: bool) -> str:
    if not has_evidence:
        return "watch"
    if tone > 0.15:
        return "tailwind"
    if tone < -0.15:
        return "headwind"
    return "mixed"


def _sentiment(text: str) -> float:
    # Reuses the finance-tuned sentiment scorer from the forecast engine.
    from src.prediction import _score_headline

    return _score_headline(text)


def auto_report() -> dict[str, Any]:
    """Build the full automatic exposure report for the current portfolio."""
    from src.rag.embeddings import embed

    rows = portfolio.positions()
    if not rows:
        return {"themes": [], "holdings": [], "as_of": _now(), "empty": True}

    detected = themes.detect_themes([row.symbol for row in rows])
    if not detected:
        return {"themes": [], "holdings": [], "as_of": _now(), "empty": False}

    # -- gather each holding's live profile and headlines ----------------------
    with ThreadPoolExecutor(max_workers=min(8, len(rows))) as pool:
        profiles = list(pool.map(portfolio._profile, rows))
        news = list(pool.map(lambda row: get_news(row.symbol, limit=6), rows))
    betas = [float(get_fundamentals(row.symbol).get("beta") or 1.0) for row in rows]

    # -- embed everything once ---------------------------------------------------
    theme_vectors = np.asarray(embed([t["theme"] for t in detected]), dtype=np.float32)
    profile_vectors = np.asarray(embed(profiles), dtype=np.float32)
    relevance = profile_vectors @ theme_vectors.T  # (holdings, themes)

    headline_texts = [[f"{a.title}. {a.summary}".strip() for a in articles] for articles in news]
    flat = [text for texts in headline_texts for text in texts]
    flat_vectors = np.asarray(embed(flat), dtype=np.float32) if flat else np.zeros((0, theme_vectors.shape[1]))
    tones = [_sentiment(text) for text in flat]

    # -- score every holding against every theme -------------------------------
    report_themes = []
    per_holding: dict[str, list[dict[str, Any]]] = {row.symbol: [] for row in rows}
    offset = 0
    offsets = []
    for texts in headline_texts:
        offsets.append(offset)
        offset += len(texts)

    for t_index, theme in enumerate(detected):
        matches = []
        for h_index, row in enumerate(rows):
            start, count = offsets[h_index], len(headline_texts[h_index])
            sims = flat_vectors[start:start + count] @ theme_vectors[t_index] if count else np.array([])
            news_link = float(sims.max()) if len(sims) else 0.0
            score = 0.65 * float(relevance[h_index, t_index]) + 0.35 * max(0.0, news_link)
            if score < MATCH_THRESHOLD:
                continue

            # Evidence: this holding's headlines that are actually about the theme.
            evidence_ids = [i for i, sim in enumerate(sims) if sim >= LINK_THRESHOLD]
            if evidence_ids:
                weights = np.array([sims[i] for i in evidence_ids])
                tone = float(np.average([tones[start + i] for i in evidence_ids], weights=weights))
            else:
                tone = 0.0
            direction = _direction(tone, bool(evidence_ids))

            beta = max(0.3, min(2.0, betas[h_index]))
            impact = score * (row.weight / 100) * beta  # share of the book this touches, risk-scaled

            articles = news[h_index]
            evidence = [
                {
                    "title": articles[i].title,
                    "publisher": articles[i].publisher,
                    "published": articles[i].published,
                    "url": articles[i].url,
                    "sentiment": round(tones[start + i], 3),
                }
                for i in sorted(evidence_ids, key=lambda i: sims[i], reverse=True)[:2]
            ]
            match = {
                "symbol": row.symbol,
                "name": row.name,
                "weight": round(row.weight, 2),
                "score": round(score, 3),
                "relevance": round(float(relevance[h_index, t_index]), 3),
                "news_link": round(news_link, 3),
                "tone": round(tone, 3),
                "direction": direction,
                "beta": round(beta, 2),
                "impact": round(impact * 100, 2),
                "day_change_percent": row.day_change_percent,
                "sector": row.sector or "Unclassified",
                "evidence": evidence,
            }
            matches.append(match)
            per_holding[row.symbol].append({"theme": theme["theme"], "score": match["score"], "direction": direction})

        if not matches:
            continue
        matches.sort(key=lambda m: m["impact"], reverse=True)
        total_impact = sum(m["impact"] for m in matches)
        weighted_tone = (
            sum(m["tone"] * m["impact"] for m in matches) / total_impact if total_impact else 0.0
        )
        directions = {m["direction"] for m in matches}
        if {"tailwind", "headwind"} <= directions:
            theme_direction = "mixed"  # good for some holdings, bad for others
        else:
            theme_direction = _direction(weighted_tone, any(m["evidence"] for m in matches))
        report_themes.append(
            {
                "theme": theme["theme"],
                "source": theme["source"],
                "headline_count": theme.get("headline_count", 0),
                "headlines": theme.get("headlines", []),
                "book_share": round(sum(m["weight"] for m in matches), 2),
                "impact": round(total_impact, 2),
                "tone": round(weighted_tone, 3),
                "direction": theme_direction,
                "holdings": matches,
            }
        )

    report_themes.sort(key=lambda t: t["impact"], reverse=True)

    holdings = []
    for row in rows:
        touched = sorted(per_holding[row.symbol], key=lambda m: m["score"], reverse=True)
        holdings.append(
            {
                "symbol": row.symbol,
                "name": row.name,
                "weight": round(row.weight, 2),
                "day_change_percent": row.day_change_percent,
                "themes": touched[:4],
                "headwinds": sum(1 for m in touched if m["direction"] == "headwind"),
                "tailwinds": sum(1 for m in touched if m["direction"] == "tailwind"),
            }
        )

    headwinds = [t for t in report_themes if t["direction"] == "headwind"]
    return {
        "themes": report_themes,
        "holdings": holdings,
        "top_risk": headwinds[0]["theme"] if headwinds else None,
        "as_of": _now(),
        "empty": False,
    }


def to_text(report: dict[str, Any]) -> str:
    """The exposure report as the model should read it."""
    if report.get("empty"):
        return "The portfolio is empty, so there is no exposure to assess."
    if not report.get("themes"):
        return f"No holding shows meaningful exposure to today's themes (checked {report['as_of']})."
    lines = [f"Automatic exposure scan of the portfolio against today's themes (as of {report['as_of']}):"]
    for theme in report["themes"]:
        lines.append(
            f"- {theme['theme']} [{theme['direction']}]: touches {theme['book_share']:.1f}% of the book, "
            f"impact score {theme['impact']:.2f}"
        )
        for match in theme["holdings"][:4]:
            lines.append(
                f"    · {match['symbol']} ({match['weight']:.1f}% of book): {match['direction']}, "
                f"score {match['score']:.2f}, headline tone {match['tone']:+.2f}"
            )
            for article in match["evidence"][:1]:
                lines.append(f"      evidence: \"{article['title']}\" — {article['publisher']}")
    if report.get("top_risk"):
        lines.append(f"Biggest headwind today: {report['top_risk']}")
    return "\n".join(lines)
