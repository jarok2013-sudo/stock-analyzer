"""
fundamental_score.py

Fundamental Score 0-100.

Ocena opiera się na:
- wzroście przychodów
- wzroście zysków
- marżach
- ROE
- P/E
- EV/EBITDA
- zadłużeniu
- Free Cash Flow
"""

import math


def _number(value):
    """Zwraca float albo None dla brakującej/niepoprawnej wartości."""
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


def calculate_fundamental_score(analysis):
    """
    Oblicza Fundamental Score w zakresie 0-100.

    Zwraca:
        (score, reasons)
    """

    info = analysis.instrument_info or {}

    score = 0
    reasons = []

    # =========================================================
    # 1. WZROST PRZYCHODÓW — 15 pkt
    # =========================================================

    revenue_growth = _number(info.get("revenueGrowth"))

    if revenue_growth is not None:
        if revenue_growth >= 0.15:
            score += 15
            _add_reason(
                reasons,
                15,
                f"Wysoki wzrost przychodów ({revenue_growth * 100:.1f}%)"
            )
        elif revenue_growth >= 0.08:
            score += 12
            _add_reason(
                reasons,
                12,
                f"Dobry wzrost przychodów ({revenue_growth * 100:.1f}%)"
            )
        elif revenue_growth >= 0.03:
            score += 8
            _add_reason(
                reasons,
                8,
                f"Umiarkowany wzrost przychodów ({revenue_growth * 100:.1f}%)"
            )
        elif revenue_growth >= 0:
            score += 4
            _add_reason(
                reasons,
                4,
                f"Stabilne przychody ({revenue_growth * 100:.1f}%)"
            )
        else:
            _add_reason(
                reasons,
                0,
                f"Spadek przychodów ({revenue_growth * 100:.1f}%)"
            )
    else:
        _add_reason(reasons, 0, "Brak danych o wzroście przychodów")

    # =========================================================
    # 2. WZROST ZYSKÓW — 15 pkt
    # =========================================================

    earnings_growth = _number(info.get("earningsGrowth"))

    if earnings_growth is not None:
        if earnings_growth >= 0.20:
            score += 15
            _add_reason(
                reasons,
                15,
                f"Wysoki wzrost zysków ({earnings_growth * 100:.1f}%)"
            )
        elif earnings_growth >= 0.10:
            score += 12
            _add_reason(
                reasons,
                12,
                f"Dobry wzrost zysków ({earnings_growth * 100:.1f}%)"
            )
        elif earnings_growth >= 0:
            score += 7
            _add_reason(
                reasons,
                7,
                f"Dodatni wzrost zysków ({earnings_growth * 100:.1f}%)"
            )
        else:
            _add_reason(
                reasons,
                0,
                f"Spadek zysków ({earnings_growth * 100:.1f}%)"
            )
    else:
        _add_reason(reasons, 0, "Brak danych o wzroście zysków")

    # =========================================================
    # 3. MARŻE — 15 pkt
    # =========================================================

    gross_margin = _number(info.get("grossMargins"))
    operating_margin = _number(info.get("operatingMargins"))
    profit_margin = _number(info.get("profitMargins"))

    margin_points = 0

    if gross_margin is not None:
        if gross_margin >= 0.50:
            margin_points += 5
        elif gross_margin >= 0.30:
            margin_points += 3
        elif gross_margin >= 0.15:
            margin_points += 1

    if operating_margin is not None:
        if operating_margin >= 0.20:
            margin_points += 5
        elif operating_margin >= 0.10:
            margin_points += 3
        elif operating_margin > 0:
            margin_points += 1

    if profit_margin is not None:
        if profit_margin >= 0.15:
            margin_points += 5
        elif profit_margin >= 0.08:
            margin_points += 3
        elif profit_margin > 0:
            margin_points += 1

    margin_points = min(margin_points, 15)
    score += margin_points

    if margin_points > 0:
        _add_reason(
            reasons,
            margin_points,
            f"Rentowność i marże ({margin_points}/15 pkt)"
        )
    else:
        _add_reason(
            reasons,
            0,
            "Słabe lub brakujące dane o marżach"
        )

    # =========================================================
    # 4. ROE — 10 pkt
    # =========================================================

    roe = _number(info.get("returnOnEquity"))

    if roe is not None:
        if roe >= 0.20:
            score += 10
            _add_reason(reasons, 10, f"Wysoki ROE ({roe * 100:.1f}%)")
        elif roe >= 0.15:
            score += 8
            _add_reason(reasons, 8, f"Dobry ROE ({roe * 100:.1f}%)")
        elif roe >= 0.10:
            score += 5
            _add_reason(reasons, 5, f"Umiarkowany ROE ({roe * 100:.1f}%)")
        elif roe >= 0.05:
            score += 2
            _add_reason(reasons, 2, f"Niski ROE ({roe * 100:.1f}%)")
        else:
            _add_reason(reasons, 0, f"Słaby ROE ({roe * 100:.1f}%)")
    else:
        _add_reason(reasons, 0, "Brak danych ROE")

    # =========================================================
    # 5. P/E — 15 pkt
    # =========================================================

    pe = _number(info.get("trailingPE"))

    if pe is not None and pe > 0:
        if pe <= 12:
            score += 15
            _add_reason(reasons, 15, f"Niskie P/E ({pe:.1f})")
        elif pe <= 18:
            score += 12
            _add_reason(reasons, 12, f"Atrakcyjne P/E ({pe:.1f})")
        elif pe <= 25:
            score += 8
            _add_reason(reasons, 8, f"Umiarkowane P/E ({pe:.1f})")
        elif pe <= 35:
            score += 4
            _add_reason(reasons, 4, f"Podwyższone P/E ({pe:.1f})")
        else:
            _add_reason(reasons, 0, f"Wysokie P/E ({pe:.1f})")
    else:
        _add_reason(reasons, 0, "Brak użytecznego P/E")

    # =========================================================
    # 6. EV / EBITDA — 10 pkt
    # =========================================================

    ev_ebitda = _number(info.get("enterpriseToEbitda"))

    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda <= 8:
            score += 10
            _add_reason(reasons, 10, f"Niskie EV/EBITDA ({ev_ebitda:.1f})")
        elif ev_ebitda <= 12:
            score += 8
            _add_reason(reasons, 8, f"Atrakcyjne EV/EBITDA ({ev_ebitda:.1f})")
        elif ev_ebitda <= 18:
            score += 5
            _add_reason(reasons, 5, f"Umiarkowane EV/EBITDA ({ev_ebitda:.1f})")
        elif ev_ebitda <= 25:
            score += 2
            _add_reason(reasons, 2, f"Podwyższone EV/EBITDA ({ev_ebitda:.1f})")
        else:
            _add_reason(reasons, 0, f"Wysokie EV/EBITDA ({ev_ebitda:.1f})")
    else:
        _add_reason(reasons, 0, "Brak danych EV/EBITDA")

    # =========================================================
    # 7. ZADŁUŻENIE — 10 pkt
    # =========================================================

    debt_to_equity = _number(info.get("debtToEquity"))

    if debt_to_equity is not None and debt_to_equity >= 0:
        if debt_to_equity <= 30:
            score += 10
            _add_reason(
                reasons,
                10,
                f"Niskie zadłużenie D/E ({debt_to_equity:.1f}%)"
            )
        elif debt_to_equity <= 60:
            score += 8
            _add_reason(
                reasons,
                8,
                f"Umiarkowane zadłużenie D/E ({debt_to_equity:.1f}%)"
            )
        elif debt_to_equity <= 100:
            score += 5
            _add_reason(
                reasons,
                5,
                f"Podwyższone D/E ({debt_to_equity:.1f}%)"
            )
        elif debt_to_equity <= 150:
            score += 2
            _add_reason(
                reasons,
                2,
                f"Wysokie D/E ({debt_to_equity:.1f}%)"
            )
        else:
            _add_reason(
                reasons,
                0,
                f"Bardzo wysokie D/E ({debt_to_equity:.1f}%)"
            )
    else:
        _add_reason(reasons, 0, "Brak danych o zadłużeniu")

    # =========================================================
    # 8. FREE CASH FLOW — 10 pkt
    # =========================================================

    free_cashflow = _number(info.get("freeCashflow"))

    if free_cashflow is not None:
        if free_cashflow > 0:
            score += 10
            _add_reason(
                reasons,
                10,
                f"Dodatni Free Cash Flow ({free_cashflow:,.0f})"
            )
        else:
            _add_reason(
                reasons,
                0,
                "Ujemny Free Cash Flow"
            )
    else:
        _add_reason(
            reasons,
            0,
            "Brak danych Free Cash Flow"
        )

    # =========================================================
    # FINAL
    # =========================================================

    score = max(0, min(100, int(score)))

    return score, reasons