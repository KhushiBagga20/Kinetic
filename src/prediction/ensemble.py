"""
Ensemble Scorer — combines technical, sentiment, and fundamental signals.

Weighted ensemble:
    - Technical indicators: 40%
    - News sentiment: 30%
    - Fundamental (RAG): 30%

Outputs:
    - Signal: BULLISH / BEARISH / NEUTRAL
    - Confidence: 0-100%
    - Risk Level: LOW / MEDIUM / HIGH
    - Key contributing factors
"""

from typing import Dict, Any, List, Optional, Tuple

import config
from src.prediction.technical import (
    run_all_technical_indicators,
    get_technical_score,
)
from src.prediction.sentiment import get_ticker_sentiment
from src.tools.stock_lookup import get_historical_data
from src.rag.vector_store import similarity_search


class EnsemblePredictor:
    """
    Multi-signal ensemble prediction engine.

    Combines three signal categories:
        1. Technical indicators (RSI, MACD, Bollinger, SMA, Volume)
        2. News sentiment (VADER on recent headlines)
        3. Fundamental data from uploaded documents (RAG)

    Safety-first approach:
        - Low confidence → "INSUFFICIENT DATA"
        - Conflicting signals → "MIXED SIGNALS"
        - Never uses absolute language
    """

    def __init__(self):
        self.technical_weight = config.TECHNICAL_WEIGHT   # 0.40
        self.sentiment_weight = config.SENTIMENT_WEIGHT   # 0.30
        self.fundamental_weight = config.FUNDAMENTAL_WEIGHT  # 0.30
        self.min_confidence = config.MIN_CONFIDENCE_THRESHOLD  # 40

    def predict(self, ticker: str) -> Dict[str, Any]:
        """
        Generate a full prediction report for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL').

        Returns:
            Comprehensive prediction report dict.
        """
        ticker = ticker.strip().upper()
        report = {
            "ticker": ticker,
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "risk_level": "UNKNOWN",
            "key_factors": [],
            "technical": {},
            "sentiment": {},
            "fundamental": {},
            "disclaimer": config.DISCLAIMER_TEXT,
        }

        # ── 1. Technical Analysis (40% weight) ───────────────────────
        tech_score, tech_details = self._compute_technical(ticker)
        report["technical"] = {
            "score": tech_score,
            "details": tech_details,
        }

        # ── 2. Sentiment Analysis (30% weight) ──────────────────────
        sent_score, sent_details = self._compute_sentiment(ticker)
        report["sentiment"] = {
            "score": sent_score,
            "details": sent_details,
        }

        # ── 3. Fundamental Analysis from RAG (30% weight) ───────────
        fund_score, fund_details = self._compute_fundamental(ticker)
        report["fundamental"] = {
            "score": fund_score,
            "details": fund_details,
        }

        # ── 4. Ensemble Score ────────────────────────────────────────
        ensemble_score = (
            tech_score * self.technical_weight
            + sent_score * self.sentiment_weight
            + fund_score * self.fundamental_weight
        )

        # Confidence = how strongly the signals agree (0-100)
        scores = [tech_score, sent_score, fund_score]
        agreement = self._compute_agreement(scores)
        confidence = min(100, max(0, abs(ensemble_score) * 100 * agreement))

        # ── 5. Classify Signal ───────────────────────────────────────
        signal, risk_level = self._classify_signal(
            ensemble_score, confidence, scores
        )

        report["signal"] = signal
        report["confidence"] = round(confidence, 1)
        report["risk_level"] = risk_level
        report["ensemble_score"] = round(ensemble_score, 4)
        report["key_factors"] = self._extract_key_factors(report)

        return report

    def _compute_technical(self, ticker: str) -> Tuple[float, Dict]:
        """Compute technical indicator score."""
        try:
            data = get_historical_data(ticker, period="3mo")
            if data is None or data.empty:
                return 0.0, {"error": "No historical data available"}

            indicators = run_all_technical_indicators(data)
            score, description = get_technical_score(indicators)

            return score, {
                "indicators": indicators,
                "summary": description,
            }
        except Exception as e:
            return 0.0, {"error": f"Technical analysis failed: {e}"}

    def _compute_sentiment(self, ticker: str) -> Tuple[float, Dict]:
        """Compute news sentiment score."""
        try:
            sentiment = get_ticker_sentiment(ticker)
            # Map compound score (-1 to +1) directly as signal
            score = sentiment.get("aggregate_compound", 0.0)
            signal = sentiment.get("signal", 0)

            return float(signal) if signal != 0 else score, sentiment
        except Exception as e:
            return 0.0, {"error": f"Sentiment analysis failed: {e}"}

    def _compute_fundamental(self, ticker: str) -> Tuple[float, Dict]:
        """
        Compute fundamental score from RAG-retrieved document data.

        Searches for financial metrics related to the ticker in
        uploaded documents. If no relevant documents are found,
        returns a neutral score.
        """
        try:
            queries = [
                f"{ticker} revenue earnings growth",
                f"{ticker} financial performance outlook",
                f"{ticker} risk factors debt",
            ]

            all_docs = []
            for query in queries:
                results = similarity_search(query, k=2)
                all_docs.extend(results)

            if not all_docs:
                return 0.0, {
                    "description": "No relevant documents found for fundamental analysis",
                    "documents_found": 0,
                }

            # Extract text for analysis
            doc_text = "\n".join(doc.page_content[:300] for doc in all_docs)

            # Simple keyword-based fundamental scoring
            score = self._score_fundamental_text(doc_text)

            return score, {
                "description": f"Analyzed {len(all_docs)} document chunks",
                "documents_found": len(all_docs),
                "sources": [
                    doc.metadata.get("source_file", "unknown") for doc in all_docs
                ],
            }
        except Exception as e:
            return 0.0, {"error": f"Fundamental analysis failed: {e}"}

    def _score_fundamental_text(self, text: str) -> float:
        """
        Simple keyword-based scoring of fundamental text.
        Returns a score from -1.0 to +1.0.
        """
        text_lower = text.lower()

        bullish_keywords = [
            "growth", "increase", "profit", "strong", "beat",
            "exceed", "outperform", "upgrade", "positive", "improving",
            "record", "expand", "momentum", "dividend increase",
        ]
        bearish_keywords = [
            "decline", "loss", "weak", "miss", "below",
            "downgrade", "risk", "debt", "concern", "challenging",
            "headwind", "restructuring", "impairment", "warning",
        ]

        bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        return (bullish_count - bearish_count) / total

    def _compute_agreement(self, scores: List[float]) -> float:
        """
        Compute how much the signals agree.
        Returns 0.0 (complete disagreement) to 1.5 (strong agreement).
        """
        # If all same sign → high agreement
        positive = sum(1 for s in scores if s > 0)
        negative = sum(1 for s in scores if s < 0)
        neutral = sum(1 for s in scores if s == 0)

        if positive == len(scores) or negative == len(scores):
            return 1.5  # Perfect agreement → confidence boost
        elif neutral == len(scores):
            return 0.5  # All neutral → low confidence
        elif positive > 0 and negative > 0:
            return 0.6  # Conflicting → reduced confidence
        else:
            return 1.0  # Mostly agreeing

    def _classify_signal(
        self,
        ensemble_score: float,
        confidence: float,
        scores: List[float],
    ) -> Tuple[str, str]:
        """
        Classify the final signal and risk level.

        Safety mechanisms:
            - Confidence < 40% → INSUFFICIENT DATA
            - Conflicting signals → MIXED SIGNALS
        """
        # Check for conflicting signals
        has_bullish = any(s > 0.1 for s in scores)
        has_bearish = any(s < -0.1 for s in scores)

        if confidence < self.min_confidence:
            return "INSUFFICIENT DATA — NO RECOMMENDATION", "HIGH"

        if has_bullish and has_bearish:
            if abs(ensemble_score) < 0.15:
                return "MIXED SIGNALS — EXERCISE CAUTION", "HIGH"

        # Classify signal
        if ensemble_score > 0.3:
            signal = "BULLISH"
            risk = "MEDIUM" if confidence < 60 else "LOW"
        elif ensemble_score > 0.1:
            signal = "MILDLY BULLISH"
            risk = "MEDIUM"
        elif ensemble_score < -0.3:
            signal = "BEARISH"
            risk = "MEDIUM" if confidence < 60 else "LOW"
        elif ensemble_score < -0.1:
            signal = "MILDLY BEARISH"
            risk = "MEDIUM"
        else:
            signal = "NEUTRAL"
            risk = "LOW"

        return signal, risk

    def _extract_key_factors(self, report: Dict[str, Any]) -> List[str]:
        """Extract the top 3 key contributing factors from the report."""
        factors = []

        # Technical
        tech = report.get("technical", {})
        if isinstance(tech.get("details"), dict):
            indicators = tech["details"].get("indicators", {})
            for name, result in indicators.items():
                if isinstance(result, dict) and result.get("signal", 0) != 0:
                    factors.append(
                        (abs(result.get("signal", 0)), result.get("description", name))
                    )

        # Sentiment
        sent = report.get("sentiment", {})
        if isinstance(sent.get("details"), dict):
            desc = sent["details"].get("description", "")
            if desc:
                factors.append((abs(sent.get("score", 0)), desc))

        # Fundamental
        fund = report.get("fundamental", {})
        if isinstance(fund.get("details"), dict):
            desc = fund["details"].get("description", "")
            if desc:
                factors.append((abs(fund.get("score", 0)), desc))

        # Sort by impact and take top 3
        factors.sort(key=lambda x: x[0], reverse=True)
        return [f[1] for f in factors[:3]]


# ─── Factory ─────────────────────────────────────────────────────────────────

_predictor_instance: Optional[EnsemblePredictor] = None


def get_predictor() -> EnsemblePredictor:
    """Get the singleton ensemble predictor."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = EnsemblePredictor()
    return _predictor_instance
