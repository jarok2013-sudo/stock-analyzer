import sys
import pandas as pd
from pathlib import Path
# Dodajemy katalog nadrzędny (../) do ścieżek wyszukiwania modułów Pythona
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
from config import STOP_LOSS_BUFFER, MIN_RR  # Zachowujemy jako fallback gdyby ATR nie był dostępny


def calculate_trade_levels(analysis, atr_multiplier: float = 0.5):
    price = analysis.price
    support = analysis.nearest_support
    resistance = analysis.nearest_resistance
    atr = getattr(analysis, "atr", None)

    stop_loss = None
    take_profit = None
    rr = None

    # 1. Bufor kwotowy (ATR lub % z configu)
    if atr is not None and not pd.isna(atr) and atr > 0:
        buffer_amount = atr * atr_multiplier
    else:
        buffer_amount = price * STOP_LOSS_BUFFER

    # 2. Wyznaczenie Stop Loss
    if support is not None and support.get("price") is not None and support["price"] < price:
        stop_loss = support["price"] - buffer_amount
    else:
        stop_loss = price - (buffer_amount * 2)

    # 3. Wyznaczenie Take Profit
    # BEZPIECZNE SPRAWDZENIE: sprawdzamy czy opór istnieje ORAZ czy ma wartość liczbową
    if resistance is not None and resistance.get("price") is not None and resistance["price"] > price:
        take_profit = resistance["price"]
    else:
        # Wybicie szczytów (ATH) lub brak oporu nad głową:
        # Automatycznie celujemy w profil R/R = 2.0 na podstawie zaryzykowanej kwoty
        risk_amount = price - stop_loss
        take_profit = price + (risk_amount * max(2.5, MIN_RR))

    # 4. Wyliczenie realnego Risk/Reward Ratio (R/R)
    if stop_loss is not None and take_profit is not None:
        risk = price - stop_loss
        reward = take_profit - price

        if risk > 0 and reward > 0:
            rr = round(reward / risk, 2)
        else:
            rr = 0.0

    return (
    round(stop_loss, 2) if stop_loss is not None else None,
    round(take_profit, 2) if take_profit is not None else None,
    rr
)