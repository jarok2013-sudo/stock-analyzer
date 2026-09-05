"""

Przedział,Kolor,Stan / Sygnał,Co oznacza w practicale?
85 – 100+ pkt,🟢 Zielony,KUPUJ / SPUST POLUZOWANY,"Idealny moment: Świetny R/R (≥2.5-3.0), cena na wsparciu/BB, potwierdzony wolumen i wyzwalacz (MACD/Stoch)."
65 – 84 pkt,🟡 Żółty,OBSERWUJ / GOTOWOŚĆ,"Przyzwoite wejście, ale brakuje wyzwalacza (np. MACD jeszcze nie opadł) lub wolumen jest przeciętny."
45 – 64 pkt,⚪ Szary,NEUTRALNY / SPASUJ,Słaby R/R lub cena zbyt daleko od poziomów obronnych (SL musiałby być zbyt szeroki).
0 – 44 pkt,🔴 Czerwony,ZAKAZ WEJŚCIA,Brak wsparcia pod nogami, fatalny R/R lub kupowanie tuż pod oporem.

do 100
┌─────────────────────────┬─────────┐
│ R/R                     │ 35 pkt  │
├─────────────────────────┼─────────┤
│ Proximity               │ 25 pkt  │
├─────────────────────────┼─────────┤
│ MACD trigger            │ 20 pkt  │
│ Stochastic trigger      │  5 pkt  │
│ ADX/DI confirmation     │  5 pkt  │
├─────────────────────────┼─────────┤
│ Volume                  │ 10 pkt  │
├─────────────────────────┼─────────┤
│ SUMA                    │ 100 pkt │
└─────────────────────────┴─────────┘
"""
import sys
import pandas as pd
from pathlib import Path

# Dodaj katalog nadrzędny do ścieżki importów
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





# ============================================================
# GŁÓWNY ENTRY SCORE
# ============================================================

def calculate_entry_score(analysis):
    """
    Entry Score 0-100.

    Składniki:

        R/R              35 pkt
        Proximity        25 pkt
        Trigger          30 pkt (MACD: 20, Stoch: 5, ADX: 5)
        Volume           10 pkt
        -----------------------
                         100 pkt
    """

    
    score = 0
    reasons = []

    # --------------------------------------------------------
    # POSZCZEGÓLNE KOMPONENTY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TWARDY WARUNEK TRADINGOWY: Brak R/R = Brak pozycji
    # --------------------------------------------------------
    rr = _safe_number(getattr(analysis, "risk_reward", None))
    if rr is None or rr <= 0:
        final_score = 0
    else:
        # --------------------------------------------------------
        # OGRANICZENIE DO 0-100
        # --------------------------------------------------------
        final_score = max(0, min(100, int(score)))

    return final_score, reasons


# ============================================================
# 1. RISK / REWARD
# ============================================================

def score_entry_rr(analysis):
    """
    Maksimum: 35 pkt
    """

    score = 0
    reasons = []

    rr = _safe_number(
        getattr(analysis, "risk_reward", None)
    )

    min_rr = getattr(config, "MIN_RR", 2.0)

    max_points = getattr(
        config,
        "ENTRY_POINTS_RR",
        35,
    )

    if rr is None:
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak możliwości wyliczenia R/R.",
        )
        return 0, reasons

    # --------------------------------------------------------
    # R/R >= 3.0
    # --------------------------------------------------------

    if rr >= 3.0:

        score = max_points

        add_reason(
            reasons,
            "Risk/Reward",
            score,
            f"Wybitny profil R/R = {rr:.2f}",
        )

    # --------------------------------------------------------
    # R/R >= MIN_RR
    # --------------------------------------------------------

    elif rr >= min_rr:

        score = int(max_points * 0.70)

        add_reason(
            reasons,
            "Risk/Reward",
            score,
            f"Dobre R/R = {rr:.2f}",
        )

    # --------------------------------------------------------
    # R/R dodatnie, ale za małe
    # --------------------------------------------------------

    elif rr > 0:

        add_reason(
            reasons,
            "Risk/Reward",
            0,
            (
                f"R/R zbyt niskie "
                f"({rr:.2f} < {min_rr:.2f})"
            ),
        )

    # --------------------------------------------------------
    # R/R <= 0
    # --------------------------------------------------------

    else:

        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Nieprawidłowy profil R/R.",
        )

    return score, reasons


# ============================================================
# 2. PROXIMITY
# ============================================================

def score_entry_proximity(analysis):
    """
    Maksimum: 25 pkt

    Składniki:

        lokalizacja ceny / retest  20 pkt
        siła wsparcia/retest        2 pkt
        Bollinger Squeeze           3 pkt
        ----------------------------
                                   25 pkt

    Priorytet lokalizacji:

        1. retest przełamanego oporu (zamiana ról: opór -> wsparcie)
        2. wsparcie (standardowe)
        3. spadek pod wsparcie (brak obrony / wyłamanie)
        4. EMA20 (do 2%)
        5. EMA20 (2-4%)
        6. dolna Bollinger Band
    """

    score = 0
    reasons = []
    info = getattr(analysis, "instrument_info", {}) or {}
    currency = info.get("currency", "PLN")

    # --------------------------------------------------------
    # Pobranie parametrów ceny i poziomów technicznych
    # --------------------------------------------------------
    price = _safe_number(
        getattr(analysis, "price", None)
    )

    support = getattr(
        analysis,
        "nearest_support",
        None,
    )

    rated_resistances = getattr(
        analysis,
        "rated_resistances",
        [],
    )

    rated_supports = getattr(
        analysis,
        "rated_supports",
        [],
    )

    ema20 = _safe_number(
        getattr(analysis, "ema20", None)
    )

    bb_lower = _safe_number(
        getattr(analysis, "bb_lower", None)
    )

    bb_squeeze = bool(
        getattr(
            analysis,
            "bb_squeeze",
            False,
        )
    )

    max_dist = getattr(
        config,
        "MAX_SUPPORT_DISTANCE",
        2.5,
    )

    max_points = getattr(
        config,
        "ENTRY_POINTS_SUPPORT",
        25,
    )

    # --------------------------------------------------------
    # Bezpieczna cena
    # --------------------------------------------------------
    if price is None or price <= 0:
        add_reason(
            reasons,
            "Proximity",
            0,
            "Brak aktualnej ceny.",
        )
        return 0, reasons

    # --------------------------------------------------------
    # Odległość od wsparcia
    # --------------------------------------------------------
    dist_support = None
    touches = 1

    if isinstance(support, dict):
        support_price = _safe_number(
            support.get("price")
        )

        if (
            support_price is not None
            and support_price > 0
        ):
            # dodatnie = cena NAD wsparciem
            # ujemne = cena POD wsparciem
            dist_support = (
                (price - support_price)
                / price
            ) * 100

            # NIE ZMIENIAMY NAZWY "touches"
            raw_touches = support.get("touches")

            if raw_touches is not None:
                try:
                    touches = int(raw_touches)
                except (TypeError, ValueError):
                    touches = 1

    # --------------------------------------------------------
    # Odległość od EMA20
    # --------------------------------------------------------
    dist_ema20 = None

    if ema20 is not None and ema20 > 0:
        dist_ema20 = (
            abs(price - ema20)
            / ema20
        ) * 100

    # --------------------------------------------------------
    # Wykrywanie przełamanych poziomów (Zasada Zamiany Ról)
    # --------------------------------------------------------
    # Szukamy oporów pod ceną (przebite opory stające się wsparciem)
    broken_resistances = [
        r for r in rated_resistances
        if isinstance(r, dict) and _safe_number(r.get("price")) is not None and _safe_number(r.get("price")) < price
    ]

    # Szukamy wsparć nad ceną (przełamane wsparcia stające się oporem)
    broken_supports = [
        s for s in rated_supports
        if isinstance(s, dict) and _safe_number(s.get("price")) is not None and _safe_number(s.get("price")) > price
    ]

    # ========================================================
    # LOKALIZACJA CENY — MAX 20 PKT
    # ========================================================
    location_points = 0
    is_retest = False

    # --------------------------------------------------------
    # 1. RETEST PRZEBITEGO OPORU (Zasada zamiany ról)
    # --------------------------------------------------------
    if broken_resistances:
        last_broken_res = max(
            broken_resistances,
            key=lambda x: _safe_number(x.get("price"))
        )
        broken_res_price = _safe_number(last_broken_res.get("price"))
        dist_broken_res = ((price - broken_res_price) / price) * 100.0

        if 0 <= dist_broken_res <= max_dist:
            location_points = 20
            is_retest = True
            add_reason(
                reasons,
                "Proximity",
                location_points,
                (
                    f"Retest wybitego oporu ({broken_res_price:.2f} {currency}) — "
                    f"dawny opór stał się wsparciem (+{dist_broken_res:.2f}%)"
                ),
            )

    # --------------------------------------------------------
    # 2. WSPARCIE (STANDARDOWE)
    # --------------------------------------------------------
    elif (
        dist_support is not None
        and 0 <= dist_support <= max_dist
    ):
        location_points = 20
        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena blisko wsparcia "
                f"({dist_support:.2f}%)"
            ),
        )

    # --------------------------------------------------------
    # 3. SPADEK PONIŻEJ WSPARCIA (WYŁAMANIE DÓŁ)
    # --------------------------------------------------------
    elif (
        broken_supports
        and dist_support is None
    ):
        last_broken_supp = min(
            broken_supports,
            key=lambda x: _safe_number(x.get("price"))
        )
        broken_supp_price = _safe_number(last_broken_supp.get("price"))
        dist_below = ((broken_supp_price - price) / price) * 100.0

        if dist_below <= 3.0:
            location_points = 0
            add_reason(
                reasons,
                "Proximity",
                0,
                (
                    f"Cena wyłamała wsparcie w dół ({broken_supp_price:.2f} {currency}) — "
                    f"brak obrony (-{dist_below:.2f}%)"
                ),
            )

    # --------------------------------------------------------
    # 4. EMA20 (BLISKO DO 2%)
    # --------------------------------------------------------
    elif (
        dist_ema20 is not None
        and dist_ema20 <= 2.0
    ):
        location_points = 16
        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena blisko EMA20 "
                f"(odchylenie {dist_ema20:.2f}%)"
            ),
        )

    # --------------------------------------------------------
    # 5. EMA20 (UMIARKOWANIE 2-4%)
    # --------------------------------------------------------
    elif (
        dist_ema20 is not None
        and 2.0 < dist_ema20 <= 4.0
    ):
        location_points = 6
        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena umiarkowanie oddalona "
                f"od EMA20 ({dist_ema20:.2f}%)"
            ),
        )

    # --------------------------------------------------------
    # 6. DOLNA BOLLINGER BAND
    # --------------------------------------------------------
    elif (
        bb_lower is not None
        and price <= bb_lower * 1.01
    ):
        location_points = 14
        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Test dolnej Bollinger Band "
                f"({bb_lower:.2f})"
            ),
        )

    # --------------------------------------------------------
    # 7. BRAK DOBREJ LOKALIZACJI
    # --------------------------------------------------------
    else:
        add_reason(
            reasons,
            "Proximity",
            0,
            (
                "Cena znajduje się zbyt daleko "
                "od dobrego poziomu wejścia."
            ),
        )

    score += location_points

    # ========================================================
    # SIŁA WSPARCIA / RETEST — MAX 2 PKT
    # ========================================================
    strength_points = 0
    strength_msg = None

    # Punkty przyznajemy TYLKO wtedy, gdy cena jest w prawidłowej lokalizacji wejściowej
    if location_points > 0:
        is_near_ath = bool(getattr(analysis, "is_near_ath", False))

        # 1. Przypadek retestu wybitego oporu
        if is_retest:
            last_broken_res = max(
                broken_resistances,
                key=lambda x: _safe_number(x.get("price"))
            )
            res_touches = last_broken_res.get("touches", touches)
            try:
                res_touches = int(res_touches)
            except (TypeError, ValueError):
                res_touches = 1

            strength_points = 2
            strength_msg = f"Retest poziomu wybicia ({res_touches} testy)"

        # 2. Przypadek standardowego wsparcia
        elif dist_support is not None:
            if is_near_ath and touches <= 2:
                strength_points = 2
                strength_msg = f"Retest poziomu wybicia w rejonie ATH ({touches} testy)"
            elif not is_near_ath and touches >= 4:
                strength_points = 2
                strength_msg = f"Silna strefa wsparcia ({touches} testów)"

    if strength_points > 0:
        score += strength_points
        add_reason(
            reasons,
            "Proximity",
            strength_points,
            strength_msg,
        )

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
            (
                "Bollinger Squeeze - "
                "spadek zmienności przed możliwym wybiciem."
            ),
        )

    # ========================================================
    # OGRANICZENIE PROXIMITY DO 25 PKT
    # ========================================================
    return min(max_points, score), reasons


# ============================================================
# 3. TRIGGER
# ============================================================

def score_entry_trigger(analysis):
    """
    Maksimum: 30 pkt

    MACD:
        20 pkt

    Stochastic:
         5 pkt

    ADX/DI confirmation:
         5 pkt
    """

    score = 0
    reasons = []

    # ========================================================
    # MACD
    # ========================================================

    macd = _safe_number(
        getattr(analysis, "macd", None)
    )

    macd_signal = _safe_number(
        getattr(
            analysis,
            "macd_signal",
            None,
        )
    )

    prev_macd = _safe_number(
        getattr(
            analysis,
            "prev_macd",
            None,
        )
    )

    prev_macd_signal = _safe_number(
        getattr(
            analysis,
            "prev_macd_signal",
            None,
        )
    )

    histogram_rising = bool(
        getattr(
            analysis,
            "histogram_rising",
            False,
        )
    )

    macd_points = 20

    # Brak danych
    if macd is None or macd_signal is None:

        add_reason(
            reasons,
            "Trigger",
            0,
            "Brak danych MACD.",
        )

    else:

        macd_bullish = macd > macd_signal

        # ----------------------------------------------------
        # ŚWIEŻE PRZECIĘCIE MACD
        # ----------------------------------------------------

        fresh_cross = (
            prev_macd is not None
            and prev_macd_signal is not None
            and prev_macd <= prev_macd_signal
            and macd > macd_signal
        )

        if fresh_cross:

            score += macd_points

            add_reason(
                reasons,
                "Trigger",
                macd_points,
                "Świeże bycze przecięcie MACD.",
            )

        # ----------------------------------------------------
        # MACD bullish + histogram rośnie
        # ----------------------------------------------------

        elif macd_bullish and histogram_rising:

            points = 15

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                "MACD jest wzrostowy i histogram rośnie.",
            )

        # ----------------------------------------------------
        # MACD bullish
        # ----------------------------------------------------

        elif macd_bullish:

            points = 8

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                "MACD jest powyżej linii sygnałowej.",
            )

        # ----------------------------------------------------
        # MACD bearish
        # ----------------------------------------------------

        else:

            add_reason(
                reasons,
                "Trigger",
                0,
                "Brak byczego sygnału MACD.",
            )

    # ========================================================
    # STOCHASTIC
    # ========================================================

    stoch_k = _safe_number(
        getattr(
            analysis,
            "stoch_k",
            None,
        )
    )

    stoch_d = _safe_number(
        getattr(
            analysis,
            "stoch_d",
            None,
        )
    )

    prev_stoch_k = _safe_number(
        getattr(
            analysis,
            "prev_stoch_k",
            None,
        )
    )

    prev_stoch_d = _safe_number(
        getattr(
            analysis,
            "prev_stoch_d",
            None,
        )
    )

    # ========================================================
    # ŚWIEŻE PRZECIĘCIE W STREFIE WYPRZEDANIA
    # ========================================================

    if (
        stoch_k is not None
        and stoch_d is not None
        and prev_stoch_k is not None
        and prev_stoch_d is not None
    ):

        fresh_stoch_cross = (
            prev_stoch_k <= prev_stoch_d
            and stoch_k > stoch_d
        )

        if fresh_stoch_cross and stoch_k < 30:

            points = 5

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                (
                    "Świeże bycze przecięcie "
                    f"Stochastic w strefie wyprzedania "
                    f"(%K={stoch_k:.1f})"
                ),
            )

        elif (
            stoch_k < 25
            and stoch_k > stoch_d
        ):

            points = 3

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                (
                    "Stochastic wychodzi "
                    f"z wyprzedania (%K={stoch_k:.1f})"
                ),
            )

        else:

            add_reason(
                reasons,
                "Trigger",
                0,
                "Brak świeżego byczego triggera Stochastic.",
            )

    else:

        add_reason(
            reasons,
            "Trigger",
            0,
            "Brak pełnych danych Stochastic.",
        )

    # ========================================================
    # ADX / DI CONFIRMATION
    # ========================================================

    adx = _safe_number(getattr(analysis, "adx", None))
    plus_di = _safe_number(getattr(analysis, "plus_di", None))
    minus_di = _safe_number(getattr(analysis, "minus_di", None))

    if adx is not None and plus_di is not None and minus_di is not None:
        if adx >= 20 and plus_di > minus_di:
            adx_pts = 5
            score += adx_pts
            add_reason(
                reasons,
                "Trigger",
                adx_pts,
                f"Potwierdzenie trendu ADX ({adx:.1f}) oraz +DI > -DI.",
            )
        else:
            add_reason(
                reasons,
                "Trigger",
                0,
                "Brak potwierdzenia siły trendu ADX/DI.",
            )

    # ========================================================
    # OGRANICZENIE TRIGGERA (MAX 30)
    # ========================================================

    score = min(score, 30)

    return score, reasons


# ============================================================
# 4. VOLUME
# ============================================================

def score_entry_volume(analysis):
    """
    Maksimum: 10 pkt
    """

    score = 0
    reasons = []

    vol_ratio = _safe_number(
        getattr(
            analysis,
            "vol_ratio",
            None,
        ),
        default=1.0,
    )

    max_points = getattr(
        config,
        "ENTRY_POINTS_VOLUME",
        10,
    )

    # ========================================================
    # BARDZO MOCNY WOLUMEN
    # ========================================================

    if vol_ratio >= 1.5:

        score = max_points

        add_reason(
            reasons,
            "Volume",
            score,
            (
                f"Bardzo mocny wolumen "
                f"({vol_ratio:.2f}x średniej)"
            ),
        )

    # ========================================================
    # DOBRY WOLUMEN
    # ========================================================

    elif vol_ratio >= 1.3:

        score = 7

        add_reason(
            reasons,
            "Volume",
            score,
            (
                f"Podwyższony wolumen "
                f"({vol_ratio:.2f}x średniej)"
            ),
        )

    # ========================================================
    # UMIARKOWANY
    # ========================================================

    elif vol_ratio >= 1.2:

        score = 5

        add_reason(
            reasons,
            "Volume",
            score,
            (
                f"Umiarkowanie podwyższony wolumen "
                f"({vol_ratio:.2f}x średniej)"
            ),
        )

    # ========================================================
    # LEKKO PODWYŻSZONY
    # ========================================================

    elif vol_ratio >= 1.1:

        score = 3

        add_reason(
            reasons,
            "Volume",
            score,
            (
                f"Nieznacznie podwyższony wolumen "
                f"({vol_ratio:.2f}x średniej)"
            ),
        )

    # ========================================================
    # NORMALNY / NISKI
    # ========================================================

    else:

        add_reason(
            reasons,
            "Volume",
            0,
            "Przeciętny lub niski wolumen na wejściu.",
        )

    return score, reasons