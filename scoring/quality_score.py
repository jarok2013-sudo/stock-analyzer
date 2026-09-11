"""
QUALITY SCORE
0–100 pkt

Znaczenie:
🟢 85–100 pkt: Bardzo silna jakość techniczna
🟡 70–84 pkt: Dobra jakość techniczna
⚪ 50–69 pkt: Neutralna / średnia jakość
🔴 <50 pkt: Słaba jakość techniczna

Quality Score odpowiada na pytanie:
"Czy technicznie spółka jest zdrowa i ma przewagę kupujących?"

Nie ocenia bezpośrednio:
- czy TERAZ jest dobry moment na wejście,
- czy cena jest blisko supportu,
- czy R/R jest atrakcyjne.

Za moment wejścia odpowiada Entry Score.
"""

import pandas as pd
import config


# =====================================================================
# HELPERS
# =====================================================================

def add_reason(reasons, category, points, text):
    reasons.append({
        "category": category,
        "points": points,
        "text": text
    })


def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_trend_value(analysis):
    trend = getattr(analysis, "trend", "UNKNOWN")

    if isinstance(trend, dict):
        return trend.get("trend", "UNKNOWN")

    return str(trend)


def is_uptrend(analysis):
    return get_trend_value(analysis) in ("UP", "STRONG_UP")


# =====================================================================
# MAIN QUALITY SCORE
# =====================================================================

def calculate_quality_score(analysis):
    score = 0
    reasons = []

    scorers = [
        score_trend,
        score_ema_crossovers,
        score_macd,
        score_rsi,
        score_support,
        score_resistance,
        score_volume,
        score_stoch,
        score_extension,
        score_obv,
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    # Wynik zawsze 0–100
    final_score = max(0, min(100, score))

    return final_score, reasons


# =====================================================================
# TREND + ADX
# MAX: 20 pkt
# =====================================================================

def score_trend(analysis):
    score = 0
    reasons = []

    trend = get_trend_value(analysis)
    adx = safe_float(getattr(analysis, "adx", None))

    # -------------------------------------------------------------
    # TREND
    # -------------------------------------------------------------

    if trend == "STRONG_UP":
        score += 15
        add_reason(
            reasons,
            "Trend",
            15,
            "Silny trend wzrostowy"
        )

    elif trend == "UP":
        score += 10
        add_reason(
            reasons,
            "Trend",
            10,
            "Trend wzrostowy"
        )

    elif trend == "SIDEWAYS":
        score += 4
        add_reason(
            reasons,
            "Trend",
            4,
            "Trend boczny / konsolidacja"
        )

    elif trend == "DOWN":
        score += 0
        add_reason(
            reasons,
            "Trend",
            0,
            "Trend spadkowy"
        )

    else:
        score -= 5
        add_reason(
            reasons,
            "Trend",
            -5,
            "Brak przewagi kupujących / niekorzystna struktura trendu"
        )

    # -------------------------------------------------------------
    # ADX
    #
    # ADX nie mówi, czy trend jest wzrostowy/spadkowy.
    # Mówi przede wszystkim o sile ruchu.
    # -------------------------------------------------------------

    if adx is not None:

        if trend in ("UP", "STRONG_UP"):

            if adx >= 40:
                score += 5
                add_reason(
                    reasons,
                    "ADX",
                    5,
                    f"Bardzo silna dynamika trendu wzrostowego (ADX: {adx:.1f})"
                )

            elif adx >= 30:
                score += 4
                add_reason(
                    reasons,
                    "ADX",
                    4,
                    f"Silna dynamika trendu wzrostowego (ADX: {adx:.1f})"
                )

            elif adx >= 24:
                score += 2
                add_reason(
                    reasons,
                    "ADX",
                    2,
                    f"Dobra siła trendu wzrostowego (ADX: {adx:.1f})"
                )

            elif adx < 18:
                score -= 2
                add_reason(
                    reasons,
                    "ADX",
                    -2,
                    f"Słaba dynamika trendu (ADX: {adx:.1f})"
                )

            else:
                add_reason(
                    reasons,
                    "ADX",
                    0,
                    f"Umiarkowana siła trendu (ADX: {adx:.1f})"
                )

        elif trend in ("DOWN", "STRONG_DOWN"):

            if adx >= 30:
                score -= 5
                add_reason(
                    reasons,
                    "ADX",
                    -5,
                    f"Silny trend spadkowy potwierdzony przez ADX ({adx:.1f})"
                )

            elif adx >= 24:
                score -= 2
                add_reason(
                    reasons,
                    "ADX",
                    -2,
                    f"Trend spadkowy ma wyraźną dynamikę (ADX: {adx:.1f})"
                )

    return score, reasons


# =====================================================================
# EMA
# MAX: 15 pkt
# =====================================================================

def score_ema_crossovers(analysis):
    score = 0
    reasons = []

    ema20 = safe_float(getattr(analysis, "ema20", None))
    ema50 = safe_float(getattr(analysis, "ema50", None))
    ema200 = safe_float(getattr(analysis, "ema200", None))

    prev_ema50 = safe_float(getattr(analysis, "prev_ema50", None))
    prev_ema200 = safe_float(getattr(analysis, "prev_ema200", None))

    if None in (ema20, ema50, ema200):
        return score, reasons

    # -------------------------------------------------------------
    # 1. UKŁAD EMA
    # -------------------------------------------------------------

    if ema20 > ema50 > ema200:
        score += 10
        add_reason(
            reasons,
            "EMA Alignment",
            10,
            "Byczy układ EMA20 > EMA50 > EMA200"
        )

    elif ema20 > ema50:
        score += 5
        add_reason(
            reasons,
            "EMA Alignment",
            5,
            "EMA20 znajduje się powyżej EMA50"
        )

    elif ema20 < ema50 < ema200:
        score -= 8
        add_reason(
            reasons,
            "EMA Alignment",
            -8,
            "Niedźwiedzi układ EMA20 < EMA50 < EMA200"
        )

    elif ema20 < ema50:
        score -= 4
        add_reason(
            reasons,
            "EMA Alignment",
            -4,
            "EMA20 znajduje się poniżej EMA50"
        )

    # -------------------------------------------------------------
    # 2. ŚWIEŻY ZŁOTY / ŚMIERCI KRZYŻ
    # -------------------------------------------------------------

    if None not in (prev_ema50, prev_ema200):

        if ema50 > ema200 and prev_ema50 <= prev_ema200:
            score += 5
            add_reason(
                reasons,
                "EMA Crossover",
                5,
                "Świeży złoty krzyż: EMA50 przebiła EMA200"
            )

        elif ema50 < ema200 and prev_ema50 >= prev_ema200:
            score -= 5
            add_reason(
                reasons,
                "EMA Crossover",
                -5,
                "Krzyż śmierci: EMA50 spadła poniżej EMA200"
            )

    return score, reasons


# =====================================================================
# MACD
# MAX: 15 pkt
# =====================================================================

def score_macd(analysis):
    score = 0
    reasons = []

    macd = safe_float(getattr(analysis, "macd", None))
    signal = safe_float(getattr(analysis, "macd_signal", None))

    above_signal = getattr(analysis, "macd_above_signal", None)
    histogram_rising = getattr(analysis, "histogram_rising", None)

    if macd is None or signal is None:
        return score, reasons

    if above_signal and histogram_rising:
        score += 15
        add_reason(
            reasons,
            "MACD",
            15,
            "MACD powyżej sygnału i rosnący histogram"
        )

    elif above_signal:
        score += 10
        add_reason(
            reasons,
            "MACD",
            10,
            "MACD powyżej linii sygnału"
        )

    elif macd < signal:
        score += 0
        add_reason(
            reasons,
            "MACD",
            0,
            "MACD poniżej linii sygnału"
        )

    else:
        add_reason(
            reasons,
            "MACD",
            0,
            "MACD neutralny względem linii sygnału"
        )

    return score, reasons


# =====================================================================
# RSI
# MAX: 10 pkt
# =====================================================================

def score_rsi(analysis):
    score = 0
    reasons = []

    rsi = safe_float(getattr(analysis, "rsi", None))

    if rsi is None:
        return score, reasons

    trend = get_trend_value(analysis)

    # -------------------------------------------------------------
    # TREND WZROSTOWY
    # -------------------------------------------------------------

    if trend in ("UP", "STRONG_UP"):

        if 40 <= rsi <= 60:
            score += 10
            add_reason(
                reasons,
                "RSI",
                10,
                f"RSI w zdrowej strefie trendu ({rsi:.1f})"
            )

        elif 30 <= rsi < 40:
            score += 8
            add_reason(
                reasons,
                "RSI",
                8,
                f"RSI wskazuje na korektę w trendzie wzrostowym ({rsi:.1f})"
            )

        elif rsi < 30:
            score += 8
            add_reason(
                reasons,
                "RSI",
                8,
                f"RSI skrajnie niskie w trendzie wzrostowym ({rsi:.1f})"
            )

        elif 60 < rsi <= 70:
            score += 6
            add_reason(
                reasons,
                "RSI",
                6,
                f"RSI pokazuje silne momentum ({rsi:.1f})"
            )

        elif 70 < rsi <= 75:
            score += 2
            add_reason(
                reasons,
                "RSI",
                2,
                f"RSI wysokie — trend nadal silny, ale rośnie ryzyko przegrzania ({rsi:.1f})"
            )

        else:
            score += 0
            add_reason(
                reasons,
                "RSI",
                0,
                f"RSI bardzo wysokie — podwyższone ryzyko przegrzania ({rsi:.1f})"
            )

    # -------------------------------------------------------------
    # KONSOLIDACJA
    # -------------------------------------------------------------

    elif trend == "SIDEWAYS":

        if 40 <= rsi <= 60:
            score += 5
            add_reason(
                reasons,
                "RSI",
                5,
                f"RSI neutralne ({rsi:.1f})"
            )

        elif rsi < 30:
            score += 3
            add_reason(
                reasons,
                "RSI",
                3,
                f"RSI wskazuje na wyprzedanie w konsolidacji ({rsi:.1f})"
            )

        elif rsi > 70:
            score -= 2
            add_reason(
                reasons,
                "RSI",
                -2,
                f"RSI wysokie w konsolidacji — ryzyko cofnięcia ({rsi:.1f})"
            )

    # -------------------------------------------------------------
    # TREND SPADKOWY / UNKNOWN
    # -------------------------------------------------------------

    else:
        add_reason(
            reasons,
            "RSI",
            0,
            f"RSI nie daje przewagi kupującym ({rsi:.1f})"
        )

    return score, reasons


# =====================================================================
# SUPPORT
# MAX: 8 pkt
#
# Support w Quality Score opisuje jakość struktury.
# Sama bliskość supportu jest przede wszystkim zadaniem Entry Score.
# =====================================================================

def score_support(analysis):
    score = 0
    reasons = []

    support = getattr(analysis, "nearest_support", None)
    rated_supports = getattr(analysis, "rated_supports", [])
    price_val = safe_float(getattr(analysis, "price", None))

    # -------------------------------------------------------------
    # BRAK SUPPORTU POD CENĄ
    # -------------------------------------------------------------

    if not isinstance(support, dict):

        broken_supports = [
            s
            for s in rated_supports
            if (
                isinstance(s, dict)
                and safe_float(s.get("price")) is not None
                and price_val is not None
                and safe_float(s.get("price")) > price_val
            )
        ]

        if broken_supports:
            score -= 6
            add_reason(
                reasons,
                "Support",
                -6,
                "Cena znajduje się poniżej znanego wsparcia — pogorszenie struktury"
            )
        else:
            score -= 2
            add_reason(
                reasons,
                "Support",
                -2,
                "Brak wiarygodnego wsparcia poniżej ceny"
            )

        return score, reasons

    price = safe_float(support.get("price"))
    distance = safe_float(getattr(analysis, "support_distance", None))

    touches = support.get("touches", 1)

    try:
        touches = int(touches)
    except (TypeError, ValueError):
        touches = 1

    if price is None or distance is None:
        return score, reasons

    # -------------------------------------------------------------
    # SILNE WSPARCIE = JAKOŚĆ STRUKTURY
    # NIE DAJEMY 12 PKT ZA SAMĄ BLISKOŚĆ.
    # -------------------------------------------------------------

    if touches >= 5:
        score += 6
        add_reason(
            reasons,
            "Support",
            6,
            f"Silne wsparcie strukturalne ({touches} testów)"
        )

    elif touches >= 3:
        score += 4
        add_reason(
            reasons,
            "Support",
            4,
            f"Wiarygodne wsparcie ({touches} testy)"
        )

    elif touches >= 2:
        score += 2
        add_reason(
            reasons,
            "Support",
            2,
            f"Widoczne wsparcie ({touches} testy)"
        )

    else:
        score += 1
        add_reason(
            reasons,
            "Support",
            1,
            "Obecne wsparcie, ale słabo potwierdzone"
        )

    return score, reasons


# =====================================================================
# RESISTANCE
# MAX: 8 pkt
#
# Resistance w Quality Score ocenia strukturę i przestrzeń,
# ale nie traktujemy braku oporu jako automatycznego +10.
# =====================================================================

def score_resistance(analysis):
    score = 0
    reasons = []

    resistance = getattr(analysis, "nearest_resistance", None)
    rated_resistances = getattr(analysis, "rated_resistances", [])
    price_val = safe_float(getattr(analysis, "price", None))

    # -------------------------------------------------------------
    # OPÓR NAD CENĄ
    # -------------------------------------------------------------

    if isinstance(resistance, dict):

        res_price = safe_float(resistance.get("price"))
        distance = safe_float(
            getattr(analysis, "resistance_distance", None)
        )

        if res_price is None or distance is None:
            return score, reasons

        touches = resistance.get("touches", 1)

        try:
            touches = int(touches)
        except (TypeError, ValueError):
            touches = 1

        # Bliski silny opór = ryzyko strukturalne
        if 0 <= distance <= 2.0:

            if touches >= 5:
                score -= 8
                add_reason(
                    reasons,
                    "Resistance",
                    -8,
                    f"Cena blisko bardzo silnego oporu ({touches} testów, {distance:.1f}%)"
                )
            else:
                score -= 5
                add_reason(
                    reasons,
                    "Resistance",
                    -5,
                    f"Cena blisko oporu ({touches} testów, {distance:.1f}%)"
                )

        elif 2.0 < distance < 5.0:

            add_reason(
                reasons,
                "Resistance",
                0,
                f"Umiarkowana przestrzeń do oporu ({distance:.1f}%)"
            )

        elif 5.0 <= distance < 10.0:

            score += 2
            add_reason(
                reasons,
                "Resistance",
                2,
                f"Dobra przestrzeń do najbliższego oporu ({distance:.1f}%)"
            )

        else:

            score += 4
            add_reason(
                reasons,
                "Resistance",
                4,
                f"Dużo przestrzeni do najbliższego oporu ({distance:.1f}%)"
            )

        return score, reasons

    # -------------------------------------------------------------
    # BRAK OPORU NAD CENĄ
    # -------------------------------------------------------------

    broken_resistances = [
        r
        for r in rated_resistances
        if (
            isinstance(r, dict)
            and safe_float(r.get("price")) is not None
            and price_val is not None
            and safe_float(r.get("price")) < price_val
        )
    ]

    if broken_resistances:

        last_broken = max(
            broken_resistances,
            key=lambda x: safe_float(x.get("price"))
        )

        broken_price = safe_float(last_broken.get("price"))

        score += 6

        add_reason(
            reasons,
            "Resistance",
            6,
            f"Cena znajduje się powyżej ostatniego znanego oporu ({broken_price:.2f})"
        )

    else:

        # Brak oporu ≠ automatycznie idealny breakout.
        score += 2

        add_reason(
            reasons,
            "Resistance",
            2,
            "Brak wiarygodnego oporu powyżej ceny"
        )

    return score, reasons


# =====================================================================
# VOLUME
# MAX: 5 pkt
# =====================================================================

def score_volume(analysis):
    score = 0
    reasons = []

    vol_ratio = safe_float(getattr(analysis, "vol_ratio", None))
    price = safe_float(getattr(analysis, "price", None))
    previous_price = safe_float(getattr(analysis, "prev_price", None))

    if vol_ratio is None:
        return score, reasons

    price_rising = (
        price is not None
        and previous_price is not None
        and price >= previous_price
    )

    if vol_ratio >= 2.0:

        if price_rising:
            score += 5
            add_reason(
                reasons,
                "Volume",
                5,
                f"Wysoki wolumen potwierdza wzrost ({vol_ratio:.1f}x średniej)"
            )
        else:
            add_reason(
                reasons,
                "Volume",
                0,
                f"Wysoki wolumen bez potwierdzenia wzrostem ceny ({vol_ratio:.1f}x)"
            )

    elif vol_ratio >= 1.2:

        if price_rising:
            score += 3
            add_reason(
                reasons,
                "Volume",
                3,
                f"Podwyższony wolumen wspiera wzrost ({vol_ratio:.1f}x)"
            )
        else:
            score += 1
            add_reason(
                reasons,
                "Volume",
                1,
                f"Podwyższony wolumen ({vol_ratio:.1f}x średniej)"
            )

    elif vol_ratio < 0.6:

        score -= 1
        add_reason(
            reasons,
            "Volume",
            -1,
            f"Niski wolumen ({vol_ratio:.1f}x średniej)"
        )

    return score, reasons


# =====================================================================
# STOCHASTIC
# MAX: 5 pkt
# =====================================================================

def score_stoch(analysis):
    score = 0
    reasons = []

    k = safe_float(getattr(analysis, "stoch_k", None))
    d = safe_float(getattr(analysis, "stoch_d", None))

    prev_k = safe_float(getattr(analysis, "prev_stoch_k", None))
    prev_d = safe_float(getattr(analysis, "prev_stoch_d", None))

    if k is None or d is None:
        return score, reasons

    trend = get_trend_value(analysis)

    bullish_cross = (
        prev_k is not None
        and prev_d is not None
        and prev_k <= prev_d
        and k > d
    )

    bearish_cross = (
        prev_k is not None
        and prev_d is not None
        and prev_k >= prev_d
        and k < d
    )

    # -------------------------------------------------------------
    # HIERARCHICZNA KLASYFIKACJA
    # -------------------------------------------------------------

    if bullish_cross and trend in ("UP", "STRONG_UP"):

        score += 5

        add_reason(
            reasons,
            "Stochastic",
            5,
            f"Bycze przecięcie Stochastic (%K: {k:.1f})"
        )

    elif k < 20 and d < 20 and trend in ("UP", "STRONG_UP"):

        score += 4

        add_reason(
            reasons,
            "Stochastic",
            4,
            f"Stochastic wyprzedany w trendzie (%K: {k:.1f})"
        )

    elif bearish_cross:

        score -= 2

        add_reason(
            reasons,
            "Stochastic",
            -2,
            f"Niedźwiedzie przecięcie Stochastic (%K: {k:.1f})"
        )

    elif k > 80:

        score -= 2

        add_reason(
            reasons,
            "Stochastic",
            -2,
            f"Stochastic wykupiony (%K: {k:.1f})"
        )

    else:

        add_reason(
            reasons,
            "Stochastic",
            0,
            f"Stochastic w strefie neutralnej (%K: {k:.1f})"
        )

    return score, reasons


# =====================================================================
# EXTENSION + BOLLINGER
# MAX: 5 pkt
#
# Tutaj oceniamy zdrowie struktury względem EMA20,
# a nie bezpośrednią atrakcyjność wejścia.
# =====================================================================

def score_extension(analysis):
    score = 0
    reasons = []

    dist_ema20 = safe_float(
        getattr(analysis, "dist_ema20_pct", None)
    )

    close = safe_float(
        getattr(analysis, "price", None)
    )

    bb_upper = safe_float(
        getattr(analysis, "bb_upper", None)
    )

    bb_lower = safe_float(
        getattr(analysis, "bb_lower", None)
    )

    trend = get_trend_value(analysis)

    # -------------------------------------------------------------
    # EMA20
    #
    # WAŻNE:
    # abs() nie jest już używane.
    #
    # + punkty tylko wtedy, gdy cena znajduje się NAD EMA20.
    # -------------------------------------------------------------

    if dist_ema20 is not None:

        if 0 <= dist_ema20 <= 2:

            score += 3

            add_reason(
                reasons,
                "Extension",
                3,
                f"Cena zdrowo utrzymuje się nad EMA20 ({dist_ema20:.1f}%)"
            )

        elif 2 < dist_ema20 <= 4:

            score += 2

            add_reason(
                reasons,
                "Extension",
                2,
                f"Cena umiarkowanie oddalona nad EMA20 ({dist_ema20:.1f}%)"
            )

        elif 4 < dist_ema20 <= 8:

            score += 1

            add_reason(
                reasons,
                "Extension",
                1,
                f"Cena oddalona nad EMA20 ({dist_ema20:.1f}%)"
            )

        elif dist_ema20 > 8:

            score -= 3

            add_reason(
                reasons,
                "Extension",
                -3,
                f"Cena mocno rozciągnięta nad EMA20 ({dist_ema20:.1f}%)"
            )

        else:

            # Cena poniżej EMA20.
            # Nie karzemy tutaj drugi raz — EMA alignment już to ocenia.

            add_reason(
                reasons,
                "Extension",
                0,
                f"Cena znajduje się poniżej EMA20 ({dist_ema20:.1f}%)"
            )

    # -------------------------------------------------------------
    # BOLLINGER
    # -------------------------------------------------------------

    if (
        close is not None
        and bb_upper is not None
        and close >= bb_upper
    ):

        score -= 2

        add_reason(
            reasons,
            "Bollinger",
            -2,
            "Cena przy górnej wstędze Bollingera — ryzyko przegrzania"
        )

    elif (
        close is not None
        and bb_lower is not None
        and close <= bb_lower
        and trend in ("UP", "STRONG_UP")
    ):

        score += 1

        add_reason(
            reasons,
            "Bollinger",
            1,
            "Cena przy dolnej wstędze podczas trendu wzrostowego"
        )

    return score, reasons


# =====================================================================
# OBV
# MAX: 5 pkt
# =====================================================================

def score_obv(analysis):
    score = 0
    reasons = []

    obv_rising = getattr(analysis, "obv_rising", False)
    obv_bullish_div = getattr(analysis, "obv_bullish_div", False)
    obv_bearish_div = getattr(analysis, "obv_bearish_div", False)

    if obv_bullish_div:

        score += 5

        add_reason(
            reasons,
            "OBV",
            5,
            "Bycza dywergencja OBV — możliwa akumulacja"
        )

    elif obv_rising:

        score += 3

        add_reason(
            reasons,
            "OBV",
            3,
            "OBV rośnie — ruch ceny ma potwierdzenie wolumenowe"
        )

    elif obv_bearish_div:

        score -= 5

        add_reason(
            reasons,
            "OBV",
            -5,
            "Niedźwiedzia dywergencja OBV — ryzyko słabnięcia ruchu"
        )

    else:

        add_reason(
            reasons,
            "OBV",
            0,
            "Brak wyraźnego potwierdzenia ze strony OBV"
        )

    return score, reasons