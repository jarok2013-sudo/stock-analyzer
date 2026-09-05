import pandas as pd
import datetime

def fmt_float(val, precision=2, default="N/D"):
            """Bezpiecznie formatuje liczby, obsługując wartości None oraz NaN."""
            if val is None or pd.isna(val):
                return default
            return f"{val:.{precision}f}"

def fmt_num(val, unit="", is_pct=False, precision=2):
    """Pomocnicza funkcja do bezpiecznego formatowania wartości z Yahoo Finance."""
    if val is None or val == "N/A":
        return "-"
    try:
        num = float(val)
        if is_pct:
            # Jeśli yfinance zwraca np. 0.0047 dla 0.47%
            val_pct = num * 100 if num < 1.0 else num
            return f"{val_pct:.2f}%"
        if abs(num) >= 1e9:
            return f"{num / 1e9:.2f} mld {unit}".strip()
        if abs(num) >= 1e6:
            return f"{num / 1e6:.2f} mln {unit}".strip()
        return f"{num:.{precision}f} {unit}".strip()
    except (ValueError, TypeError):
        return str(val)

def fmt_date(ts):
    """Formatowanie znacznika czasu Unix do daty."""
    if not ts:
        return "-"
    try:
        if isinstance(ts, (int, float)):
            return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        return str(ts)
    except Exception:
        return str(ts)

def safe_date_str(val):
    if not val:
        return None
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    if isinstance(val, (int, float)):
        return datetime.datetime.fromtimestamp(val).strftime("%Y-%m-%d")
    return str(val)[:10]

# zabezpieczenie przed None i NaN dla wartości boolowskich
def _bool_value(value, default=False):
    if value is None or pd.isna(value):
        return default
    return bool(value)

def _safe_number(value, default=None):
    """
    Bezpiecznie konwertuje wartość na float.
    Na NaN zwraca default.
    """
    if value is None:
        return default

    try:
        value = float(value)
    except (TypeError, ValueError):
        return default

    if pd.isna(value):
        return default

    return value