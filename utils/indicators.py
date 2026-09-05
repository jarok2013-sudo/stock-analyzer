"""
wyliczenie wskaźników i dodanie kolumn wskaźników (indicators) do df
"""
import numpy as np
import pandas as pd
import pandas_ta as ta

# wartości do wyliczania wskaźników
from config import EMA_FAST, EMA_LONG, EMA_SLOW, MACD_FAST, MACD_SIGNAL, MACD_SLOW, RSI_PERIOD


def add_ema(df: pd.DataFrame) -> pd.DataFrame:
    """EMA średnie ceny z 20, 50 i 200 sesji"""
    df["EMA20"] = ta.ema(df["close"], length=EMA_FAST)
    df["EMA50"] = ta.ema(df["close"], length=EMA_SLOW)
    df["EMA200"] = ta.ema(df["close"], length=EMA_LONG)
    return df


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    macd_df = ta.macd(
        df["close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL
    )

    if macd_df is not None:
        macd_df.columns = ["MACD", "MACD_hist", "MACD_signal"]
        df = pd.concat([df, macd_df], axis=1)

    return df


def add_atr(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    df["ATR"] = ta.atr(
        high=df["high"], low=df["low"], close=df["close"], length=length
    )
    return df


def add_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    vol_col = "volume" if "volume" in df.columns else "Volume"
    df["vol_sma20"] = ta.sma(df[vol_col], length=period)
    df["vol_ratio"] = df[vol_col] / df["vol_sma20"].replace(0, np.nan)
    return df


def add_bollinger_bands(
    df: pd.DataFrame, length: int = 20, std: float = 2.0
) -> pd.DataFrame:
    # Wyliczenie wstęg
    bb = ta.bbands(df["close"], length=length, std=std)

    if bb is not None and not bb.empty:
        # Prawidłowe przypisanie 5 kolumn zwracanych przez pandas_ta
        # (BBL, BBM, BBU, BBB, BBP)
        bb.columns = [
            "bb_lower",
            "bb_middle",
            "bb_upper",
            "bb_bandwidth",
            "bb_percent",
        ]
        df = pd.concat([df, bb], axis=1)

        # 20-dniowe minimum bandwidth z POPRZEDNICH dni (przesunięte o 1 dzień)
        past_min_bandwidth = (
            df["bb_bandwidth"].shift(1).rolling(window=length).min()
        )

        # Squeeze: Aktualna szerokość wstęgi <= 105% minimum z ostatnich 'length' dni
        df["bb_squeeze"] = df["bb_bandwidth"] <= (past_min_bandwidth * 1.05)
    else:
        df["bb_lower"] = None
        df["bb_middle"] = None
        df["bb_upper"] = None
        df["bb_bandwidth"] = None
        df["bb_percent"] = None
        df["bb_squeeze"] = False

    return df



def add_adx(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    adx = ta.adx(high=df["high"], low=df["low"], close=df["close"], length=length)
    if adx is not None:
        df["ADX"] = adx.iloc[:, 0]
        df["DIP"] = adx.iloc[:, 1]
        df["DIN"] = adx.iloc[:, 2]
    return df


def add_stoch(df: pd.DataFrame, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    stoch = ta.stoch(high=df["high"], low=df["low"], close=df["close"], k=k, d=d, smooth_k=smooth_k)
    if stoch is not None:
        df["STOCH_k"] = stoch.iloc[:, 0]
        df["STOCH_d"] = stoch.iloc[:, 1]
    return df


# =====================================================================
# PEŁNY MODUŁ OBV + DYWERGENCJE (Rozbudowany pod quality_score)
# =====================================================================
def add_obv(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    1. Oblicza surowy OBV przy użyciu pandas_ta.
    2. Dodaje średnią EMA z OBV oraz dynamikę (OBV_Slope).
    3. Wykrywa trend oraz Dywergencję Byczą i Niedźwiedzią.
    """
    vol_col = "volume" if "volume" in df.columns else "Volume"

    # 1. Obliczenie surowego OBV z pandas_ta
    df["OBV"] = ta.obv(close=df["close"], volume=df[vol_col])

    # Jeśli dane są niewystarczające, wracamy z wartościami domyślnymi
    if df["OBV"] is None or len(df) < window:
        df["OBV_EMA"] = np.nan
        df["OBV_Slope"] = 0.0
        df["obv_rising"] = False
        df["obv_bullish_div"] = False
        df["obv_bearish_div"] = False
        return df

    # 2. Sygnał i nachylenie
    df["OBV_EMA"] = ta.ema(df["OBV"], length=20)
    df["OBV_Slope"] = df["OBV"].diff(5)
    
    # Trend: czy OBV jest powyżej swojej 5-okresowej średniej
    obv_sma5 = ta.sma(df["OBV"], length=5)
    df["obv_rising"] = df["OBV"] > obv_sma5

    # 3. Wykrywanie Dywergencji
    df["obv_bullish_div"] = False
    df["obv_bearish_div"] = False

    closes = df["close"].to_numpy()
    obv_vals = df["OBV"].to_numpy()
    n = len(df)
    half_w = max(2, window // 2)

    for i in range(window, n):
        sub_price = closes[i - window : i + 1]
        sub_obv = obv_vals[i - window : i + 1]

        # Bycza dywergencja: niższy dołek ceny, wyższy dołek OBV
        price_min_idx = np.argmin(sub_price)
        if price_min_idx >= half_w:
            if sub_price[price_min_idx] < sub_price[0] and sub_obv[price_min_idx] > sub_obv[0]:
                df.iloc[i, df.columns.get_loc("obv_bullish_div")] = True

        # Niedźwiedzia dywergencja: wyższy szczyt ceny, niższy szczyt OBV
        price_max_idx = np.argmax(sub_price)
        if price_max_idx >= half_w:
            if sub_price[price_max_idx] > sub_price[0] and sub_obv[price_max_idx] < sub_obv[0]:
                df.iloc[i, df.columns.get_loc("obv_bearish_div")] = True

    return df


def add_support_resistance_levels(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    df["rolling_high_20"] = df["high"].rolling(window=window).max()
    df["rolling_low_20"] = df["low"].rolling(window=window).min()
    return df


def add_ath_indicators(df: pd.DataFrame, ath_buffer_pct: float = 2.5) -> pd.DataFrame:
    df["ATH"] = df["high"].cummax()
    df["dist_to_ath_pct"] = ((df["ATH"] - df["close"]) / df["ATH"]) * 100
    df["is_near_ath"] = df["dist_to_ath_pct"] <= ath_buffer_pct
    return df


# --- Główna funkcja zbiorcza ---
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Dodaje komplet wskaźników do ramki danych."""
    df = add_ema(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_atr(df)
    df = add_volume_ratio(df)

    df = add_bollinger_bands(df)
    df = add_adx(df)
    df = add_stoch(df)
    df = add_obv(df)  # Zawiera wyliczenie OBV oraz dywergencji
    df = add_support_resistance_levels(df)
    df = add_ath_indicators(df)

    return df