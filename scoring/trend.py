"""
liczymy trend na podstawien EMA
"""

import pandas as pd


def trend_description(trend: str) -> str:
    descriptions = {
        "STRONG_UP": "Silny trend wzrostowy",
        "UP": "Trend wzrostowy",
        "SIDEWAYS": "Trend boczny (konsolidacja)",
        "DOWN": "Trend spadkowy",
        "STRONG_DOWN": "Silny trend spadkowy",
        "UNKNOWN": "Za mało danych na wyliczenie EMA200",
    }
    return descriptions.get(trend, "Nieznany trend")


def get_trend(df, flat_threshold_pct: float = 0.5) -> dict:
    """Liczy trend na podstawie EMA z obsługą sortowania oraz progu konsolidacji.

    :param df: DataFrame z danymi OHLCV i wyliczonymi EMA
    :param flat_threshold_pct: Minimalna zmiana EMA200 w % z ostatnich 20
    sesji, uznawana za trend (domyślnie 0.5%)
    """
    if len(df) < 200:
        return {"trend": "UNKNOWN", "desc": trend_description("UNKNOWN")}


    last = df.iloc[-1]
    prev_20 = df.iloc[-20]  # Stan sprzed 20 sesji (~1 miesiąc)

    # Pobranie cen
    close = last.get("close", last.get("Close"))
    ema20 = last["EMA20"]
    ema50 = last["EMA50"]
    ema200 = last["EMA200"]
    prev_ema200 = prev_20["EMA200"]

    # 2. POPRAWKA 2: Obliczenie procentowego nachylenia (zmiany) EMA200
    # Zapobiega fałszywym sygnałom podczas ruchu płaskiego
    ema200_change_pct = ((ema200 - prev_ema200) / prev_ema200) * 100

    ema200_rising = ema200_change_pct > flat_threshold_pct
    ema200_falling = ema200_change_pct < -flat_threshold_pct
    ema200_flat = abs(ema200_change_pct) <= flat_threshold_pct

    # --- LOGIKA WYZNACZANIA TRENDU ---

    # Jeśli długoterminowa średnia EMA200 jest całkowicie płaska -> Konsolidacja
    if ema200_flat and not (
        ema20 > ema50 > ema200
    ):  # Wyjątek: bardzo silne i czyste ułożenie średnich
        trend_code = "SIDEWAYS"

    # 1. Silny trend wzrostowy: pełna hierarchia + cena nad EMA200 + nachylenie EMA200 w górę
    elif ema20 > ema50 > ema200 and close > ema200 and ema200_rising:
        trend_code = "STRONG_UP"

    # 2. Silny trend spadkowy: pełna hierarchia w dół + cena pod EMA200 + nachylenie EMA200 w dół
    elif ema20 < ema50 < ema200 and close < ema200 and ema200_falling:
        trend_code = "STRONG_DOWN"

    # 3. Zwykły trend wzrostowy: układ krótkich średnich + dodatnie nachylenie EMA200
    elif ema20 > ema50 and close > ema200 and ema200_change_pct > 0:
        trend_code = "UP"

    # 4. Zwykły trend spadkowy: układ krótkich średnich + ujemne nachylenie EMA200
    elif ema20 < ema50 and close < ema200 and ema200_change_pct < 0:
        trend_code = "DOWN"

    # 5. Pozostałe przypadki (przeplatające się średnie) -> Trend boczny
    else:
        trend_code = "SIDEWAYS"

    return {"trend": trend_code, "desc": trend_description(trend_code)}