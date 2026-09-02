"""
dwuwarstwowy system decyzyjny używany przez profesjonalny trading algorytmiczny:
Quality Score >= 75-80 $\rightarrow$ Skaner tworzy listę obserwacyjną ("To są świetne spółki z silnym trendem").
Entry Score >= 80-85 $\rightarrow$ Skaner wyrzuca natychmiastowy alert transakcyjny ("I właśnie w tej sekundzie masz idealny punkt do zajęcia pozycji z małym ryzykiem").


Moduł scoringu,Maks. punkty,Warunek dla maksa
score_trend,20 pkt,STRONG_UP
score_ema_crossover,15 pkt,Świeży Złoty Krzyż (EMA50 > EMA200)
score_macd,15 pkt,MACD nad sygnałem + rosnący histogram
score_support,12 pkt,Tuż nad silnym wsparciem (testowanym ≥5 razy)
score_resistance,10 pkt,Wybicie szczytów wszech czasów (ATH / brak oporów)
score_rsi,10 pkt,RSI zrównoważone (45–60) lub w strefie korekty
score_volume,10 pkt,Wolumen ≥2.0× średniej
score_extension,5 pkt,Cena w bliskiej odległości od EMA20 (0–3%)
RAZEM TEORTYCZNIE,97 pkt,(Idealny stan rynkowy)

Praktyczna uwaga:
W realnym handlu spółki niezwykle rzadko osiągną pełne 97–100 punktów, ponieważ niektóre warunki rynkowe rzadko występują jednocześnie (np. idealne odbicie od wsparcia rzadko zbiega się ze świeżym wybiciem szczytów ATH bez oporów).

Dla Twojego skanera progi jakościowe możesz przyjąć następująco:

🟢 85–100+ pkt: Top okazja (Bardzo silny trend z pełnym potwierdzeniem impetu i świetnym momentem na wejście)

🟡 70–84 pkt: Dobra spółka (Solidny układ techniczny, warta obserwacji lub wejścia pakietowego)

⚪ 50–69 pkt: Neutralna / Średniak (Brak wyraźnego przewagi)

🔴 Poniżej 50 pkt: Omijaj / Słaby układ
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
        score_quality_obv,
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    # Wynik zawsze 0-100
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
            "Silny trend spadkowy / brak przewagi kupujących"
        )

    # ADX nie określa kierunku.
    # Jest tylko potwierdzeniem siły trendu.

    if adx is not None:

        if trend in ("UP", "STRONG_UP"):

            if adx >= 30:
                score += 5
                add_reason(
                    reasons,
                    "ADX",
                    5,
                    f"Silna dynamika trendu (ADX: {adx:.1f})"
                )

            elif adx < 18:
                score -= 2
                add_reason(
                    reasons,
                    "ADX",
                    -2,
                    f"Słaba dynamika trendu (ADX: {adx:.1f})"
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

    prev_ema20 = safe_float(getattr(analysis, "prev_ema20", None))
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
    # 2. ŚWIEŻY ZŁOTY KRZYŻ
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

    above_signal = getattr(
        analysis,
        "macd_above_signal",
        None
    )

    histogram_rising = getattr(
        analysis,
        "histogram_rising",
        None
    )

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

        score += 3

        add_reason(
            reasons,
            "MACD",
            3,
            "MACD blisko linii sygnału"
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

        elif 60 < rsi <= 70:

            score += 6

            add_reason(
                reasons,
                "RSI",
                6,
                f"RSI pokazuje silne momentum ({rsi:.1f})"
            )

        elif rsi > 70:

            score += 1

            add_reason(
                reasons,
                "RSI",
                1,
                f"RSI wykupione — ryzyko schłodzenia ({rsi:.1f})"
            )

        else:

            score += 0

            add_reason(
                reasons,
                "RSI",
                0,
                f"RSI bardzo niskie — trend wymaga ostrożności ({rsi:.1f})"
            )

    # -------------------------------------------------------------
    # BRAK TRENDOWEJ PRZEWAGI
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

    # -------------------------------------------------------------
    # TREND SPADKOWY
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
# MAX: 12 pkt
# =====================================================================

def score_support(analysis):
    score = 0
    reasons = []

    support = getattr(
        analysis,
        "nearest_support",
        None
    )

    if not isinstance(support, dict):

        score -= 5

        add_reason(
            reasons,
            "Support",
            -5,
            "Brak wiarygodnego wsparcia poniżej ceny"
        )

        return score, reasons

    price = safe_float(support.get("price"))
    distance = safe_float(
        getattr(analysis, "support_distance", None)
    )

    # WAŻNE:
    # w Twoim modelu poziom używa pola "tests",
    # a nie "touches".

    tests = support.get("tests", 1)

    try:
        tests = int(tests)
    except (TypeError, ValueError):
        tests = 1

    if price is None or distance is None:
        return score, reasons

    if distance <= 1.5 and tests >= 5:

        score += 12

        add_reason(
            reasons,
            "Support",
            12,
            f"Cena tuż nad bardzo silnym wsparciem ({tests} testów)"
        )

    elif distance <= 1.5:

        score += 8

        add_reason(
            reasons,
            "Support",
            8,
            f"Cena blisko wsparcia ({tests} testów)"
        )

    elif distance <= 3.5:

        score += 4

        add_reason(
            reasons,
            "Support",
            4,
            f"Wsparcie znajduje się w pobliżu ({distance:.1f}%)"
        )

    elif distance >= 10:

        score += 0

        add_reason(
            reasons,
            "Support",
            0,
            "Wsparcie znajduje się daleko"
        )

    else:

        score += 2

        add_reason(
            reasons,
            "Support",
            2,
            f"Bezpieczny odstęp od wsparcia ({distance:.1f}%)"
        )

    return score, reasons


# =====================================================================
# RESISTANCE
# MAX: 10 pkt
# =====================================================================

def score_resistance(analysis):
    score = 0
    reasons = []

    resistance = getattr(
        analysis,
        "nearest_resistance",
        None
    )

    if not isinstance(resistance, dict):

        score += 10

        add_reason(
            reasons,
            "Resistance",
            10,
            "Brak najbliższego oporu — dużo miejsca nad ceną"
        )

        return score, reasons

    distance = safe_float(
        getattr(analysis, "resistance_distance", None)
    )

    tests = resistance.get("tests", 1)

    try:
        tests = int(tests)
    except (TypeError, ValueError):
        tests = 1

    if distance is None:
        return score, reasons

    if distance <= 1.5 and tests >= 5:

        score -= 10

        add_reason(
            reasons,
            "Resistance",
            -10,
            f"Cena tuż pod bardzo silnym oporem ({tests} testów)"
        )

    elif distance <= 1.5:

        score -= 6

        add_reason(
            reasons,
            "Resistance",
            -6,
            f"Cena blisko oporu ({tests} testów)"
        )

    elif distance >= 10:

        score += 5

        add_reason(
            reasons,
            "Resistance",
            5,
            f"Dużo miejsca do najbliższego oporu ({distance:.1f}%)"
        )

    else:

        score += 2

        add_reason(
            reasons,
            "Resistance",
            2,
            f"Bezpieczny odstęp od oporu ({distance:.1f}%)"
        )

    return score, reasons


# =====================================================================
# VOLUME
# MAX: 5 pkt
# =====================================================================

def score_volume(analysis):
    score = 0
    reasons = []

    vol_ratio = safe_float(
        getattr(analysis, "vol_ratio", None)
    )

    price = safe_float(
        getattr(analysis, "price", None)
    )

    previous_price = safe_float(
        getattr(analysis, "prev_price", None)
    )

    if vol_ratio is None:
        return score, reasons

    price_rising = (
        price is not None
        and previous_price is not None
        and price > previous_price
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

            score += 0

            add_reason(
                reasons,
                "Volume",
                0,
                f"Wysoki wolumen, ale brak potwierdzenia wzrostem ceny ({vol_ratio:.1f}x)"
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

    k = safe_float(
        getattr(analysis, "stoch_k", None)
    )

    d = safe_float(
        getattr(analysis, "stoch_d", None)
    )

    prev_k = safe_float(
        getattr(analysis, "prev_stoch_k", None)
    )

    prev_d = safe_float(
        getattr(analysis, "prev_stoch_d", None)
    )

    if k is None or d is None:
        return score, reasons

    trend = get_trend_value(analysis)

    # -------------------------------------------------------------
    # PRAWDZIWE PRZECIĘCIE %K NAD %D
    # -------------------------------------------------------------

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

    if bullish_cross and trend in ("UP", "STRONG_UP"):

        score += 5

        add_reason(
            reasons,
            "Stochastic",
            5,
            f"Bycze przecięcie Stochastic w trendzie wzrostowym (%K: {k:.1f})"
        )

    elif k < 20 and d < 20 and trend in ("UP", "STRONG_UP"):

        score += 4

        add_reason(
            reasons,
            "Stochastic",
            4,
            f"Wyprzedanie Stochastic w trendzie wzrostowym ({k:.1f})"
        )

    elif bearish_cross:

        score -= 2

        add_reason(
            reasons,
            "Stochastic",
            -2,
            f"Niedźwiedzie przecięcie Stochastic ({k:.1f})"
        )

    elif k > 80:

        score -= 2

        add_reason(
            reasons,
            "Stochastic",
            -2,
            f"Stochastic wykupiony ({k:.1f})"
        )

    return score, reasons


# =====================================================================
# EXTENSION + BOLLINGER
# MAX: 3 pkt
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
    # ODLEGŁOŚĆ OD EMA20
    # -------------------------------------------------------------

    if dist_ema20 is not None:

        if 0 <= dist_ema20 <= 2:

            score += 3

            add_reason(
                reasons,
                "Extension",
                3,
                f"Cena blisko EMA20 ({dist_ema20:.1f}%)"
            )

        elif 2 < dist_ema20 <= 4:

            score += 1

            add_reason(
                reasons,
                "Extension",
                1,
                f"Cena umiarkowanie oddalona od EMA20 ({dist_ema20:.1f}%)"
            )

        elif dist_ema20 > 8:

            score -= 3

            add_reason(
                reasons,
                "Extension",
                -3,
                f"Cena mocno rozciągnięta nad EMA20 ({dist_ema20:.1f}%)"
            )

    # -------------------------------------------------------------
    # BOLLINGER
    # NIE dajemy automatycznie +5 za dolną wstęgę.
    # -------------------------------------------------------------

    if close is not None and bb_upper is not None:

        if close >= bb_upper:

            score -= 2

            add_reason(
                reasons,
                "Bollinger",
                -2,
                "Cena przy górnej wstędze Bollingera — ryzyko przegrzania"
            )

    if (
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
            "Cena przy dolnej wstędze podczas trendu wzrostowego — możliwa korekta"
        )

    return score, reasons


# =====================================================================
# OBV
# MAX: 5 pkt
# =====================================================================

def score_quality_obv(analysis):
    score = 0
    reasons = []

    obv_rising = getattr(
        analysis,
        "obv_rising",
        False
    )

    obv_bullish_div = getattr(
        analysis,
        "obv_bullish_div",
        False
    )

    obv_bearish_div = getattr(
        analysis,
        "obv_bearish_div",
        False
    )

    # -------------------------------------------------------------
    # DYWERGENCJA BYCZA
    # -------------------------------------------------------------

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

    else:

        add_reason(
            reasons,
            "OBV",
            0,
            "Brak wyraźnego potwierdzenia ze strony OBV"
        )

    # -------------------------------------------------------------
    # DYWERGENCJA NIEDŹWIEDZIA
    # -------------------------------------------------------------

    if obv_bearish_div:

        score -= 5

        add_reason(
            reasons,
            "OBV",
            -5,
            "Niedźwiedzia dywergencja OBV — ryzyko słabnięcia ruchu"
        )

    return score, reasons