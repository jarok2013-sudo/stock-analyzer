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


def add_reason(reasons, category, points, text):
    reasons.append({
        "category": category,
        "points": points,
        "text": text
    })


def calculate_quality_score(analysis):
    score = 0
    reasons = []

    # Lista modułów oceniania (włączając nowe wskaźniki)
    scorers = [
        score_trend,  # Teraz uwzględnia też ADX (+5 pkt)
        score_ema_crossovers,  # 15 pkt
        score_rsi,  # 10 pkt
        score_stoch,  # NOWOŚĆ: Stochastic (+6 pkt)
        score_macd,  # 15 pkt
        score_support,  # 12 pkt
        score_resistance,  # 10 pkt
        score_volume,  # 10 pkt
        score_extension,  # Teraz uwzględnia EMA20 + Bollinger Bands (+5 / -5 pkt)
        score_quality_obv,    # NOWOŚĆ: Skumulowany wolumen OBV (+10 / -12 pkt)
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    # Zabezpieczenie: wynik nie powinien spaść poniżej 0
    final_score = max(0, score)

    return final_score, reasons


# =====================================================================
# MODUŁY OCENIAJĄCE
# =====================================================================

"""
core_trend (Z filtrem siły ADX)Do dotychczasowych punktów za układ trendu 
dodajemy premię za wysoką wartość ADX ($>25$ oznaczą silny trend, $>40$ bardzo silny).
"""
def score_trend(analysis):
    score = 0
    reasons = []
    if isinstance(analysis.trend, dict):
        trend_val = analysis.trend.get("trend", "UNKNOWN")
    else:
        trend_val = str(analysis.trend)
    #trend = getattr(analysis, "trend", "SIDEWAYS")
    adx = getattr(analysis, "adx", None)

    # Base trend score
    if trend_val == "STRONG_UP":
        score += 20
        add_reason(reasons, "Trend", 20, "Silny trend wzrostowy")
    elif trend_val == "UP":
        score += 12
        add_reason(reasons, "Trend", 12, "Trend wzrostowy")
    elif trend_val == "SIDEWAYS":
        score += 5
        add_reason(reasons, "Trend", 5, "Trend boczny (konsolidacja)")
    elif trend_val == "DOWN":
        score += 0
        add_reason(reasons, "Trend", 0, "Trend spadkowy")
    else:
        score -= 5
        add_reason(reasons, "Trend", -5, "Silny trend spadkowy")

    # UZUPEŁNIENIE O ADX (Siła trendu)
    if adx is not None and trend_val in ["STRONG_UP", "UP"]:
        if adx >= 30:
            score += 5
            add_reason(
                reasons,
                "ADX",
                5,
                f"Potwierdzona wysoka siła trendu (ADX: {adx:.1f})",
            )
        elif adx < 18:
            score -= 4
            add_reason(
                reasons,
                "ADX",
                -4,
                f"Słaba dynamika trendu / ryzyko konsolidacji (ADX: {adx:.1f})",
            )

    return score, reasons


def score_ema_crossovers(analysis):
    score = 0
    reasons = []

    # Safe extraction (warto zabezpieczyć getattr na wypadek braku pól)
    ema20 = getattr(analysis, "ema20", None)
    ema50 = getattr(analysis, "ema50", None)
    ema200 = getattr(analysis, "ema200", None)

    prev_ema20 = getattr(analysis, "prev_ema20", None)
    prev_ema50 = getattr(analysis, "prev_ema50", None)
    prev_ema200 = getattr(analysis, "prev_ema200", None)

    # =========================================================================
    # 1. OCENA UKŁADU ŚREDNICH (Stan trwały / Położenie względem siebie)
    # =========================================================================
    if all(v is not None for v in [ema20, ema50, ema200]):
        # BYCZY UKŁAD: EMA20 > EMA50 > EMA200
        if ema20 > ema50 > ema200:
            score += 10
            add_reason(
                reasons,
                "EMA Alignment",
                10,
                "Byczy układ średnich: EMA20 > EMA50 > EMA200",
            )
        elif ema20 > ema50:
            score += 5
            add_reason(
                reasons,
                "EMA Alignment",
                5,
                "Krótkoterminowa przewaga byków (EMA20 > EMA50)",
            )

        # NIEDŹWIEDZI UKŁAD: EMA20 < EMA50 < EMA200
        elif ema20 < ema50 < ema200:
            score -= 10
            add_reason(
                reasons,
                "EMA Alignment",
                -10,
                "Niedźwiedzi układ średnich: EMA20 < EMA50 < EMA200",
            )
        elif ema20 < ema50:
            score -= 5
            add_reason(
                reasons,
                "EMA Alignment",
                -5,
                "Krótkoterminowa przewaga niedźwiedzi (EMA20 < EMA50)",
            )

    # =========================================================================
    # 2. OCENA ŚWIEŻYCH PRZECIĘĆ (Świeży impuls rynkowy)
    # =========================================================================
    # A. Długoterminowy impuls (EMA50 vs EMA200)
    if all(v is not None for v in [ema50, ema200, prev_ema50, prev_ema200]):
        # Złoty Krzyż (przebicie w górę)
        if ema50 > ema200 and prev_ema50 <= prev_ema200:
            score += 10
            add_reason(
                reasons,
                "EMA Crossover",
                10,
                "🚀 ZŁOTY KRZYŻ! Świeże przebicie EMA50 nad EMA200",
            )
        # Krzyż Śmierci (przebicie w dół)
        elif ema50 < ema200 and prev_ema50 >= prev_ema200:
            score -= 15
            add_reason(
                reasons,
                "EMA Crossover",
                -15,
                "💀 KRZYŻ ŚMIERCI! EMA50 spadła poniżej EMA200",
            )

    # B. Krótkoterminowy impuls (EMA20 vs EMA50)
    if all(v is not None for v in [ema20, ema50, prev_ema20, prev_ema50]):
        if ema20 > ema50 and prev_ema20 <= prev_ema50:
            score += 5
            add_reason(
                reasons,
                "EMA Crossover",
                5,
                "Krótkoterminowy sygnał kupna: EMA20 wybiła nad EMA50",
            )
        elif ema20 < ema50 and prev_ema20 >= prev_ema50:
            score -= 5
            add_reason(
                reasons,
                "EMA Crossover",
                -5,
                "Krótkoterminowy sygnał sprzedaży: EMA20 spadła pod EMA50",
            )

    return score, reasons

def score_rsi(analysis):
    score = 0
    reasons = []
    rsi = getattr(analysis, "rsi", None)

    # Zabezpieczenie przed brakiem danych lub NaN
    if rsi is None or pd.isna(rsi):
        add_reason(reasons, "RSI", 0, "Brak danych RSI do oceny")
        return score, reasons

    # Logika oceny oparta o stałe z config.py
    if rsi < config.RSI_OVERSOLD:  # < 35
        score += 7
        add_reason(
            reasons,
            "RSI",
            7,
            f"RSI mocno wyprzedane ({rsi:.1f}) - szansa na odbicie",
        )
    elif config.RSI_OVERSOLD <= rsi < config.RSI_GOOD:  # 35 - 45
        score += 9
        add_reason(reasons, "RSI", 9, f"RSI w strefie korekty ({rsi:.1f})")
    elif config.RSI_GOOD <= rsi <= config.RSI_IDEAL:  # 45 - 60
        score += 10
        add_reason(
            reasons, "RSI", 10, f"RSI idealne / zrównoważone ({rsi:.1f})"
        )
    elif config.RSI_IDEAL < rsi <= config.RSI_OVERBOUGHT:  # 60 - 70
        score += 6
        add_reason(reasons, "RSI", 6, f"RSI lekko wykupione ({rsi:.1f})")
    elif (
        config.RSI_OVERBOUGHT < rsi <= config.RSI_STRONG_OVERBOUGHT
    ):  # 70 - 80
        score += 2
        add_reason(
            reasons,
            "RSI",
            2,
            f"RSI wykupione ({rsi:.1f}) - ryzyko schłodzenia",
        )
    else:  # > 80
        add_reason(
            reasons, "RSI", 0, f"RSI ekstremalnie wykupione ({rsi:.1f})"
        )

    return score, reasons




def score_macd(analysis):
    score = 0
    reasons = []

    if analysis.macd_above_signal and analysis.histogram_rising:
        score += 15
        add_reason(reasons, "MACD", 15, "MACD powyżej sygnału, momentum rośnie")
    elif analysis.macd_above_signal:
        score += 10
        add_reason(reasons, "MACD", 10, "MACD powyżej sygnału")
    # Skalowanie względne pod cenę waloru
    elif abs(analysis.macd - analysis.macd_signal) / analysis.price < 0.001:
        score += 5
        add_reason(reasons, "MACD", 5, "Możliwe bliskie przecięcie MACD")
    else:
        add_reason(reasons, "MACD", 0, "MACD poniżej sygnału")

    return score, reasons


def score_support(analysis):
    score = 0
    reasons = []

    # 1. Brak wsparcia
    supp = getattr(analysis, "nearest_support", None)
    is_no_support = (
        supp is None
        or not isinstance(supp, dict)
        or supp.get("price") is None
        or pd.isna(supp.get("price"))
    )

    # 1. Brak wsparcia pod nogami (np. nowe historyczne dołki)
    if is_no_support:
        score -= 10
        add_reason(
            reasons,
            "Support",
            -10,
            "Brak wsparcia poniżej (nowe dołki / brak dna)",
        )
        return score, reasons

    distance = analysis.support_distance

    # ZABEZPIECZENIE: Jeśli distance to None, traktujemy to neutralnie/bezpiecznie
    if distance is None:
        add_reason(
            reasons, "Support", 0, "Niezidentyfikowana odległość od wsparcia"
        )
        return score, reasons

    tests = analysis.nearest_support.get("touches", 1)

    # 2. Ocena odległości od wsparcia
    if distance <= 1.5 and tests >= 5:
        score += 12
        add_reason(
            reasons, "Support", 12, "Cena tuż nad bardzo silnym wsparciem"
        )
    elif distance <= 1.5:
        score += 8
        add_reason(reasons, "Support", 8, "Cena blisko wsparcia")
    elif distance <= 3.5:
        score += 4
        add_reason(reasons, "Support", 4, "Wsparcie w pobliżu")
    elif distance >= 10:
        add_reason(
            reasons, "Support", 0, "Wsparcie daleko (ryzyko głębszej korekty)"
        )
    else:
        score += 2
        add_reason(reasons, "Support", 2, "Bezpieczny odstęp od wsparcia")

    return score, reasons


def score_resistance(analysis):
    score = 0
    reasons = []

    res = getattr(analysis, "nearest_resistance", None)

    # Bezpieczne sprawdzenie braku oporu / wybicia ATH
    is_no_resistance = (
        res is None
        or not isinstance(res, dict)
        or res.get("price") is None
        or pd.isna(res.get("price"))
    )

    if is_no_resistance:
        score += 10
        add_reason(
            reasons,
            "Resistance",
            10,
            "Brak oporu nad głową (wybicie szczytów / ATH) 🚀",
        )
        return score, reasons

    distance = getattr(analysis, "resistance_distance", None)

    if distance is None:
        add_reason(
            reasons, "Resistance", 0, "Niezidentyfikowana odległość od oporu"
        )
        return score, reasons

    tests = res.get("touches", 1)

    if distance <= 1.5 and tests >= 5:
        score -= 10
        add_reason(reasons, "Resistance", -10, "Cena tuż pod silnym oporem")
    elif distance <= 1.5:
        score -= 6
        add_reason(reasons, "Resistance", -6, "Cena blisko oporu")
    elif distance >= 10:
        score += 5
        add_reason(reasons, "Resistance", 5, "Dużo miejsca do najbliższego oporu")
    else:
        score += 2
        add_reason(reasons, "Resistance", 2, "Bezpieczna odległość od oporu")

    return score, reasons


def score_volume(analysis):
    score = 0
    reasons = []
    
    # Stosunek bieżącego wolumenu do średniego wolumenu (np. volume_sma20)
    vol_ratio = getattr(analysis, "vol_ratio", 1.0)

    if vol_ratio >= 2.0:
        score += 10
        add_reason(reasons, "Volume", 10, f"Bardzo wysoki wolumen ({vol_ratio:.1f}x średniej)")
    elif vol_ratio >= 1.2:
        score += 5
        add_reason(reasons, "Volume", 5, f"Powiększony wolumen ({vol_ratio:.1f}x średniej)")
    elif vol_ratio < 0.6:
        score -= 3
        add_reason(reasons, "Volume", -3, f"Słaby wolumen / brak zainteresowania ({vol_ratio:.1f}x średniej)")

    return score, reasons

"""
score_extension (RSI + EMA + Bollinger Bands)
Zamiast patrzeć tylko na EMA20, sprawdzamy, 
czy cena nie wyskoczyła ponad górną Wstęgę Bollingera (co prawie zawsze skutkuje powrotem do średniej).
"""
def score_extension(analysis):
    score = 0
    reasons = []

    dist_ema20 = getattr(analysis, "dist_ema20_pct", 0.0)
    close = getattr(analysis, "price", None)
    bb_upper = getattr(analysis, "bb_upper", None)
    bb_lower = getattr(analysis, "bb_lower", None)

    # 1. Odchylenie od EMA20
    if dist_ema20 > 8.0:
        score -= 8
        add_reason(
            reasons,
            "Extension",
            -8,
            f"Cena mocno rozciągnięta nad EMA20 (+{dist_ema20:.1f}%) - ryzyko schłodzenia",
        )
    # ZMIANA: Ujednolicony próg do 2.0%
    elif 0.0 <= dist_ema20 <= 2.0:
        score += 5
        add_reason(
            reasons,
            "Extension",
            5,
            f"Cena przy samej EMA20 (+{dist_ema20:.1f}%) - optymalny punkt uchwytu",
        )
    elif 2.0 < dist_ema20 <= 4.0:
        score += 2
        add_reason(
            reasons,
            "Extension",
            2,
            f"Cena w akceptowalnej odległości od EMA20 (+{dist_ema20:.1f}%)",
        )

    # 2. UZUPEŁNIENIE O WSTĘGI BOLLINGERA
    if close and bb_upper and close >= bb_upper:
        score -= 5
        add_reason(
            reasons,
            "Bollinger",
            -5,
            f"Cena przebija górną Wstęgę Bollingera ({bb_upper:.1f}) - rynek lokalnie przegrzany",
        )
    elif close and bb_lower and close <= bb_lower:
        score += 5
        add_reason(
            reasons,
            "Bollinger",
            5,
            "Cena dotyka dolnej Wstęgi Bollingera ({bb_lower:.1f}) - strefa potencjalnego odbicia",
        )

    return score, reasons


"""
moduł score_stoch (Szybki impuls momentum)
Dodajemy jako osobny, mały moduł impulsowy Maks. +6 pkt. 
Szukamy wyprzedania w trendzie wzrostowym lub wygenerowania "szybkiego sygnału kupna" (przebicie %K nad %D).
"""

def score_stoch(analysis):
    score = 0
    reasons = []

    stoch_k = getattr(analysis, "stoch_k", None)
    stoch_d = getattr(analysis, "stoch_d", None)

    if stoch_k is None or stoch_d is None:
        return score, reasons

    # Wyprzedanie w trendzie wzrostowym (szansa na lokalne dno korekty)
    if stoch_k < 20 and stoch_d < 20:
        score += 6
        add_reason(
            reasons,
            "Stochastic",
            6,
            f"Stochastic w strefie silnego wyprzedania ({stoch_k:.1f}) - okazja po korekcie",
        )
    elif stoch_k > stoch_d and stoch_k < 50:
        score += 3
        add_reason(
            reasons,
            "Stochastic",
            3,
            "Stochastic daje prowzrostowy sygnał (linia %K przebija %D)",
        )
    elif stoch_k > 80:
        score -= 3
        add_reason(
            reasons,
            "Stochastic",
            -3,
            f"Stochastic w strefie silnego wykupienia ({stoch_k:.1f}) - ryzyko schłodzenia",
        )

    return score, reasons


# =====================================================================
# MODUŁ OBV (Akumulacja / Dystrybucja kapitału)
# =====================================================================

def score_quality_obv(analysis):
    """
    Ocenia spójność wolumenu skumulowanego (OBV) z ruchem cenowym.
    Max: +10 pkt (premie), Penalty: do -12 pkt (kary za dywergencje).
    """
    score = 0
    reasons = []

    obv_rising = getattr(analysis, "obv_rising", False)
    obv_bullish_div = getattr(analysis, "obv_bullish_div", False)
    obv_bearish_div = getattr(analysis, "obv_bearish_div", False)

    # 1. Bycza dywergencja (Najsilniejszy sygnał: duży kapitał skupuje w ukryciu)
    if obv_bullish_div:
        score += 10
        add_reason(
            reasons,
            "OBV",
            10,
            "🚀 Bycza dywergencja OBV (akumulacja kapitału mimo braku wzrostu ceny)",
        )
    # 2. Zdrowa akumulacja (Trend rosnący poparty wzrostem wskaźnika OBV)
    elif obv_rising:
        score += 6
        add_reason(
            reasons,
            "OBV",
            6,
            "Potwierdzenie wolumenowe: OBV rośnie (zdrowa akumulacja)",
        )
    else:
        add_reason(
            reasons,
            "OBV",
            0,
            "Brak wsparcia wolumenowego (OBV płaski lub spadkowy)",
        )

    # 3. KARA: Niedźwiedzia dywergencja (Ucieczka kapitału przy rosnącej cenie)
    if obv_bearish_div:
        score -= 12
        add_reason(
            reasons,
            "OBV",
            -12,
            "⚠️ Niedźwiedzia dywergencja OBV (cena rośnie, ale kapitał ucieka – ryzyko pułapki!)",
        )

    return score, reasons