import pandas as pd


# =====================================================================
# POMOCNICZE FUNKCJE WEJŚCIOWE I KONWERSJA DANYCH
# =====================================================================

def add_reason(reasons, category, points, text):
    """Dodaje wpis audytowy do listy uzasadnień punktacji."""
    reasons.append({
        "category": category,
        "points": points,
        "text": text
    })


def safe_float(value):
    """Bezpieczna konwersja wartości do typu float."""
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


# =====================================================================
# 1. MULTI-TIMEFRAME TREND (MTF)
# MAX: 25 pkt
# =====================================================================

def score_mtf_trend(analysis):
    score = 0
    reasons = []

    trend_main = str(getattr(analysis, "trend_main", "UNKNOWN"))    # np. D1 / H4
    trend_entry = str(getattr(analysis, "trend_entry", "UNKNOWN"))  # np. H1 / M15
    adx = safe_float(getattr(analysis, "adx_main", None))

    if trend_main in ("UP", "STRONG_UP") and trend_entry in ("UP", "STRONG_UP"):
        score += 20
        add_reason(
            reasons,
            "MTF Trend",
            20,
            "Pełna zgodność trendu wzrostowego na wyższym i niższym interwale"
        )
    elif trend_main in ("UP", "STRONG_UP") and trend_entry == "SIDEWAYS":
        score += 12
        add_reason(
            reasons,
            "MTF Trend",
            12,
            "Wyższy trend wzrostowy, niższy interwał w konsolidacji"
        )
    elif trend_main in ("DOWN", "STRONG_DOWN"):
        score -= 10
        add_reason(
            reasons,
            "MTF Trend",
            -10,
            "Główny trend jest spadkowy — wysokie ryzyko dla pozycji długiej"
        )
    else:
        add_reason(reasons, "MTF Trend", 0, "Brak jednoznacznego trendu MTF")

    # Siła trendu z ADX głównego interwału
    if adx is not None and trend_main in ("UP", "STRONG_UP"):
        if adx >= 25:
            score += 5
            add_reason(reasons, "ADX MTF", 5, f"Silna dynamika głównego trendu (ADX: {adx:.1f})")

    return score, reasons


# =====================================================================
# 2. SPREAD / ATR RATIO (Stosunek spreadu do zmienności)
# MAX: 15 pkt
# =====================================================================

def score_volatility_noise(analysis):
    score = 0
    reasons = []

    spread = safe_float(getattr(analysis, "spread", None))
    atr = safe_float(getattr(analysis, "atr", None))

    if spread is None or atr is None or atr == 0:
        return score, reasons

    # Stosunek spreadu do ATR (%)
    spread_atr_ratio = (spread / atr) * 100

    if spread_atr_ratio < 2.0:
        score += 15
        add_reason(
            reasons,
            "CFD Spread/ATR",
            15,
            f"Doskonała płynność — spread stanowi zaledwie {spread_atr_ratio:.1f}% ATR"
        )
    elif spread_atr_ratio < 5.0:
        score += 8
        add_reason(
            reasons,
            "CFD Spread/ATR",
            8,
            f"Akceptowalny spread względem zmienności ({spread_atr_ratio:.1f}% ATR)"
        )
    elif spread_atr_ratio > 10.0:
        score -= 10
        add_reason(
            reasons,
            "CFD Spread/ATR",
            -10,
            f"Wysoki koszt wejścia/wyjścia — spread zjada {spread_atr_ratio:.1f}% ATR"
        )

    return score, reasons


# =====================================================================
# 3. UKŁAD ŚREDNICH (EMA)
# MAX: 15 pkt
# =====================================================================

def score_ema_alignment(analysis):
    score = 0
    reasons = []

    ema20 = safe_float(getattr(analysis, "ema20", None))
    ema50 = safe_float(getattr(analysis, "ema50", None))
    ema200 = safe_float(getattr(analysis, "ema200", None))

    if None in (ema20, ema50, ema200):
        return score, reasons

    if ema20 > ema50 > ema200:
        score += 15
        add_reason(reasons, "EMA", 15, "Idealny byczy układ średnich EMA20 > EMA50 > EMA200")
    elif ema20 > ema50:
        score += 8
        add_reason(reasons, "EMA", 8, "Krótkoterminowa przewaga kupujących (EMA20 > EMA50)")
    elif ema20 < ema50 < ema200:
        score -= 12
        add_reason(reasons, "EMA", -12, "Niedźwiedzi układ EMA20 < EMA50 < EMA200")

    return score, reasons


# =====================================================================
# 4. MACD & HISTOGRAM DYNAMIKI
# MAX: 15 pkt
# =====================================================================

def score_momentum_macd(analysis):
    score = 0
    reasons = []

    macd = safe_float(getattr(analysis, "macd", None))
    signal = safe_float(getattr(analysis, "macd_signal", None))
    hist_rising = getattr(analysis, "histogram_rising", False)

    if macd is None or signal is None:
        return score, reasons

    if macd > signal and hist_rising:
        score += 15
        add_reason(reasons, "MACD", 15, "MACD powyżej sygnału, przyspieszający momentum")
    elif macd > signal:
        score += 8
        add_reason(reasons, "MACD", 8, "MACD powyżej linii sygnału")
    else:
        score -= 5
        add_reason(reasons, "MACD", -5, "MACD poniżej linii sygnału")

    return score, reasons


# =====================================================================
# 5. RSI REGIME (STREFA TRENDOWA)
# MAX: 10 pkt
# =====================================================================

def score_rsi_regime(analysis):
    score = 0
    reasons = []

    rsi = safe_float(getattr(analysis, "rsi", None))
    if rsi is None:
        return score, reasons

    if 50 <= rsi <= 68:
        score += 10
        add_reason(reasons, "RSI", 10, f"RSI w optymalnej strefie byczej ({rsi:.1f})")
    elif 40 <= rsi < 50:
        score += 5
        add_reason(reasons, "RSI", 5, f"RSI w strefie neutralnej/korekcyjnej ({rsi:.1f})")
    elif rsi > 75:
        score -= 5
        add_reason(reasons, "RSI", -5, f"Wysoce prawdopodobne wyprzedanie/przegrzanie ({rsi:.1f})")
    elif rsi < 35:
        score -= 5
        add_reason(reasons, "RSI", -5, f"Brak siły popytu ({rsi:.1f})")

    return score, reasons


# =====================================================================
# 6. SWAP / CARRY COST
# MAX: 10 pkt
# =====================================================================

def score_swap_carry(analysis):
    score = 0
    reasons = []

    swap_long = safe_float(getattr(analysis, "swap_long", None))

    if swap_long is None:
        return score, reasons

    if swap_long > 0:
        score += 10
        add_reason(reasons, "Swap", 10, f"Dodatni swap dla pozycji long (+{swap_long:.2f} pips/day)")
    elif swap_long == 0:
        score += 5
        add_reason(reasons, "Swap", 5, "Brak kosztów swap (Swap 0)")
    elif swap_long < -10:
        score -= 5
        add_reason(reasons, "Swap", -5, f"Wysoki ujemny swap obciąża pozycję ({swap_long:.2f})")

    return score, reasons


# =====================================================================
# 7. STOCHASTIC FILTER
# MAX: 10 pkt
# =====================================================================

def score_stoch_filter(analysis):
    score = 0
    reasons = []

    k = safe_float(getattr(analysis, "stoch_k", None))
    d = safe_float(getattr(analysis, "stoch_d", None))

    if k is None or d is None:
        return score, reasons

    if k > d and k < 80:
        score += 10
        add_reason(reasons, "Stochastic", 10, f"Bycze ułożenie stochastyczne w bezpiecznej strefie (%K: {k:.1f})")
    elif k > 80:
        score -= 2
        add_reason(reasons, "Stochastic", -2, f"Stochastyk w strefie wykupienia (%K: {k:.1f})")

    return score, reasons


# =====================================================================
# GŁÓWNA FUNKCJA AGREGUJĄCA
# =====================================================================

def calculate_quality_score_cfd(analysis):
    score = 0
    reasons = []

    scorers = [
        score_mtf_trend,
        score_volatility_noise,
        score_ema_alignment,
        score_momentum_macd,
        score_rsi_regime,
        score_swap_carry,
        score_stoch_filter,
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    final_score = max(0, min(100, score))
    return final_score, reasons


def calculate_confidence_CFD(analysis):
    """
    Oblicza poziom pewności (Confidence Score) dla instrumentu CFD.
    Uwzględnia jakość układu (Quality Score), timing wejścia (Entry Score),
    zgodność interwałów (MTF) oraz koszty spreadu względem zmienności (ATR).
    """
    reasons = []

    # 1. POBRANIE BAZOWYCH WYNIKÓW SYSTEMU (QUALITY & ENTRY)
    q_score = safe_float(getattr(analysis, "quality_score", 0)) or 0
    e_score = safe_float(getattr(analysis, "entry_score", 0)) or 0

    # Baza techniczna stanowiona w 80% przez Quality (45%) i Entry (35%)
    base_tech_confidence = (q_score * 0.45) + (e_score * 0.35)
    add_reason(
        reasons,
        "Base Technicals",
        round(base_tech_confidence, 1),
        f"Fundament techniczny CFD (Quality: {q_score:.0f}, Entry: {e_score:.0f})"
    )

    # 2. OCENA STOSUNKU SPREAD / ATR (Wpływ: max +10 / -10 pkt)
    spread = safe_float(getattr(analysis, "spread", None))
    atr = safe_float(getattr(analysis, "atr", None))
    cost_pts = 0

    if spread is not None and atr is not None and atr > 0:
        ratio = (spread / atr) * 100
        if ratio < 2.0:
            cost_pts = 10
            cost_msg = f"Niskie koszty tarcie ({ratio:.1f}% ATR) podnoszą pewność wygranej z dźwignią"
        elif ratio < 5.0:
            cost_pts = 5
            cost_msg = f"Akceptowalny spread względem zmienności ({ratio:.1f}% ATR)"
        elif ratio > 10.0:
            cost_pts = -10
            cost_msg = f"Wysoki spread ({ratio:.1f}% ATR) drastycznie obniża pewność sukcesu"
        else:
            cost_msg = f"Neutralny poziom kosztów spreadu ({ratio:.1f}% ATR)"
    else:
        cost_msg = "Brak danych o spreadzie/ATR (przyjęto 0 pkt)"

    add_reason(reasons, "Cost Impact", cost_pts, cost_msg)

    # 3. ZGODNOŚĆ MULTI-TIMEFRAME (Wpływ: max +10 / -10 pkt)
    trend_main = str(getattr(analysis, "trend_main", "UNKNOWN"))
    trend_entry = str(getattr(analysis, "trend_entry", "UNKNOWN"))
    mtf_pts = 0

    if trend_main in ("UP", "STRONG_UP") and trend_entry in ("UP", "STRONG_UP"):
        mtf_pts = 10
        mtf_msg = "Pełna zgodność byczego trendu na interwale wyższym i wejściowym"
    elif trend_main in ("DOWN", "STRONG_DOWN"):
        mtf_pts = -10
        mtf_msg = "Główny trend jest spadkowy — otwarcie pozycji dążącej pod prąd"
    else:
        mtf_msg = "Mieszane sygnały trendów MTF"

    add_reason(reasons, "MTF Alignment", mtf_pts, mtf_msg)

    # 4. SUMOWANIE I NORMOWANIE WYNIKU
    total_confidence = base_tech_confidence + cost_pts + mtf_pts
    final_confidence = round(max(0.0, min(100.0, total_confidence)), 1)

    # Przypisanie do atrybutów obiektu (dla zachowania spójności z klasą StockAnalysis)
    analysis.confidence_score = final_confidence
    analysis.confidence_pct = int(final_confidence)
    analysis.confidence_reasons = reasons

    return final_confidence, reasons