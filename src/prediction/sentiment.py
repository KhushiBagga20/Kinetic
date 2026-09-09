"""
Sentiment Analysis — analyzes news headlines for market sentiment.

Uses VADER (Valence Aware Dictionary and sEntiment Reasoner):
    - Designed for social media / news text
    - Returns compound score: -1 (negative) to +1 (positive)
    - Fast: no model loading required

Combines individual headline sentiment into an aggregate score.
"""

from typing import Dict, Any, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.tools.news_fetcher import get_news_for_sentiment


# ─── Singleton analyzer ──────────────────────────────────────────────────────
_analyzer = SentimentIntensityAnalyzer()


def analyze_headline(headline: str) -> Dict[str, float]:
    """
    Analyze sentiment of a single headline.

    Args:
        headline: News headline text.

    Returns:
        Dict with 'compound', 'pos', 'neg', 'neu' scores.
    """
    scores = _analyzer.polarity_scores(headline)
    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
    }


def analyze_multiple_headlines(headlines: List[str]) -> Dict[str, Any]:
    """
    Analyze sentiment across multiple headlines and compute aggregate score.

    Args:
        headlines: List of news headline strings.

    Returns:
        Dict with 'individual' scores, 'aggregate' compound, 'signal', 'description'.
    """
    if not headlines:
        return {
            "individual": [],
            "aggregate_compound": 0.0,
            "signal": 0,
            "description": "No headlines available for sentiment analysis",
            "headline_count": 0,
        }

    individual_scores = []
    compound_sum = 0.0

    for headline in headlines:
        scores = analyze_headline(headline)
        individual_scores.append({
            "headline": headline[:100],
            "compound": scores["compound"],
        })
        compound_sum += scores["compound"]

    # Aggregate: average compound score
    avg_compound = compound_sum / len(headlines)

    # Classify signal
    if avg_compound > 0.15:
        signal = 1
        desc = f"News sentiment is POSITIVE (avg: {avg_compound:+.3f}) — {len(headlines)} articles analyzed"
    elif avg_compound < -0.15:
        signal = -1
        desc = f"News sentiment is NEGATIVE (avg: {avg_compound:+.3f}) — {len(headlines)} articles analyzed"
    else:
        signal = 0
        desc = f"News sentiment is NEUTRAL (avg: {avg_compound:+.3f}) — {len(headlines)} articles analyzed"

    return {
        "individual": individual_scores,
        "aggregate_compound": round(avg_compound, 4),
        "signal": signal,
        "description": desc,
        "headline_count": len(headlines),
    }


def get_ticker_sentiment(ticker: str) -> Dict[str, Any]:
    """
    Get sentiment analysis for a stock ticker by fetching and analyzing its news.

    This is the main entry point for the prediction engine.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL').

    Returns:
        Dict with sentiment analysis results.
    """
    # Fetch news articles
    articles = get_news_for_sentiment(ticker)

    if not articles:
        return {
            "individual": [],
            "aggregate_compound": 0.0,
            "signal": 0,
            "description": f"No recent news found for {ticker} — cannot compute sentiment",
            "headline_count": 0,
        }

    # Extract headlines and descriptions for richer sentiment
    texts = []
    for article in articles:
        text = article.get("title", "")
        if article.get("description"):
            text += " " + article["description"]
        texts.append(text)

    result = analyze_multiple_headlines(texts)
    result["ticker"] = ticker

    return result
