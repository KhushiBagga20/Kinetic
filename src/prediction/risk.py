"""
Risk Assessment — evaluates risk and generates mandatory disclaimers.

Safety mechanisms:
    - Confidence thresholds for recommendations
    - Hedged language enforcement
    - Mandatory disclaimer on every output
    - Risk classification (LOW / MEDIUM / HIGH)
"""

from typing import Dict, Any

import config


def assess_risk(prediction_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess the risk level of a prediction and generate a safety report.

    Args:
        prediction_report: The output from EnsemblePredictor.predict().

    Returns:
        Risk assessment dict with level, factors, and disclaimer.
    """
    confidence = prediction_report.get("confidence", 0)
    signal = prediction_report.get("signal", "NEUTRAL")
    ensemble_score = prediction_report.get("ensemble_score", 0)

    # ── Risk Factors ──────────────────────────────────────────────────
    risk_factors = []

    # Low confidence
    if confidence < 40:
        risk_factors.append(
            "⚠️ Very low confidence — insufficient data for a reliable signal"
        )
    elif confidence < 60:
        risk_factors.append(
            "⚠️ Moderate confidence — results should be treated with caution"
        )

    # Conflicting signals
    if "MIXED" in signal:
        risk_factors.append(
            "⚠️ Conflicting signals detected — technical and sentiment "
            "indicators disagree"
        )

    # Extreme signals (overconfidence risk)
    if abs(ensemble_score) > 0.7:
        risk_factors.append(
            "⚠️ Very strong signal — extreme readings historically tend to "
            "reverse (mean reversion)"
        )

    # Missing data
    tech_details = prediction_report.get("technical", {}).get("details", {})
    sent_details = prediction_report.get("sentiment", {}).get("details", {})
    fund_details = prediction_report.get("fundamental", {}).get("details", {})

    if isinstance(tech_details, dict) and "error" in tech_details:
        risk_factors.append("⚠️ Technical analysis data unavailable")
    if isinstance(sent_details, dict) and "error" in sent_details:
        risk_factors.append("⚠️ News sentiment data unavailable")
    if isinstance(fund_details, dict) and fund_details.get("documents_found", 0) == 0:
        risk_factors.append(
            "⚠️ No financial documents uploaded — fundamental analysis incomplete"
        )

    # ── Risk Level ────────────────────────────────────────────────────
    if len(risk_factors) >= 3 or confidence < 30:
        risk_level = "HIGH"
    elif len(risk_factors) >= 1 or confidence < 60:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "risk_count": len(risk_factors),
        "recommendation_safe": confidence >= config.MIN_CONFIDENCE_THRESHOLD,
        "disclaimer": config.DISCLAIMER_TEXT,
    }


def format_prediction_report(prediction_report: Dict[str, Any]) -> str:
    """
    Format a prediction report into a readable string with mandatory disclaimer.

    Args:
        prediction_report: The output from EnsemblePredictor.predict().

    Returns:
        Formatted string report.
    """
    risk = assess_risk(prediction_report)
    ticker = prediction_report.get("ticker", "UNKNOWN")
    signal = prediction_report.get("signal", "NEUTRAL")
    confidence = prediction_report.get("confidence", 0)
    score = prediction_report.get("ensemble_score", 0)

    # ── Signal emoji ──────────────────────────────────────────────────
    if "BULLISH" in signal:
        signal_emoji = "🟢"
    elif "BEARISH" in signal:
        signal_emoji = "🔴"
    elif "MIXED" in signal or "INSUFFICIENT" in signal:
        signal_emoji = "🟡"
    else:
        signal_emoji = "⚪"

    # ── Build report ──────────────────────────────────────────────────
    lines = [
        "═" * 60,
        f"  📊 MARKET PREDICTION REPORT: {ticker}",
        "═" * 60,
        "",
        f"  {signal_emoji} Signal:     {signal}",
        f"  📈 Confidence:  {confidence:.1f}%",
        f"  ⚖️  Risk Level:  {risk['risk_level']}",
        f"  🔢 Score:       {score:+.4f}",
        "",
    ]

    # Key factors
    key_factors = prediction_report.get("key_factors", [])
    if key_factors:
        lines.append("  📋 Key Contributing Factors:")
        for i, factor in enumerate(key_factors, 1):
            lines.append(f"     {i}. {factor}")
        lines.append("")

    # Risk factors
    if risk["risk_factors"]:
        lines.append("  🛡️ Risk Assessment:")
        for factor in risk["risk_factors"]:
            lines.append(f"     {factor}")
        lines.append("")

    # Weight breakdown
    lines.extend([
        "  📊 Signal Breakdown:",
        f"     Technical  (40%): {prediction_report.get('technical', {}).get('score', 0):+.3f}",
        f"     Sentiment  (30%): {prediction_report.get('sentiment', {}).get('score', 0):+.3f}",
        f"     Fundamental(30%): {prediction_report.get('fundamental', {}).get('score', 0):+.3f}",
        "",
    ])

    # Mandatory disclaimer
    lines.extend([
        "─" * 60,
        f"  {config.DISCLAIMER_TEXT}",
        "─" * 60,
    ])

    return "\n".join(lines)
