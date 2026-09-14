import os
import sys
import io
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import mplfinance as mpf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import *


class ChartBuilder:

    def __init__(self, analysis, days: int = None):
        self.analysis = analysis
        
        if days and hasattr(analysis, "df") and analysis.df is not None:
            self.df = analysis.df.tail(days).copy()
        else:
            self.df = analysis.df.copy()

        self.fig = None
        self.ax = None
        self.ax_volume = None
        self.addplots = []
        self._has_subpanel = False

    def add_ema(self):
        """Dodaje średnie EMA do głównego wykresu (Panel 0)."""
        if "EMA20" in self.df.columns and self.df["EMA20"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["EMA20"].fillna(np.nan).astype(float), panel=0, width=1, color="orange", label="EMA20")
            )
        if "EMA50" in self.df.columns and self.df["EMA50"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["EMA50"].fillna(np.nan).astype(float), panel=0, width=1, color="blue", label="EMA50")
            )
        if "EMA200" in self.df.columns and self.df["EMA200"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["EMA200"].fillna(np.nan).astype(float), panel=0, width=1.5, color="red", label="EMA200")
            )

    def add_SMA20(self):
        """Dodaje średnią prostą wolumenu SMA20 na panelu wolumenu (Panel 1)."""
        if "vol_sma20" in self.df.columns and self.df["vol_sma20"].notna().any():
            self.addplots.append(
                mpf.make_addplot(
                    self.df["vol_sma20"].fillna(np.nan).astype(float),
                    panel=1,
                    width=1,
                    color="#2563eb",
                    linestyle="--",
                    ylabel="Vol",
                )
            )

    def add_bollinger_bands(self, period: int = 20, std_dev: int = 2):
        """Dodaje Wstęgi Bollingera na głównym wykresie (Panel 0). Oblicza je dynamicznie, jeśli brakuje ich w DF."""
        if "bb_upper" not in self.df.columns or not self.df["bb_upper"].notna().any():
            if "Close" in self.df.columns:
                sma = self.df["Close"].rolling(window=period).mean()
                rstd = self.df["Close"].rolling(window=period).std()
                self.df["bb_upper"] = sma + (rstd * std_dev)
                self.df["bb_lower"] = sma - (rstd * std_dev)
                self.df["bb_middle"] = sma

        if "bb_upper" in self.df.columns and self.df["bb_upper"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["bb_upper"].fillna(np.nan).astype(float), panel=0, width=0.9, color="#8b5cf6", linestyle="--")
            )
            self.addplots.append(
                mpf.make_addplot(self.df["bb_lower"].fillna(np.nan).astype(float), panel=0, width=0.9, color="#8b5cf6", linestyle="--")
            )
            if "bb_middle" in self.df.columns and self.df["bb_middle"].notna().any():
                self.addplots.append(
                    mpf.make_addplot(self.df["bb_middle"].fillna(np.nan).astype(float), panel=0, width=0.7, color="gray", linestyle=":")
                )

    def add_rsi(self, period: int = 14):
        """Dodaje oscylator RSI w osobnym podwykresie (Panel 2)."""
        if "RSI" not in self.df.columns or not self.df["RSI"].notna().any():
            if "Close" in self.df.columns:
                delta = self.df["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                self.df["RSI"] = 100 - (100 / (1 + rs))

        if "RSI" in self.df.columns and self.df["RSI"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["RSI"].fillna(np.nan).astype(float), panel=2, color="#7c3aed", width=1.2, ylabel="RSI")
            )
            self._has_subpanel = True

    def add_macd(self):
        """Dodaje MACD w osobnym podwykresie (Panel 2)."""
        if "MACD" in self.df.columns and "MACD_signal" in self.df.columns and self.df["MACD"].notna().any():
            self.addplots.append(
                mpf.make_addplot(self.df["MACD"].fillna(np.nan).astype(float), panel=2, color="blue", width=1.0, ylabel="MACD")
            )
            self.addplots.append(
                mpf.make_addplot(self.df["MACD_signal"].fillna(np.nan).astype(float), panel=2, color="orange", width=1.0)
            )
            if "MACD_hist" in self.df.columns:
                colors_hist = ["#2ea043" if val >= 0 else "#f85149" for val in self.df["MACD_hist"].fillna(0)]
                self.addplots.append(
                    mpf.make_addplot(self.df["MACD_hist"].fillna(np.nan).astype(float), type="bar", panel=2, color=colors_hist, alpha=0.5)
                )
            self._has_subpanel = True

    def create(self):
        if self.df is None or self.df.empty:
            return

        self.df = self.df.fillna(value=np.nan)
        for col in self.df.columns:
            if self.df[col].dtype == "object":
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # Dynamiczne dopasowanie proporcji paneli w zależności od tego, czy jest podwykres (RSI/MACD)
        ratios = (4, 1.2, 1.3) if self._has_subpanel else (4, 1.2)

        self.fig, axlist = mpf.plot(
            self.df,
            type="candle",
            style="yahoo",
            volume=True,
            ylabel_lower="Vol",
            addplot=self.addplots,
            title=f"\n{self.analysis.symbol}",
            returnfig=True,
            figsize=(14, 7),
            panel_ratios=ratios
        )

        self.ax = axlist[0]
        padding_candles = int(len(self.df) * 0.05) + 5
        self.ax.set_xlim(-1, len(self.df) + padding_candles)

        if len(axlist) > 1:
            self.ax_volume = axlist[2]
            self.ax_volume.set_xlim(-1, len(self.df) + padding_candles)
            self.ax_volume.yaxis.set_major_formatter(
                ticker.FuncFormatter(lambda x, p: f'{x*1e-6:.1f}M' if x >= 1e6 else f'{x*1e-3:.0f}k')
            )

        # Linie 70/30 dla RSI
        if self._has_subpanel and len(axlist) > 3:
            ax_sub = axlist[3]
            # Sprawdzenie czy panel dotyczy RSI
            if any(ap.get('ylabel') == 'RSI' for ap in self.addplots):
                ax_sub.axhline(70, color='red', linestyle=':', alpha=0.6, linewidth=0.8)
                ax_sub.axhline(30, color='green', linestyle=':', alpha=0.6, linewidth=0.8)
                ax_sub.set_ylim(0, 100)

        info = getattr(self.analysis, "instrument_info", {})
        long_name = info.get("longName", self.analysis.symbol)
        
        atr_val = getattr(self.analysis, "atr", None)
        atr_str = f" | ATR: {atr_val:.2f}" if atr_val is not None else ""

        self.fig.text(
            x=0.15, y=0.88, s=f"{long_name}{atr_str}", fontsize=10, style='italic', color='dimgray'
        )

    def add_trade_levels(self):
        if self.ax is None:
            return

        tp = getattr(self.analysis, "take_profit", None)
        sl = getattr(self.analysis, "stop_loss", None)
        last_x = len(self.df) - 1

        if tp is not None:
            self.ax.axhline(tp, linestyle="--", linewidth=1.2, color="#16a34a", alpha=0.8)
            self.ax.text(last_x, tp, f"  TP: {tp:.2f}", color="#16a34a", fontsize=8, fontweight="bold", va="center")

        if sl is not None:
            self.ax.axhline(sl, linestyle="--", linewidth=1.2, color="#dc2626", alpha=0.8)
            self.ax.text(last_x, sl, f"  SL: {sl:.2f}", color="#dc2626", fontsize=8, fontweight="bold", va="center")

    def add_support_zones(self):
        self._draw_zones(
            getattr(self.analysis, "support_zones", []),
            getattr(self.analysis, "nearest_support", None),
            "lightgreen", "green", "SUP",
        )

    def add_resistance_zones(self):
        self._draw_zones(
            getattr(self.analysis, "resistance_zones", []),
            getattr(self.analysis, "nearest_resistance", None),
            "lightcoral", "red", "RES",
        )

    def add_current_price(self):
        if self.ax is None:
            return

        price = self.analysis.price
        self.ax.axhline(price, linestyle="--", linewidth=1.5, color="#2563eb", alpha=0.8)
        self.ax.text(
            len(self.df) - 1, price, f"  Cena: {price:.2f}",
            color="#2563eb", fontsize=9, fontweight="bold", va="center"
        )

    def add_summary_panel(self):
        """Dodaje blok podsumowania punktowego na dole wykresu (przydatne przy podglądzie)."""
        if self.fig is None:
            return

        q_score = getattr(self.analysis, "quality_score", 0)
        e_score = getattr(self.analysis, "entry_score", 0)
        signal = getattr(self.analysis, "trade_signal", "NEUTRAL")

        summary_text = f"Quality Score: {q_score}/100  |  Entry Score: {e_score}/100  |  Sygnał: {signal}"
        self.fig.text(
            0.5, 0.01, summary_text,
            ha="center", fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1")
        )

    def show(self, block=False):
        """Wyświetla okno wykresu w interaktywnej konsoli / GUI."""
        if self.fig is not None:
            plt.show(block=block)

    def _draw_zones(self, zones, nearest, fill_color, highlight_color, label):
        if self.ax is None:
            return

        min_tests = globals().get("MIN_ZONE_TESTS", 2)
        max_zones = globals().get("MAX_ZONES_ON_CHART", 5)

        _zones = [z for z in zones if z.get("touches", 0) >= min_tests]
        _zones = sorted(_zones, key=lambda z: z.get("last_test", ""), reverse=True)[:max_zones]

        if nearest and nearest.get("price") is not None and nearest not in _zones:
            _zones.append(nearest)

        last_x = len(self.df) - 1

        for zone in _zones:
            if not zone or "prices" not in zone or not zone["prices"]:
                continue
            prices = [p for p in zone["prices"] if p is not None]
            if not prices:
                continue

            low, high = min(prices), max(prices)
            tests = zone.get("touches", 1)

            is_nearest = nearest and nearest.get("price") is not None and zone.get("price") == nearest.get("price")
            color = highlight_color if is_nearest else fill_color
            alpha = 0.35 if is_nearest else 0.15

            self.ax.axhspan(low, high, color=color, alpha=alpha, linewidth=1.0 if is_nearest else 0)

            zone_price = zone.get("price")
            if zone_price:
                self.ax.text(last_x, zone_price, f" {label} ({tests}x)", fontsize=8, color=highlight_color if is_nearest else "black", va="center")

    def save_to_buffer(self) -> io.BytesIO:
        if self.fig is None:
            raise ValueError("Wykres nie został wygenerowany.")

        buf = io.BytesIO()
        self.fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        plt.close(self.fig)
        buf.seek(0)
        return buf