"""
===========================================
Stock Analyzer - Configuration
===========================================

Większość parametrów strategii znajdują się tutaj.

Zmieniając wartości poniżej możesz łatwo
dostosować sposób analizy bez edytowania kodu.
jeżeli wiesz co robisz, możesz zmienić wartości w tym pliku.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

DB = DATA_DIR / "stocks.db"

#dane do iportu z yahoo finance
DEFAULT_PERIOD = "2y"
DEFAULT_INTERVAL = "1d"

# standardowe wartości do wylicania wskaźników
EMA_FAST = 20
EMA_SLOW = 50
EMA_LONG = 200

RSI_PERIOD = 14

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# =====================================================
# SUPPORT / RESISTANCE - WSPARCIA / OPORY
# =====================================================

# Maksymalna różnica cen tworzących jedną strefę jedna dla wsparć i oporów
ZONE_TOLERANCE = 0.02

# Minimalna liczba testów, aby pokazać strefę
MIN_ZONE_TESTS = 1

# Maksymalna liczba stref na wykresze
MAX_ZONES_ON_CHART = 1

# Liczba testów określająca siłę stref
MEDIUM_ZONE_TESTS = 5
STRONG_ZONE_TESTS = 8


# =====================
# Chart 
# =====================

ZONE_ALPHA_WEAK = 0.20
ZONE_ALPHA_MEDIUM = 0.35
ZONE_ALPHA_STRONG = 0.45
ZONE_ALPHA_NEAREST = 0.70


# =====================================================
# RSI
# =====================================================

RSI_STRONG_OVERSOLD = 25
RSI_OVERSOLD = 35
RSI_GOOD = 45
RSI_IDEAL = 60
RSI_OVERBOUGHT = 70
RSI_STRONG_OVERBOUGHT = 80

# =====================================================
# SCORE - jakość spółki
# =====================================================

MAX_SCORE = 100
# Minimalny score jakości spółki
STRONG_BUY_ENTRY_SCORE = 90
BUY_ENTRY_SCORE = 70
WATCH_ENTRY_SCORE = 50

STRONG_BUY_QUALITY_SCORE = 80
BUY_QUALITY_SCORE = 70

# =====================
# Trading   Signals
# =====================


# Minimalny współczynnik Risk / Reward
MIN_RR = 2.0

# Maksymalna odległość ceny od wsparcia (%)
MAX_SUPPORT_DISTANCE = 3.0  #2.5 dla wąski stop loss i wysoki R/R, 3.0 dla szerszego stop loss i niższego R/R

# Stop Loss (% poniżej wsparcia)
STOP_LOSS_BUFFER = 0.01


# =====================================================
# ENTRY SCORE - Trading ocena momentu wejścia,
# =====================================================


# config.py
ENTRY_POINTS_RR = 35        # Kluczowe: czy ryzyko do zysku ma sens
ENTRY_POINTS_SUPPORT = 25   # Kluczowe: czy nie kupujemy na szczycie (bliskość bazy)
ENTRY_POINTS_MACD = 25      # Wyzwalacz pędu
ENTRY_POINTS_VOLUME = 10    # Potwierdzenie obrotami


