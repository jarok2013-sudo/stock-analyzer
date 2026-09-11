"""
ENTRY SCORE
===========

Ocena jakości miejsca wejścia w pozycję: 0-100 pkt.

Składniki:
    R/R              35 pkt
    Proximity        25 pkt
    Trigger          30 pkt
    Volume           10 pkt
    -----------------------
                     100 pkt
"""

import sys
from pathlib import Path

# ============================================================
# IMPORTY
# ============================================================

parent_dir = Path(__file__).resolve().parent.parent

if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils.func import _safe_number
import config


# ============================================================
# POMOCNICZE
# ============================================================

def add_reason(reasons, category, points, text):
    reasons.append({
        "category": category,
        "points": points,
        "text": text,
    })


def _get_touches(level, default=1):
    """Pobiera liczbę testów danego poziomu."""
    if not isinstance(level, dict):
        return default

    raw_touches = level.get("touches")
    if raw_touches is None:
        return default

    try:
        return int(raw_touches)
    except (TypeError, ValueError):
        return default


# ============================================================
# GŁÓWNY ENTRY SCORE
# ============================================================

def calculate_entry_score(analysis):
    """
    Entry Score 0-100.
    Brak prawidłowego R/R dla TP2 powoduje twarde ustawienie Entry Score = 0.
    """
    score = 0
    reasons = []

    scorers = [
        score_entry_rr,
        score_entry_proximity,
        score_entry_trigger,
        score_entry_volume,
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    # ========================================================
    # TWARDY WARUNEK TRADINGOWY
    # ========================================================
    trade_levels = getattr(analysis, "trade_levels", {}) or {}
    rr = _safe_number(trade_levels.get("rr_tp2"))

    if rr is None or rr <= 0:
        final_score = 0
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak prawidłowego R/R dla TP2 — brak wejścia.",
        )
    else:
        final_score = max(0, min(100, int(score)))

    return final_score, reasons


# ============================================================
# 1. RISK / REWARD
# ============================================================

def score_entry_rr(analysis):
    """Maksimum: 35 pkt"""
    score = 0
    reasons = []

    trade_levels = getattr(analysis, "trade_levels", {}) or {}
    rr = _safe_number(trade_levels.get("rr_tp2"))
    min_rr = getattr(config, "MIN_RR", 2.0)
    max_points = getattr(config, "ENTRY_POINTS_RR", 35)

    if rr is None:
        add_reason(reasons, "Risk/Reward", 0, "Brak możliwości wyliczenia R/R.")
        return 0, reasons

    if rr >= 3.0:
        score = max_points
        add_reason(reasons, "Risk/Reward", score, f"Wybitny profil R/R = {rr:.2f}")

    elif rr >= min_rr:
        score = int(max_points * 0.70)
        add_reason(reasons, "Risk/Reward", score, f"Dobre R/R = {rr:.2f}")

    elif rr > 0:
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            f"R/R zbyt niskie ({rr:.2f} < {min_rr:.2f})",
        )

    else:
        add_reason(reasons, "Risk/Reward", 0, "Nieprawidłowy profil R/R.")

    return score, reasons


# ============================================================
# 2. PROXIMITY
# ============================================================

def score_entry_proximity(analysis):
    """
    Maksimum: 25 pkt

    Ocenia odległość ceny od kluczowych poziomów wsparcia.
    Wykorzystuje w pierwszej kolejności wyliczone wcześniej poziomy dynamiczne 
    (nearest_dynamic_support z calculate_dynamic_levels), a w razie ich braku
    przechodzi płynnie na statyczne wsparcia (nearest_support).
    """
    score = 0
    reasons = []

    info = getattr(analysis, "instrument_info", {}) or {}
    currency = info.get("currency", "PLN")

    price = _safe_number(getattr(analysis, "price", None))
    if price is None or price <= 0:
        add_reason(reasons, "Proximity", 0, "Brak aktualnej ceny.")
        return 0, reasons

    # --------------------------------------------------------
    # SELEKCJA WSPARCIA: DYNAMICZNE Z FALLBACKIEM NA STATYCZNE
    # --------------------------------------------------------
    dynamic_supp = getattr(analysis, "nearest_dynamic_support", None)
    dynamic_dist = getattr(analysis, "dynamic_support_distance", None)

    static_supp = getattr(analysis, "nearest_support", None)
    static_dist = getattr(analysis, "support_distance", None)

    active_support = None
    dist_support = None
    is_dynamic = False

    if isinstance(dynamic_supp, dict) and dynamic_dist is not None:
        active_support = dynamic_supp
        dist_support = dynamic_dist
        is_dynamic = True
    elif isinstance(static_supp, dict) and static_dist is not None:
        active_support = static_supp
        dist_support = static_dist
        is_dynamic = False

    ema20 = _safe_number(getattr(analysis, "ema20", None))
    bb_lower = _safe_number(getattr(analysis, "bb_lower", None))
    bb_squeeze = bool(getattr(analysis, "bb_squeeze", False))

    max_dist = getattr(config, "MAX_SUPPORT_DISTANCE", 2.5)
    max_points = getattr(config, "ENTRY_POINTS_SUPPORT", 25)

    # Odległość od EMA20
    dist_ema20 = None
    if ema20 is not None and ema20 > 0:
        dist_ema20 = (abs(price - ema20) / ema20) * 100.0

    # ========================================================
    # EVALUACJA LOKALIZACJI
    # ========================================================
    location_points = 0
    is_retest = False
    is_fresh_breakout = False
    touches = 1

    if active_support is not None and dist_support is not None:
        supp_price = _safe_number(active_support.get("price"))
        source = active_support.get("source", "SUPPORT")
        touches = _get_touches(active_support, default=1)

        # 1. POTWIERDZONY RETEST LUB ŚWIEŻE WYBICIE OPORU (FLIP)
        if source == "RESISTANCE_FLIP":
            retest_confirmed = active_support.get("retest_confirmed", False)

            if 0 <= dist_support <= max_dist:
                if retest_confirmed:
                    location_points = 20
                    is_retest = True
                    add_reason(
                        reasons,
                        "Proximity",
                        location_points,
                        (
                            f"Potwierdzony retest wybitego oporu ({supp_price:.2f} {currency}) "
                            f"— poziom działa jako wsparcie ({dist_support:.2f}% od ceny)."
                        ),
                    )
                else:
                    location_points = 8
                    is_fresh_breakout = True
                    add_reason(
                        reasons,
                        "Proximity",
                        location_points,
                        (
                            f"Świeże wybicie oporu ({supp_price:.2f} {currency}) "
                            f"— brak potwierdzonego retestu (+8 pkt)."
                        ),
                    )

        # 2. STANDARDOWE WSPARCIE (DYNAMICZNE LUB STATYCZNE)
        elif 0 <= dist_support <= max_dist:
            location_points = 20
            label = "dynamicznego " if is_dynamic else ""
            add_reason(
                reasons,
                "Proximity",
                location_points,
                f"Cena blisko {label}wsparcia ({supp_price:.2f} {currency}, {dist_support:.2f}% od ceny).",
            )

    # 3. TEST EMA20 — BLISKO
    if location_points == 0 and dist_ema20 is not None and dist_ema20 <= 2.0:
        location_points = 16
        add_reason(
            reasons,
            "Proximity",
            location_points,
            f"Cena blisko EMA20 (odchylenie {dist_ema20:.2f}%).",
        )

    # 4. TEST EMA20 — UMIARKOWANIE
    if location_points == 0 and dist_ema20 is not None and 2.0 < dist_ema20 <= 4.0:
        location_points = 6
        add_reason(
            reasons,
            "Proximity",
            location_points,
            f"Cena umiarkowanie oddalona od EMA20 ({dist_ema20:.2f}%).",
        )

    # 5. DOLNA BOLLINGER BAND
    if location_points == 0 and bb_lower is not None and price <= bb_lower * 1.01:
        location_points = 14
        add_reason(
            reasons,
            "Proximity",
            location_points,
            f"Test dolnej Bollinger Band ({bb_lower:.2f}).",
        )

    # 6. BRAK DOBREJ LOKALIZACJI
    if location_points == 0:
        rated_resistances = getattr(analysis, "rated_resistances", []) or []
        old_resistances = [
            r for r in rated_resistances
            if isinstance(r, dict) and _safe_number(r.get("price")) is not None and _safe_number(r.get("price")) < price
        ]

        if old_resistances:
            highest_old = max(old_resistances, key=lambda x: _safe_number(x.get("price")))
            old_price = _safe_number(highest_old.get("price"))
            add_reason(
                reasons,
                "Proximity",
                0,
                (
                    f"Cena znajduje się powyżej historycznego oporu "
                    f"({old_price:.2f} {currency}), ale brak potwierdzonego świeżego wybicia/retestu."
                ),
            )
        else:
            add_reason(
                reasons,
                "Proximity",
                0,
                "Cena znajduje się zbyt daleko od dobrego poziomu wejścia.",
            )

    score += location_points

    # ========================================================
    # SIŁA WSPARCIA / RETEST — MAX 2 PKT
    # ========================================================
    strength_points = 0
    strength_msg = None

    if location_points > 0:
        is_near_ath = bool(getattr(analysis, "is_near_ath", False))

        if is_retest:
            strength_points = 2
            strength_msg = f"Potwierdzony retest poziomu wybicia ({touches} testy)"

        elif is_fresh_breakout:
            strength_points = 0

        elif dist_support is not None:
            if is_near_ath and touches <= 2:
                strength_points = 2
                strength_msg = f"Retest poziomu wybicia w rejonie ATH ({touches} testy)"
            elif not is_near_ath and touches >= 4:
                strength_points = 2
                strength_msg = f"Silna strefa wsparcia ({touches} testów)"

    if strength_points > 0:
        score += strength_points
        add_reason(reasons, "Proximity", strength_points, strength_msg)

    # ========================================================
    # BOLLINGER SQUEEZE — MAX 3 PKT
    # ========================================================
    if bb_squeeze:
        squeeze_points = 3
        score += squeeze_points
        add_reason(
            reasons,
            "Proximity",
            squeeze_points,
            "Bollinger Squeeze — spadek zmienności przed możliwym wybiciem.",
        )

    return min(max_points, score), reasons


# ============================================================
# 3. TRIGGER
# ============================================================

def score_entry_trigger(analysis):
    """Maksimum: 30 pkt"""
    score = 0
    reasons = []

    # MACD
    macd = _safe_number(getattr(analysis, "macd", None))
    macd_signal = _safe_number(getattr(analysis, "macd_signal", None))
    prev_macd = _safe_number(getattr(analysis, "prev_macd", None))
    prev_macd_signal = _safe_number(getattr(analysis, "prev_macd_signal", None))
    histogram_rising = bool(getattr(analysis, "histogram_rising", False))

    if macd is None or macd_signal is None:
        add_reason(reasons, "Trigger", 0, "Brak danych MACD.")
    else:
        macd_bullish = macd > macd_signal
        fresh_cross = (
            prev_macd is not None
            and prev_macd_signal is not None
            and prev_macd <= prev_macd_signal
            and macd > macd_signal
        )

        if fresh_cross:
            score += 20
            add_reason(reasons, "Trigger", 20, "Świeże bycze przecięcie MACD.")
        elif macd_bullish and histogram_rising:
            score += 15
            add_reason(reasons, "Trigger", 15, "MACD jest wzrostowy i histogram rośnie.")
        elif macd_bullish:
            score += 8
            add_reason(reasons, "Trigger", 8, "MACD jest powyżej linii sygnałowej.")
        else:
            add_reason(reasons, "Trigger", 0, "Brak byczego sygnału MACD.")

    # Stochastic
    stoch_k = _safe_number(getattr(analysis, "stoch_k", None))
    stoch_d = _safe_number(getattr(analysis, "stoch_d", None))
    prev_stoch_k = _safe_number(getattr(analysis, "prev_stoch_k", None))
    prev_stoch_d = _safe_number(getattr(analysis, "prev_stoch_d", None))

    if all(v is not None for v in [stoch_k, stoch_d, prev_stoch_k, prev_stoch_d]):
        fresh_stoch_cross = prev_stoch_k <= prev_stoch_d and stoch_k > stoch_d

        if fresh_stoch_cross and stoch_k < 30:
            score += 5
            add_reason(
                reasons,
                "Trigger",
                5,
                f"Świeże bycze przecięcie Stochastic w strefie wyprzedania (%K={stoch_k:.1f}).",
            )
        elif stoch_k < 25 and stoch_k > stoch_d:
            score += 3
            add_reason(
                reasons,
                "Trigger",
                3,
                f"Stochastic wychodzi z wyprzedania (%K={stoch_k:.1f}).",
            )
        else:
            add_reason(reasons, "Trigger", 0, "Brak świeżego byczego triggera Stochastic.")
    else:
        add_reason(reasons, "Trigger", 0, "Brak pełnych danych Stochastic.")

    # ADX / DI
    adx = _safe_number(getattr(analysis, "adx", None))
    plus_di = _safe_number(getattr(analysis, "plus_di", None))
    minus_di = _safe_number(getattr(analysis, "minus_di", None))

    if all(v is not None for v in [adx, plus_di, minus_di]):
        if adx >= 20 and plus_di > minus_di:
            score += 5
            add_reason(reasons, "Trigger", 5, f"Potwierdzenie trendu ADX ({adx:.1f}) oraz +DI > -DI.")
        else:
            add_reason(reasons, "Trigger", 0, "Brak potwierdzenia siły trendu ADX/DI.")
    else:
        add_reason(reasons, "Trigger", 0, "Brak pełnych danych ADX/DI.")

    return min(score, 30), reasons


# ============================================================
# 4. VOLUME
# ============================================================

def score_entry_volume(analysis):
    """Maksimum: 10 pkt"""
    score = 0
    reasons = []

    vol_ratio = _safe_number(
        getattr(analysis, "vol_ratio", None),
        default=1.0,
    )
    max_points = getattr(config, "ENTRY_POINTS_VOLUME", 10)

    if vol_ratio >= 1.5:
        score = max_points
        add_reason(reasons, "Volume", score, f"Bardzo mocny wolumen ({vol_ratio:.2f}x średniej).")
    elif vol_ratio >= 1.3:
        score = 7
        add_reason(reasons, "Volume", score, f"Podwyższony wolumen ({vol_ratio:.2f}x średniej).")
    elif vol_ratio >= 1.2:
        score = 5
        add_reason(reasons, "Volume", score, f"Umiarkowanie podwyższony wolumen ({vol_ratio:.2f}x średniej).")
    elif vol_ratio >= 1.1:
        score = 3
        add_reason(reasons, "Volume", score, f"Nieznacznie podwyższony wolumen ({vol_ratio:.2f}x średniej).")
    else:
        add_reason(reasons, "Volume", 0, "Przeciętny lub niski wolumen na wejściu.")

    return score, reasons