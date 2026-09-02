"""
analyst_sentiment.py

Analyst Sentiment Score 0-100.

Ocena:
- konsensus analityków
- potencjał względem średniego targetu
- liczba analityków
- rozpiętość targetów
"""

import math


def _number(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value):
        return None

    return value


def _add_reason(reasons, points, text):
    reasons.append({
        "points": points,
        "text": text,
    })


def calculate_analyst_sentiment(analysis):
    """
    Oblicza Analyst Sentiment Score 0-100.

    Zwraca:
        (score, reasons)
    """

    info = analysis.instrument_info or {}

    score = 0
    reasons = []

    price = _number(getattr(analysis, "price", None))

    recommendation = str(
        info.get("recommendationKey") or ""
    ).lower().strip()

    # =========================================================
    # 1. KONSENSUS — 40 pkt
    # =========================================================

    recommendation_points = {
        "strong_buy": 40,
        "buy": 32,
        "hold": 18,
        "underperform": 7,
        "sell": 0,
        "strong_sell": 0,
    }

    if recommendation in recommendation_points:
        points = recommendation_points[recommendation]
        score += points

        labels = {
            "strong_buy": "Strong Buy",
            "buy": "Buy",
            "hold": "Hold",
            "underperform": "Underperform",
            "sell": "Sell",
            "strong_sell": "Strong Sell",
        }

        _add_reason(
            reasons,
            points,
            f"Konsensus analityków: {labels.get(recommendation, recommendation)}"
        )
    else:
        _add_reason(
            reasons,
            0,
            "Brak konsensusu analityków"
        )

    # =========================================================
    # 2. UPSIDE DO TARGETU — 30 pkt
    # =========================================================

    target_mean = _number(info.get("targetMeanPrice"))

    analyst_upside_pct = None

    if price is not None and price > 0 and target_mean is not None:
        analyst_upside_pct = (
            (target_mean - price) / price
        ) * 100

        if analyst_upside_pct >= 30:
            points = 30
        elif analyst_upside_pct >= 20:
            points = 25
        elif analyst_upside_pct >= 10:
            points = 18
        elif analyst_upside_pct >= 5:
            points = 10
        elif analyst_upside_pct >= 0:
            points = 5
        else:
            points = 0

        score += points

        _add_reason(
            reasons,
            points,
            f"Potencjał do średniego targetu: {analyst_upside_pct:+.1f}%"
        )
    else:
        _add_reason(
            reasons,
            0,
            "Brak ceny docelowej analityków"
        )

    # =========================================================
    # 3. LICZBA ANALITYKÓW — 10 pkt
    # =========================================================

    analyst_count = _number(
        info.get("numberOfAnalystOpinions")
    )

    if analyst_count is not None:
        if analyst_count >= 20:
            points = 10
        elif analyst_count >= 10:
            points = 8
        elif analyst_count >= 5:
            points = 5
        elif analyst_count >= 3:
            points = 3
        else:
            points = 0

        score += points

        _add_reason(
            reasons,
            points,
            f"Liczba opinii analityków: {int(analyst_count)}"
        )
    else:
        _add_reason(
            reasons,
            0,
            "Brak informacji o liczbie analityków"
        )

    # =========================================================
    # 4. ROZPIĘTOŚĆ TARGETÓW — 10 pkt
    # =========================================================

    target_low = _number(info.get("targetLowPrice"))
    target_high = _number(info.get("targetHighPrice"))

    target_spread_pct = None

    if (
        target_low is not None
        and target_high is not None
        and target_mean is not None
        and target_mean > 0
        and target_high >= target_low
    ):
        target_spread_pct = (
            (target_high - target_low)
            / target_mean
        ) * 100

        if target_spread_pct <= 15:
            points = 10
        elif target_spread_pct <= 30:
            points = 7
        elif target_spread_pct <= 50:
            points = 4
        elif target_spread_pct <= 75:
            points = 2
        else:
            points = 0

        score += points

        _add_reason(
            reasons,
            points,
            f"Rozpiętość targetów: {target_spread_pct:.1f}%"
        )
    else:
        _add_reason(
            reasons,
            0,
            "Brak pełnych danych o targetach"
        )

    # =========================================================
    # FINAL
    # =========================================================

    score = max(0, min(100, int(score)))

    return score, reasons