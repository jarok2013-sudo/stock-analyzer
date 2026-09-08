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

PROXIMITY:
    - potwierdzony retest wybitego oporu -> 20 pkt
    - świeże wybicie oporu bez retestu   -> 8 pkt
    - standardowe wsparcie               -> 20 pkt
    - wybicie wsparcia w dół             -> 0 pkt
    - EMA20 blisko                       -> 16 pkt
    - EMA20 umiarkowanie                 -> 6 pkt
    - dolna Bollinger Band               -> 14 pkt
    - siła wsparcia / retestu            -> 2 pkt
    - Bollinger Squeeze                  -> 3 pkt

WAŻNE:
    Sam fakt, że opór znajduje się poniżej ceny,
    NIE oznacza automatycznie wybicia ani retestu.

    Aby uznać opór za wybity:
        poprzednie Close <= opór
        obecne Close > opór

    Aby uznać ruch za retest:
        breakout musi nastąpić wcześniej,
        a następna / kolejna świeca musi wrócić
        w okolice poziomu i zamknąć się ponownie
        powyżej niego.

    Analogiczna zasada obowiązuje dla wybicia wsparcia
    w dół.
"""

import sys
from pathlib import Path

import pandas as pd


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


def _get_df(analysis):
    """
    Zwraca DataFrame z danymi OHLC.

    Obsługuje brak danych bez rzucania wyjątku.
    """
    df = getattr(analysis, "df", None)

    if df is None:
        return None

    if not isinstance(df, pd.DataFrame):
        return None

    if df.empty:
        return None

    return df


def _get_level_price(level):
    """
    Bezpiecznie pobiera cenę poziomu technicznego.
    """
    if not isinstance(level, dict):
        return None

    return _safe_number(level.get("price"))


def _levels_below_price(levels, price):
    """
    Zwraca poziomy znajdujące się poniżej aktualnej ceny.

    UWAGA:
    To tylko klasyfikacja geometryczna.

    Nie oznacza jeszcze, że poziom został rzeczywiście
    wybity w ostatnim czasie.
    """
    result = []

    if price is None:
        return result

    for level in levels or []:
        level_price = _get_level_price(level)

        if (
            level_price is not None
            and level_price < price
        ):
            result.append(level)

    return result


def _levels_above_price(levels, price):
    """
    Zwraca poziomy znajdujące się powyżej aktualnej ceny.
    """
    result = []

    if price is None:
        return result

    for level in levels or []:
        level_price = _get_level_price(level)

        if (
            level_price is not None
            and level_price > price
        ):
            result.append(level)

    return result


def _find_recent_breakout(
    df,
    level_price,
    direction="up",
    lookback=8,
):
    """
    Sprawdza, czy w ostatnich świecach nastąpiło rzeczywiste
    wybicie poziomu przez cenę zamknięcia.

    direction="up":
        Close poprzedniej świecy <= poziom
        Close bieżącej świecy  > poziom

    direction="down":
        Close poprzedniej świecy >= poziom
        Close bieżącej świecy  < poziom

    Zwraca:
        pozycję breakout candle w wyciętym DataFrame
        albo None.
    """

    if (
        df is None
        or df.empty
        or level_price is None
    ):
        return None

    if "close" not in df.columns:
        return None

    try:
        recent = df.tail(lookback + 1).copy()

        if len(recent) < 2:
            return None

        closes = pd.to_numeric(
            recent["close"],
            errors="coerce",
        )

        for i in range(1, len(closes)):

            previous_close = closes.iloc[i - 1]
            current_close = closes.iloc[i]

            if (
                pd.isna(previous_close)
                or pd.isna(current_close)
            ):
                continue

            if direction == "up":

                if (
                    previous_close <= level_price
                    and current_close > level_price
                ):
                    return i

            elif direction == "down":

                if (
                    previous_close >= level_price
                    and current_close < level_price
                ):
                    return i

    except Exception:
        return None

    return None


def _has_recent_retest_after_breakout(
    df,
    level_price,
    breakout_position,
    direction="up",
    tolerance_pct=0.5,
):
    """
    Sprawdza, czy po rzeczywistym wybiciu nastąpił retest poziomu.

    Dla wybicia górą:

        breakout:
            Close przechodzi nad poziom

        retest:
            Low wraca w okolice poziomu
            oraz Close pozostaje nad poziomem.

    Dla wybicia dołem:

        breakout:
            Close przechodzi pod poziom

        retest:
            High wraca w okolice poziomu
            oraz Close pozostaje pod poziomem.

    WAŻNE:
        Retest musi nastąpić PO świecy breakout.

        Dzięki temu świeca wybicia nie zostanie błędnie
        uznana za retest.
    """

    if (
        df is None
        or df.empty
        or level_price is None
        or breakout_position is None
    ):
        return False

    required_columns = {
        "high",
        "low",
        "close",
    }

    if not required_columns.issubset(df.columns):
        return False

    try:
        recent = df.tail(
            max(len(df), breakout_position + 2)
        ).copy()

        # breakout_position odnosi się do ostatniego
        # wycinka użytego przez _find_recent_breakout().
        #
        # Dlatego ponownie pobieramy ten sam zakres.
        lookback = max(
            8,
            breakout_position + 2,
        )

        recent = df.tail(lookback + 1).copy()

        if len(recent) <= breakout_position + 1:
            return False

        tolerance = level_price * (
            tolerance_pct / 100.0
        )

        lower_bound = level_price - tolerance
        upper_bound = level_price + tolerance

        for i in range(
            breakout_position + 1,
            len(recent),
        ):
            row = recent.iloc[i]

            high = _safe_number(row.get("high"))
            low = _safe_number(row.get("low"))
            close = _safe_number(row.get("close"))

            if (
                high is None
                or low is None
                or close is None
            ):
                continue

            if direction == "up":

                touched_level = (
                    low <= upper_bound
                    and high >= lower_bound
                )

                held_above = (
                    close > level_price
                )

                if touched_level and held_above:
                    return True

            elif direction == "down":

                touched_level = (
                    high >= lower_bound
                    and low <= upper_bound
                )

                held_below = (
                    close < level_price
                )

                if touched_level and held_below:
                    return True

    except Exception:
        return False

    return False


def _recent_breakout_and_retest(
    analysis,
    level_price,
    direction="up",
    lookback=8,
    tolerance_pct=1.0,
):
    """
    Wspólny wrapper:

        1. szuka świeżego wybicia,
        2. szuka retestu po wybiciu.

    Zwraca:

        {
            "breakout": bool,
            "retest": bool,
        }
    """

    df = _get_df(analysis)

    result = {
        "breakout": False,
        "retest": False,
    }

    if (
        df is None
        or level_price is None
    ):
        return result

    breakout_position = _find_recent_breakout(
        df=df,
        level_price=level_price,
        direction=direction,
        lookback=lookback,
    )

    if breakout_position is None:
        return result

    result["breakout"] = True

    result["retest"] = _has_recent_retest_after_breakout(
        df=df,
        level_price=level_price,
        breakout_position=breakout_position,
        direction=direction,
        tolerance_pct=tolerance_pct,
    )

    return result


def _get_touches(level, default=1):
    """
    Pobiera touches bez zmiany nazwy pola.

    WAŻNE:
        używamy dokładnie "touches".
    """

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

    Składniki:

        R/R              35 pkt
        Proximity        25 pkt
        Trigger          30 pkt
        Volume           10 pkt
        -----------------------
                         100 pkt

    Brak prawidłowego R/R dla TP2
    powoduje twarde ustawienie Entry Score = 0.
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
    # Brak prawidłowego R/R = brak wejścia.
    # ========================================================

    trade_levels = getattr(
        analysis,
        "trade_levels",
        {},
    ) or {}

    rr = _safe_number(
        trade_levels.get("rr_tp2")
    )

    if rr is None or rr <= 0:

        final_score = 0

        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak prawidłowego R/R dla TP2 — brak wejścia.",
        )

    else:

        final_score = max(
            0,
            min(
                100,
                int(score),
            ),
        )

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

    trade_levels = getattr(
        analysis,
        "trade_levels",
        {},
    ) or {}

    rr = _safe_number(
        trade_levels.get("rr_tp2")
    )

    min_rr = getattr(
        config,
        "MIN_RR",
        2.0,
    )

    max_points = getattr(
        config,
        "ENTRY_POINTS_RR",
        35,
    )

    # ========================================================
    # Brak R/R
    # ========================================================

    if rr is None:

        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak możliwości wyliczenia R/R.",
        )

        return 0, reasons

    # ========================================================
    # R/R >= 3
    # ========================================================

    if rr >= 3.0:

        score = max_points

        add_reason(
            reasons,
            "Risk/Reward",
            score,
            f"Wybitny profil R/R = {rr:.2f}",
        )

    # ========================================================
    # R/R >= MIN_RR
    # ========================================================

    elif rr >= min_rr:

        score = int(
            max_points * 0.70
        )

        add_reason(
            reasons,
            "Risk/Reward",
            score,
            f"Dobre R/R = {rr:.2f}",
        )

    # ========================================================
    # R/R dodatnie, ale za małe
    # ========================================================

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

    # ========================================================
    # R/R <= 0
    # ========================================================

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

        lokalizacja / retest       20 pkt
        siła wsparcia / retestu     2 pkt
        Bollinger Squeeze           3 pkt
        ----------------------------
                                  25 pkt

    PRIORYTET:

        1. POTWIERDZONY retest wybitego oporu
        2. świeże wybicie oporu bez retestu
        3. standardowe wsparcie
        4. wybicie wsparcia w dół
        5. EMA20 <= 2%
        6. EMA20 2-4%
        7. dolna Bollinger Band

    NAJWAŻNIEJSZA ZASADA:

        Opór poniżej ceny != automatycznie wybity opór.

        Aby dostać punkty za retest, potrzebujemy
        potwierdzenia w danych OHLC.
    """

    score = 0
    reasons = []

    info = getattr(
        analysis,
        "instrument_info",
        {},
    ) or {}

    currency = info.get(
        "currency",
        "PLN",
    )

    # ========================================================
    # Dane podstawowe
    # ========================================================

    price = _safe_number(
        getattr(
            analysis,
            "price",
            None,
        )
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
    ) or []

    rated_supports = getattr(
        analysis,
        "rated_supports",
        [],
    ) or []

    ema20 = _safe_number(
        getattr(
            analysis,
            "ema20",
            None,
        )
    )

    bb_lower = _safe_number(
        getattr(
            analysis,
            "bb_lower",
            None,
        )
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

    # ========================================================
    # Bezpieczna cena
    # ========================================================

    if price is None or price <= 0:

        add_reason(
            reasons,
            "Proximity",
            0,
            "Brak aktualnej ceny.",
        )

        return 0, reasons

    # ========================================================
    # ODLEGŁOŚĆ OD NAJBLIŻSZEGO WSPARCIA
    # ========================================================

    dist_support = None
    touches = 1

    if isinstance(support, dict):

        support_price = _get_level_price(
            support
        )

        if (
            support_price is not None
            and support_price > 0
        ):

            # dodatnie = cena NAD wsparciem
            # ujemne   = cena POD wsparciem

            dist_support = (
                (price - support_price)
                / price
            ) * 100.0

            # ==================================================
            # NIE ZMIENIAMY "touches"
            # ==================================================

            touches = _get_touches(
                support,
                default=1,
            )

    # ========================================================
    # ODLEGŁOŚĆ OD EMA20
    # ========================================================

    dist_ema20 = None

    if (
        ema20 is not None
        and ema20 > 0
    ):

        dist_ema20 = (
            abs(price - ema20)
            / ema20
        ) * 100.0

    # ========================================================
    # KLASYFIKACJA POZIOMÓW
    # ========================================================

    # --------------------------------------------------------
    # WAŻNE:
    #
    # broken_resistances oznacza tylko:
    # "historyczny opór znajduje się poniżej ceny".
    #
    # NIE oznacza:
    # "ten opór został niedawno wybity".
    # --------------------------------------------------------

    broken_resistances = (
        _levels_below_price(
            rated_resistances,
            price,
        )
    )

    broken_supports = (
        _levels_above_price(
            rated_supports,
            price,
        )
    )

    # ========================================================
    # ZMIENNE STANU
    # ========================================================

    location_points = 0

    is_retest = False
    is_fresh_breakout = False

    selected_broken_resistance = None
    selected_broken_support = None

    # ========================================================
    # 1. POTWIERDZONY RETEST WYBITEGO OPORU
    # ========================================================
    #
    # NIE wystarczy:
    #
    #     resistance < price
    #
    # Musi wystąpić:
    #
    #     Close <= resistance
    #     następnie Close > resistance
    #     następnie powrót w okolice resistance
    #     oraz Close > resistance
    #
    # ========================================================

    confirmed_retests = []

    for resistance in broken_resistances:

        resistance_price = _get_level_price(
            resistance
        )

        if resistance_price is None:
            continue

        breakout_state = (
            _recent_breakout_and_retest(
                analysis=analysis,
                level_price=resistance_price,
                direction="up",
                lookback=8,
                tolerance_pct=1.0,
            )
        )

        if breakout_state["retest"]:

            confirmed_retests.append(
                resistance
            )

    if confirmed_retests:

        # Najwyższy potwierdzony poziom
        # znajdujący się poniżej ceny.
        selected_broken_resistance = max(
            confirmed_retests,
            key=lambda x: (
                _get_level_price(x)
                or 0
            ),
        )

        broken_res_price = _get_level_price(
            selected_broken_resistance
        )

        dist_broken_res = (
            (price - broken_res_price)
            / price
        ) * 100.0

        if (
            0 <= dist_broken_res <= max_dist
        ):

            location_points = 20
            is_retest = True

            add_reason(
                reasons,
                "Proximity",
                location_points,
                (
                    f"Potwierdzony retest wybitego "
                    f"oporu ({broken_res_price:.2f} "
                    f"{currency}) — poziom działa "
                    f"jako wsparcie "
                    f"({dist_broken_res:.2f}% od ceny)."
                ),
            )

    # ========================================================
    # 2. ŚWIEŻE WYBICIE OPORU — BEZ RETESTU
    # ========================================================
    #
    # Jeżeli mamy potwierdzone wybicie, ale jeszcze nie ma
    # retestu, dajemy tylko ograniczoną liczbę punktów.
    #
    # Nie chcemy udawać, że cena jest już na wsparciu.
    # ========================================================

    if location_points == 0:

        fresh_breakouts = []

        for resistance in broken_resistances:

            resistance_price = _get_level_price(
                resistance
            )

            if resistance_price is None:
                continue

            breakout_state = (
                _recent_breakout_and_retest(
                    analysis=analysis,
                    level_price=resistance_price,
                    direction="up",
                    lookback=8,
                    tolerance_pct=1.0,
                )
            )

            if breakout_state["breakout"]:

                fresh_breakouts.append(
                    resistance
                )

        if fresh_breakouts:

            selected_broken_resistance = max(
                fresh_breakouts,
                key=lambda x: (
                    _get_level_price(x)
                    or 0
                ),
            )

            broken_res_price = _get_level_price(
                selected_broken_resistance
            )

            dist_broken_res = (
                (price - broken_res_price)
                / price
            ) * 100.0

            if (
                0 <= dist_broken_res <= max_dist
            ):

                location_points = 8
                is_fresh_breakout = True

                add_reason(
                    reasons,
                    "Proximity",
                    location_points,
                    (
                        f"Świeże wybicie oporu "
                        f"({broken_res_price:.2f} "
                        f"{currency}) — brak potwierdzonego "
                        f"retestu (+8 pkt)."
                    ),
                )

    # ========================================================
    # 3. STANDARDOWE WSPARCIE
    # ========================================================

    if (
        location_points == 0
        and dist_support is not None
        and 0 <= dist_support <= max_dist
    ):

        location_points = 20

        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena blisko wsparcia "
                f"({dist_support:.2f}%)."
            ),
        )

    # ========================================================
    # 4. WYŁAMANIE WSPARCIA W DÓŁ
    # ========================================================
    #
    # Tutaj również nie uznajemy samego:
    #
    #     support > price
    #
    # za dowód świeżego wybicia.
    #
    # Szukamy rzeczywistego zamknięcia poniżej poziomu.
    # ========================================================

    if location_points == 0:

        recent_support_breaks = []

        for support_level in broken_supports:

            support_level_price = _get_level_price(
                support_level
            )

            if support_level_price is None:
                continue

            breakout_state = (
                _recent_breakout_and_retest(
                    analysis=analysis,
                    level_price=support_level_price,
                    direction="down",
                    lookback=8,
                    tolerance_pct=1.0,
                )
            )

            if breakout_state["breakout"]:

                recent_support_breaks.append(
                    support_level
                )

        if recent_support_breaks:

            selected_broken_support = min(
                recent_support_breaks,
                key=lambda x: (
                    _get_level_price(x)
                    or float("inf")
                ),
            )

            broken_supp_price = _get_level_price(
                selected_broken_support
            )

            dist_below = (
                (broken_supp_price - price)
                / price
            ) * 100.0

            if (
                dist_below >= 0
                and dist_below <= 3.0
            ):

                location_points = 0

                add_reason(
                    reasons,
                    "Proximity",
                    0,
                    (
                        f"Cena świeżo wyłamała "
                        f"wsparcie w dół "
                        f"({broken_supp_price:.2f} "
                        f"{currency}) — brak obrony."
                    ),
                )

    # ========================================================
    # 5. EMA20 — BLISKO
    # ========================================================

    if (
        location_points == 0
        and dist_ema20 is not None
        and dist_ema20 <= 2.0
    ):

        location_points = 16

        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena blisko EMA20 "
                f"(odchylenie {dist_ema20:.2f}%)."
            ),
        )

    # ========================================================
    # 6. EMA20 — UMIARKOWANIE
    # ========================================================

    if (
        location_points == 0
        and dist_ema20 is not None
        and 2.0 < dist_ema20 <= 4.0
    ):

        location_points = 6

        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Cena umiarkowanie oddalona "
                f"od EMA20 "
                f"({dist_ema20:.2f}%)."
            ),
        )

    # ========================================================
    # 7. DOLNA BOLLINGER BAND
    # ========================================================

    if (
        location_points == 0
        and bb_lower is not None
        and price <= bb_lower * 1.01
    ):

        location_points = 14

        add_reason(
            reasons,
            "Proximity",
            location_points,
            (
                f"Test dolnej Bollinger Band "
                f"({bb_lower:.2f})."
            ),
        )

    # ========================================================
    # 8. BRAK DOBREJ LOKALIZACJI
    # ========================================================

    if location_points == 0:

        # Jeżeli mamy stary opór poniżej ceny,
        # ale nie ma potwierdzonego świeżego wybicia,
        # mówimy to wprost.
        #
        # To jest ważne diagnostycznie.

        if broken_resistances:

            highest_old_resistance = max(
                broken_resistances,
                key=lambda x: (
                    _get_level_price(x)
                    or 0
                ),
            )

            old_res_price = _get_level_price(
                highest_old_resistance
            )

            add_reason(
                reasons,
                "Proximity",
                0,
                (
                    f"Cena znajduje się powyżej "
                    f"historycznego oporu "
                    f"({old_res_price:.2f} {currency}), "
                    f"ale brak potwierdzonego świeżego "
                    f"wybicia/retestu."
                ),
            )

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

    if location_points > 0:

        is_near_ath = bool(
            getattr(
                analysis,
                "is_near_ath",
                False,
            )
        )

        # ====================================================
        # POTWIERDZONY RETEST
        # ====================================================

        if is_retest and selected_broken_resistance:

            res_touches = _get_touches(
                selected_broken_resistance,
                default=touches,
            )

            strength_points = 2

            strength_msg = (
                f"Potwierdzony retest poziomu wybicia "
                f"({res_touches} testy)"
            )

        # ====================================================
        # ŚWIEŻE WYBICIE BEZ RETESTU
        # ====================================================

        elif is_fresh_breakout:

            # Nie dajemy +2 za retest,
            # bo retestu jeszcze nie było.

            strength_points = 0

        # ====================================================
        # STANDARDOWE WSPARCIE
        # ====================================================

        elif dist_support is not None:

            if (
                is_near_ath
                and touches <= 2
            ):

                strength_points = 2

                strength_msg = (
                    "Retest poziomu wybicia "
                    f"w rejonie ATH "
                    f"({touches} testy)"
                )

            elif (
                not is_near_ath
                and touches >= 4
            ):

                strength_points = 2

                strength_msg = (
                    f"Silna strefa wsparcia "
                    f"({touches} testów)"
                )

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
                "Bollinger Squeeze — "
                "spadek zmienności przed możliwym "
                "wybiciem."
            ),
        )

    # ========================================================
    # OGRANICZENIE PROXIMITY
    # ========================================================

    return min(
        max_points,
        score,
    ), reasons


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

    ADX/DI:
         5 pkt
    """

    score = 0
    reasons = []

    # ========================================================
    # MACD
    # ========================================================

    macd = _safe_number(
        getattr(
            analysis,
            "macd",
            None,
        )
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

    # ========================================================
    # Brak danych
    # ========================================================

    if (
        macd is None
        or macd_signal is None
    ):

        add_reason(
            reasons,
            "Trigger",
            0,
            "Brak danych MACD.",
        )

    else:

        macd_bullish = (
            macd > macd_signal
        )

        # ====================================================
        # ŚWIEŻE PRZECIĘCIE
        # ====================================================

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

        # ====================================================
        # MACD BULLISH + HISTOGRAM ROŚNIE
        # ====================================================

        elif (
            macd_bullish
            and histogram_rising
        ):

            points = 15

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                (
                    "MACD jest wzrostowy "
                    "i histogram rośnie."
                ),
            )

        # ====================================================
        # MACD BULLISH
        # ====================================================

        elif macd_bullish:

            points = 8

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                (
                    "MACD jest powyżej "
                    "linii sygnałowej."
                ),
            )

        # ====================================================
        # MACD BEARISH
        # ====================================================

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
    # ŚWIEŻE PRZECIĘCIE STOCHASTIC
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

        # ====================================================
        # ŚWIEŻE PRZECIĘCIE W WYPRZEDANIU
        # ====================================================

        if (
            fresh_stoch_cross
            and stoch_k < 30
        ):

            points = 5

            score += points

            add_reason(
                reasons,
                "Trigger",
                points,
                (
                    "Świeże bycze przecięcie "
                    f"Stochastic w strefie "
                    f"wyprzedania "
                    f"(%K={stoch_k:.1f})."
                ),
            )

        # ====================================================
        # STOCHASTIC WYCHODZI Z WYPRZEDANIA
        # ====================================================

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
                    f"z wyprzedania "
                    f"(%K={stoch_k:.1f})."
                ),
            )

        else:

            add_reason(
                reasons,
                "Trigger",
                0,
                (
                    "Brak świeżego byczego "
                    "triggera Stochastic."
                ),
            )

    else:

        add_reason(
            reasons,
            "Trigger",
            0,
            "Brak pełnych danych Stochastic.",
        )

    # ========================================================
    # ADX / DI
    # ========================================================

    adx = _safe_number(
        getattr(
            analysis,
            "adx",
            None,
        )
    )

    plus_di = _safe_number(
        getattr(
            analysis,
            "plus_di",
            None,
        )
    )

    minus_di = _safe_number(
        getattr(
            analysis,
            "minus_di",
            None,
        )
    )

    if (
        adx is not None
        and plus_di is not None
        and minus_di is not None
    ):

        if (
            adx >= 20
            and plus_di > minus_di
        ):

            adx_pts = 5

            score += adx_pts

            add_reason(
                reasons,
                "Trigger",
                adx_pts,
                (
                    f"Potwierdzenie trendu ADX "
                    f"({adx:.1f}) oraz +DI > -DI."
                ),
            )

        else:

            add_reason(
                reasons,
                "Trigger",
                0,
                (
                    "Brak potwierdzenia siły "
                    "trendu ADX/DI."
                ),
            )

    else:

        add_reason(
            reasons,
            "Trigger",
            0,
            "Brak pełnych danych ADX/DI.",
        )

    # ========================================================
    # LIMIT TRIGGERA
    # ========================================================

    score = min(
        score,
        30,
    )

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
                f"({vol_ratio:.2f}x średniej)."
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
                f"({vol_ratio:.2f}x średniej)."
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
                f"Umiarkowanie podwyższony "
                f"wolumen "
                f"({vol_ratio:.2f}x średniej)."
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
                f"Nieznacznie podwyższony "
                f"wolumen "
                f"({vol_ratio:.2f}x średniej)."
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
            (
                "Przeciętny lub niski "
                "wolumen na wejściu."
            ),
        )

    return score, reasons