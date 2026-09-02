import sys
from pathlib import Path

# Dodajemy katalog nadrzędny (../) do ścieżek wyszukiwania modułów Pythona
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import pandas as pd
import config
from database import save_instrument, should_update, _load_fundamentals_from_db
from download import get_instrument_info
from scoring.quality_score import calculate_quality_score
from scoring.trend import get_trend
from scoring.fundamantal_score import calculate_fundamental_score
from scoring.analyst_sentiment import calculate_analyst_sentiment

from signals.entry_score import calculate_entry_score
from signals.signal_generator import SignalGenerator
from signals.trade_levels import calculate_trade_levels
from utils.distance import distance_to_resistance, distance_to_support
from utils.patterns import (
    find_local_minmax_vectorized,
    find_local_nearest_minmax,
)
from utils.resistances import (
    find_nearest_resistance,
    find_resistance_zones,
    rate_resistances,
)
from utils.supports import (
    find_nearest_support,
    find_support_zones,
    rate_supports,
)
from utils.func import _bool_value


class StockAnalysis:

    def __init__(self, symbol: str, df: pd.DataFrame):
        self.symbol = symbol
        self.df = df

        self.price = float(df.iloc[-1]["close"]) if (df is not None and not df.empty) else 0.0
        self.prev_price = None

        self.instrument_info = {}
        self.trend = None

        # Wskaźniki trendu (EMA)
        self.ema20 = None
        self.ema50 = None
        self.ema200 = None

        self.prev_ema20 = None
        self.prev_ema50 = None
        self.prev_ema200 = None
        self.dist_ema20_pct = 0.0

        # Wskaźniki pędu i zmienności
        self.rsi = None
        self.macd = None
        self.macd_signal = None
        self.histogram = None
        self.prev_histogram = None
        self.macd_above_signal = False
        self.histogram_rising = False
        self.atr = None
        self.vol_ratio = 1.0
        self.adx = None

        # Stochastic
        self.stoch_k = None
        self.stoch_d = None
        self.prev_stoch_k = None
        self.prev_stoch_d = None

        # Wstęgi Bollingera
        self.bb_lower = None
        self.bb_middle = None
        self.bb_upper = None
        self.bb_bandwidth = None
        self.bb_squeeze = False

        # OBV
        self.obv = None
        self.obv_rising = False
        self.obv_bullish_div = False
        self.obv_bearish_div = False

        # Geometria rynku / Szczyty
        self.high_20d = None
        self.low_20d = None
        self.ath = None
        self.dist_to_ath_pct = None
        self.is_near_ath = False

        self.minima = []
        self.maxima = []
        self.minmax = []
        self.support_zones = []
        self.resistance_zones = []
        self.rated_supports = []
        self.rated_resistances = []

        self.nearest_support = None
        self.nearest_resistance = None
        self.support_distance = None
        self.resistance_distance = None

        # Ocena techniczna vs fundamentalna
        # self.technical_quality_score = 0
        # self.fundamental_score = 0
        # self.fundamental_details = []

        # Wyniki punktowe łączne
        self.rating = ""
        self.quality_score = 0
        self.quality_reasons = []

        self.entry_score = 0
        self.entry_reasons = []

        # Sygnały transakcyjne i Poziomy Trade
        self.trade_signal = None
        self.stop_loss = None
        self.take_profit = None
        self.risk_reward = None
        self.confidence = 0

        # Pola fundamentalne z bazy danych
        self.target_mean_price = None
        self.recommendation_key = "N/D"
        self.dividend_yield = None
        self.pe_ratio = None
        self.roe = None

        self.fundamental_score = 0
        self.fundamental_reasons = []

        self.analyst_sentiment_score = 0
        self.analyst_sentiment_reasons = []

        self.analyst_upside_pct = None
        self.analyst_target_spread_pct = None

    def fetch_instrument_info(self):
        """Pobiera metadane o spółce."""
        try:
            self.instrument_info = get_instrument_info(self.symbol) or {}
            #if should_update(self.symbol):
            save_instrument(self.instrument_info, symbol=self.symbol)
        except Exception:
            self.instrument_info = {
                "longName": self.symbol,
                "currency": "PLN",
                "country": "PL",
                "sector": "N/A",
                "type": "Akcje",
            }

    def calculate_trend(self):
        """Wyznacza główny trend kierunkowy."""
        self.trend = get_trend(self.df)

    def calculate_indicators(self):
        """Odczytuje przeliczone wskaźniki z DataFrame i przypisuje do pól obiektu."""
        if self.df is None or self.df.empty:
            return

        last_row = self.df.iloc[-1]
        prev_row = self.df.iloc[-2] if len(self.df) > 1 else last_row

        self.prev_price = (
            float(prev_row["close"])
            if "close" in prev_row and not pd.isna(prev_row["close"])
            else None
        )

        # 1. EMA
        for ema_name in ["EMA20", "EMA50", "EMA200"]:
            val = last_row.get(ema_name)
            setattr(
                self,
                ema_name.lower(),
                float(val) if val is not None and not pd.isna(val) else None,
            )

            prev_val = prev_row.get(ema_name)
            prev_attr = f"prev_{ema_name.lower()}"
            setattr(
                self,
                prev_attr,
                (
                    float(prev_val)
                    if prev_val is not None and not pd.isna(prev_val)
                    else getattr(self, ema_name.lower())
                ),
            )

        if self.price and self.ema20 and self.ema20 > 0:
            self.dist_ema20_pct = ((self.price - self.ema20) / self.ema20) * 100.0
        else:
            self.dist_ema20_pct = 0.0

        # 2. RSI
        rsi_val = last_row.get("RSI")
        self.rsi = float(rsi_val) if rsi_val is not None and not pd.isna(rsi_val) else None

        # 3. MACD
        self.macd = float(last_row.get("MACD", 0.0)) if not pd.isna(last_row.get("MACD")) else None
        self.macd_signal = float(last_row.get("MACD_signal", 0.0)) if not pd.isna(last_row.get("MACD_signal")) else None
        self.histogram = float(last_row.get("MACD_hist", 0.0)) if not pd.isna(last_row.get("MACD_hist")) else None

        prev_hist = prev_row.get("MACD_hist")
        self.prev_histogram = float(prev_hist) if prev_hist is not None and not pd.isna(prev_hist) else 0.0

        self.macd_above_signal = self.macd > self.macd_signal
        self.histogram_rising = self.histogram > self.prev_histogram

        # 4. ATR, Vol Ratio, ADX
        self.atr = float(last_row["ATR"]) if "ATR" in last_row and not pd.isna(last_row["ATR"]) else None
        self.vol_ratio = float(last_row["vol_ratio"]) if "vol_ratio" in last_row and not pd.isna(last_row["vol_ratio"]) else 1.0
        self.adx = float(last_row["ADX"]) if "ADX" in last_row and not pd.isna(last_row["ADX"]) else None

        # 5. STOCHASTIC
        self.stoch_k = float(last_row["STOCH_k"]) if "STOCH_k" in last_row and not pd.isna(last_row["STOCH_k"]) else None
        self.stoch_d = float(last_row["STOCH_d"]) if "STOCH_d" in last_row and not pd.isna(last_row["STOCH_d"]) else None
        self.prev_stoch_k = float(prev_row["STOCH_k"]) if "STOCH_k" in prev_row and not pd.isna(prev_row["STOCH_k"]) else None
        self.prev_stoch_d = float(prev_row["STOCH_d"]) if "STOCH_d" in prev_row and not pd.isna(prev_row["STOCH_d"]) else None

        # 6. BOLLINGER BANDS
        self.bb_lower = float(last_row["bb_lower"]) if "bb_lower" in last_row and not pd.isna(last_row["bb_lower"]) else None
        self.bb_upper = float(last_row["bb_upper"]) if "bb_upper" in last_row and not pd.isna(last_row["bb_upper"]) else None
        self.bb_middle = float(last_row["bb_middle"]) if "bb_middle" in last_row and not pd.isna(last_row["bb_middle"]) else None
        self.bb_bandwidth = float(last_row["bb_bandwidth"]) if "bb_bandwidth" in last_row and not pd.isna(last_row["bb_bandwidth"]) else None
        #self.bb_squeeze = bool(last_row.get("bb_squeeze", False))
        self.bb_squeeze = _bool_value(last_row.get("bb_squeeze", False), default=False)

        # 7. OBV
        self.obv = float(last_row["OBV"]) if "OBV" in last_row and not pd.isna(last_row["OBV"]) else None
        self.obv_rising = _bool_value(last_row.get("obv_rising", False), default=False)
        self.obv_bullish_div = _bool_value(last_row.get("obv_bullish_div", False), default=False)
        self.obv_bearish_div = _bool_value(last_row.get("obv_bearish_div", False), default=False)

        # 8. Geometria / ATH
        self.high_20d = float(last_row["rolling_high_20"]) if "rolling_high_20" in last_row and not pd.isna(last_row["rolling_high_20"]) else None
        self.low_20d = float(last_row["rolling_low_20"]) if "rolling_low_20" in last_row and not pd.isna(last_row["rolling_low_20"]) else None
        self.ath = float(last_row["ATH"]) if "ATH" in last_row and not pd.isna(last_row["ATH"]) else None
        self.dist_to_ath_pct = float(last_row["dist_to_ath_pct"]) if "dist_to_ath_pct" in last_row and not pd.isna(last_row["dist_to_ath_pct"]) else None
        self.is_near_ath = _bool_value(last_row.get("is_near_ath", False), default=False)

    def calculate_levels(self):
        """Wyznacza lokalne ekstrema oraz strefy wsparć i oporów."""
        extrema = find_local_minmax_vectorized(self.df, window_size=2)
        self.minima = [e for e in extrema if e["type"] == "minimum"]
        self.maxima = [e for e in extrema if e["type"] == "maximum"]
        self.minmax = find_local_nearest_minmax(self.df)

        self.support_zones = find_support_zones(self.minima)
        self.rated_supports = rate_supports(self.support_zones)
        self.nearest_support = find_nearest_support(self.price, self.rated_supports)

        self.resistance_zones = find_resistance_zones(self.maxima)
        self.rated_resistances = rate_resistances(self.resistance_zones)
        self.nearest_resistance = find_nearest_resistance(self.price, self.rated_resistances)

        self.support_distance = distance_to_support(self.price, self.nearest_support)
        self.resistance_distance = distance_to_resistance(self.price, self.nearest_resistance)

    def calculate_trade_levels(self):
        """Wyznacza Stop Loss, Take Profit oraz wskaźnik Risk/Reward."""
        (
            self.stop_loss,
            self.take_profit,
            self.risk_reward,
        ) = calculate_trade_levels(self)

    def calculate_fundamental_score(self):
        """Wylicza Fundamental Score 0-100."""
        (
            self.fundamental_score,
            self.fundamental_reasons
        ) = calculate_fundamental_score(self)

    # def calculate_fundamental_score(self):
    #     """Pobiera dane fundamentalne z bazy i wylicza Fundamental Score."""
    #     data = _load_fundamentals_from_db(self.symbol)

    #     if not data:
    #         return

    #     self.target_mean_price = data.get("targetMeanPrice")
    #     self.recommendation_key = data.get("recommendationKey", "N/D")
    #     self.dividend_yield = data.get("dividendYield")
    #     self.pe_ratio = data.get("trailingPE")
    #     self.roe = data.get("returnOnEquity")

    #     score = 0
    #     self.fundamental_details = []

    #     # Ocena P/E
    #     if self.pe_ratio and 0 < self.pe_ratio < 15:
    #         score += 25
    #         self.fundamental_details.append("Niska wycena P/E (<15)")
    #     elif self.pe_ratio and self.pe_ratio < 25:
    #         score += 15
    #         self.fundamental_details.append("Umiarkowana wycena P/E (<25)")

    #     # Ocena ROE
    #     if self.roe and self.roe >= 0.15:
    #         score += 25
    #         self.fundamental_details.append("Wysoki ROE (>=15%)")

    #     # Dywidenda
    #     if self.dividend_yield and self.dividend_yield >= 0.03:
    #         score += 25
    #         div_pct = self.dividend_yield * 100 if self.dividend_yield < 1.0 else self.dividend_yield
    #         self.fundamental_details.append(f"Atrakcyjna dywidenda ({div_pct:.1f}%)")

    #     # Rekomendacje
    #     if str(self.recommendation_key).lower() in ["buy", "strong_buy"]:
    #         score += 25
    #         self.fundamental_details.append("Rekomendacja KUPUJ")

    #     self.fundamental_score = score

    def calculate_analyst_sentiment(self):
        """Wylicza Analyst Sentiment Score 0-100."""
        (
            self.analyst_sentiment_score,
            self.analyst_sentiment_reasons
        ) = calculate_analyst_sentiment(self)

    def calculate_quality_score(self):
        """Wylicza wyłącznie techniczny Quality Score 0–100."""
        (
            self.quality_score,
            self.quality_reasons
        ) = calculate_quality_score(self)

        #self.technical_quality_score = self.quality_score

    def calculate_entry_score(self):
        """Wylicza punktację momentu wejścia."""
        self.entry_score, self.entry_reasons = calculate_entry_score(self)

    def calculate_signal(self):
        """Generuje ostateczny sygnał handlowy."""
        generator = SignalGenerator(self)
        self.trade_signal = generator.generate()

    def calculate_confidence(self):
        """Oblicza poziom pewności sygnału."""
        self.confidence = (self.quality_score + self.entry_score) / 2

    def debug_print_analysis(self):
        """Drukuje podsumowanie kontrolne analizowanego waloru."""
        print("=" * 50)
        print(f"--- SPRAWDZENIE DANYCH DLA: {getattr(self, 'symbol', 'N/A')} ---")
        print(f"Cena zamknięcia:      {self.price}")
        print(
            f"ATH:                  {getattr(self, 'ath', 'Brak')} (Czy"
            f" blisko ATH? {getattr(self, 'is_near_ath', False)})"
        )

        print("\n--- WSKAŹNIK OBV ---")
        print(f"OBV:                  {getattr(self, 'obv', 'Brak')}")
        print(f"Czy OBV rośnie?:      {getattr(self, 'obv_rising', False)}")
        print(f"Bycza Dywergencja?:   {getattr(self, 'obv_bullish_div', False)}")

        print("\n--- GEOMETRIA (Wsparcie / Opór) ---")
        supp = getattr(self, "nearest_support", None)
        res = getattr(self, "nearest_resistance", None)
        touches_cnt = supp.get("touches", 1) if supp else 0
        print(
            f"Najbliższe wsparcie:  {supp.get('price') if supp else 'Brak'} (Liczba"
            f" testów: {touches_cnt})"
        )
        print(f"Najbliższy opór:     {res.get('price') if res else 'Brak'}")

        print("\n--- POZIOMY TRANSAKCYJNE ---")
        print(f"Stop Loss (SL):       {getattr(self, 'stop_loss', 'Brak')}")
        print(f"Take Profit (TP):     {getattr(self, 'take_profit', 'Brak')}")
        print(f"Risk / Reward (R/R):  {getattr(self, 'risk_reward', 'Brak')}")
        print("=" * 50)

    def check_nulls(self):
        """Wypisuje podsumowanie wszystkich pól i kolumn, które mają wartość None / NaN."""
        print("\n" + "=" * 50)
        print(f"🔍 AUDYT BRAKÓW DANYCH (NULL / NaN): {self.symbol}")
        print("=" * 50)

        found_nulls = False

        # 1. Sprawdzenie atrybutów instancji
        print("📌 Atrybuty obiektu:")
        for attr, val in vars(self).items():
            if attr == "df":
                continue  # Ramkę df sprawdzamy osobno poniżej

            if val is None or (isinstance(val, float) and pd.isna(val)):
                print(f"  ❌ {attr:<25} : {val}")
                found_nulls = True
            elif isinstance(val, dict):
                for dict_k, dict_v in val.items():
                    if dict_v is None or (isinstance(dict_v, float) and pd.isna(dict_v)):
                        print(f"  ❌ {attr}['{dict_k}'] : {dict_v}")
                        found_nulls = True

        if not found_nulls:
            print("  ✅ Wszystkie kluczowe atrybuty posiadają wartości.")

        # 2. Sprawdzenie kolumn w df
        if hasattr(self, "df") and self.df is not None:
            df_nulls = self.df.isna().sum()
            missing_cols = df_nulls[df_nulls > 0]

            print("\n📌 Kolumny w ramce df z wartościami NaN:")
            if not missing_cols.empty:
                for col_name, count in missing_cols.items():
                    print(f"  ⚠️ {col_name:<20} : {count} pustych wierszy / {len(self.df)}")
            else:
                print("  ✅ Ramka danych df nie posiada braków (NaN).")

        print("=" * 50 + "\n")

    def run(self):
        """Główna metoda wykonująca pełną analizę w odpowiedniej sekwencji."""
        self.fetch_instrument_info()
        self.calculate_trend()
        self.calculate_indicators()
        self.calculate_levels()
        
        # Prawidłowa kolejność: najpierw wczytanie fundamentów, potem łączny jakość
        self.calculate_fundamental_score()
        self.calculate_analyst_sentiment()

        self.calculate_quality_score()
        
        self.calculate_trade_levels()
        self.calculate_entry_score()
        self.calculate_signal()
        self.calculate_confidence()
        return self