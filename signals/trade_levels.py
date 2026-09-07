import sys
import pandas as pd
from pathlib import Path


# ----------------------------------------------------------------------
# IMPORTY PROJEKTOWE
# ----------------------------------------------------------------------

parent_dir = Path(__file__).resolve().parent.parent

if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from config import STOP_LOSS_BUFFER, MIN_RR


# ----------------------------------------------------------------------
# TRADE LEVELS
# ----------------------------------------------------------------------

def calculate_trade_levels(analysis, atr_multiplier: float = 0.5):
    """
    Wyznacza poziomy transakcji:

    SL:
        Najbliższe istotne wsparcie poniżej ceny
        minus bufor ATR.

    TP1:
        Najbliższy rzeczywisty opór powyżej ceny.

    TP2:
        Najbliższy rzeczywisty opór spełniający MIN_RR.
        Jeżeli taki opór nie istnieje, TP2 jest wyznaczany
        matematycznie na podstawie docelowego RR.

    Zwraca słownik zawierający:
        stop_loss
        take_profit_1
        take_profit_2
        rr_tp1
        rr_tp2
        tp1_source
        tp2_source
    """

    price = float(analysis.price)

    support = analysis.nearest_support
    nearest_resistance = analysis.nearest_resistance

    rated_resistances = getattr(
        analysis,
        "rated_resistances",
        []
    )

    atr = getattr(analysis, "atr", None)

    # ------------------------------------------------------------------
    # 1. BUFOR ATR
    # ------------------------------------------------------------------

    if atr is not None and not pd.isna(atr) and atr > 0:
        buffer_amount = float(atr) * atr_multiplier
    else:
        buffer_amount = price * STOP_LOSS_BUFFER

    # ------------------------------------------------------------------
    # 2. STOP LOSS
    # ------------------------------------------------------------------

    if (
        support is not None
        and support.get("price") is not None
        and support["price"] < price
    ):
        stop_loss = float(support["price"]) - buffer_amount

    else:
        # Fallback, jeżeli nie znaleziono poprawnego wsparcia
        stop_loss = price - (buffer_amount * 2)

    # ------------------------------------------------------------------
    # 3. RYZYKO
    # ------------------------------------------------------------------

    risk_amount = price - stop_loss

    if risk_amount <= 0:
        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit_1": None,
            "take_profit_2": None,
            "rr_tp1": 0.0,
            "rr_tp2": 0.0,
            "tp1_source": None,
            "tp2_source": None,
        }

    # ------------------------------------------------------------------
    # 4. TP1 - NAJBLIŻSZY RZECZYWISTY OPÓR
    # ------------------------------------------------------------------

    take_profit_1 = None
    rr_tp1 = 0.0

    if (
        nearest_resistance is not None
        and nearest_resistance.get("price") is not None
    ):
        resistance_price = float(
            nearest_resistance["price"]
        )

        if resistance_price > price:
            take_profit_1 = resistance_price

            reward_tp1 = take_profit_1 - price
            rr_tp1 = round(
                reward_tp1 / risk_amount,
                2
            )

    tp1_source = "RESISTANCE" if take_profit_1 is not None else None

    # ------------------------------------------------------------------
    # 5. SZUKANIE OPORÓW SPEŁNIAJĄCYCH MIN_RR
    # ------------------------------------------------------------------

    valid_resistances = []

    if isinstance(rated_resistances, list):

        for level in rated_resistances:

            if not isinstance(level, dict):
                continue

            resistance_price = level.get("price")

            if resistance_price is None:
                continue

            try:
                resistance_price = float(resistance_price)
            except (TypeError, ValueError):
                continue

            # Opór musi znajdować się powyżej ceny
            if resistance_price <= price:
                continue

            reward = resistance_price - price

            resistance_rr = reward / risk_amount

            # Interesują nas tylko opory spełniające MIN_RR
            if resistance_rr >= MIN_RR:

                valid_resistances.append(
                    {
                        "price": resistance_price,
                        "rr": resistance_rr,
                        "level": level,
                    }
                )

    # ------------------------------------------------------------------
    # 6. TP2
    # ------------------------------------------------------------------

    if valid_resistances:

        # Najbliższy opór spełniający wymagane RR
        selected_resistance = min(
            valid_resistances,
            key=lambda x: x["price"]
        )

        take_profit_2 = selected_resistance["price"]

        reward_tp2 = take_profit_2 - price

        rr_tp2 = round(
            reward_tp2 / risk_amount,
            2
        )

        tp2_source = "RESISTANCE"

    else:

        # Brak rzeczywistego oporu spełniającego MIN_RR.
        #
        # W takim przypadku tworzymy matematyczny cel.
        target_rr = max(2.5, MIN_RR)

        take_profit_2 = price + (
            risk_amount * target_rr
        )

        rr_tp2 = round(
            (take_profit_2 - price) / risk_amount,
            2
        )

        tp2_source = "RISK_REWARD"

    # ------------------------------------------------------------------
    # 7. WYNIK
    # ------------------------------------------------------------------

    return {
        "stop_loss": round(stop_loss, 2),

        "take_profit_1": (
            round(take_profit_1, 2)
            if take_profit_1 is not None
            else None
        ),

        "take_profit_2": round(take_profit_2, 2),

        "rr_tp1": rr_tp1,

        "rr_tp2": rr_tp2,

        "tp1_source": tp1_source,

        "tp2_source": tp2_source,
    }