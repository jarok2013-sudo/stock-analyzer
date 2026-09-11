import pandas as pd
from utils.func import _safe_number

def _get_level_price(level):
    if not isinstance(level, dict):
        return None

    return _safe_number(level.get("price"))

def find_recent_breakout(
    df,
    level_price,
    direction="up",
    lookback=8,
):
    # Ekstrakcja DataFrame, jeśli przekazano obiekt StockAnalysis
    if hasattr(df, "df"):
        df = df.df
    elif hasattr(df, "data"):
        df = df.data

    if (
        df is None
        or not hasattr(df, "empty")
        or df.empty
        or level_price is None
        or "close" not in df.columns
    ):
        return None

    recent = df.tail(lookback + 1).copy()

    if len(recent) < 2:
        return None

    closes = pd.to_numeric(
        recent["close"],
        errors="coerce"
    )

    for i in range(1, len(closes)):

        previous_close = closes.iloc[i - 1]
        current_close = closes.iloc[i]

        if (
            pd.isna(previous_close)
            or pd.isna(current_close)
        ):
            continue

        if direction == "up":

            if (
                previous_close <= level_price
                and current_close > level_price
            ):
                return i

        elif direction == "down":

            if (
                previous_close >= level_price
                and current_close < level_price
            ):
                return i

    return None

def has_recent_retest_after_breakout(
    df,
    level_price,
    breakout_position,
    direction="up",
    tolerance_pct=1.0,
):
    # Ekstrakcja DataFrame, jeśli przekazano obiekt StockAnalysis
    if hasattr(df, "df"):
        df = df.df
    elif hasattr(df, "data"):
        df = df.data

    if (
        df is None
        or not hasattr(df, "empty")
        or df.empty
        or level_price is None
        or breakout_position is None
    ):
        return False

    required_columns = {
        "high",
        "low",
        "close",
    }

    if not required_columns.issubset(df.columns):
        return False

    recent = df.tail(9).copy()

    if len(recent) <= breakout_position + 1:
        return False

    tolerance = level_price * (
        tolerance_pct / 100.0
    )

    lower_bound = level_price - tolerance
    upper_bound = level_price + tolerance

    # WAŻNE:
    # zaczynamy dopiero po świecy breakout

    for i in range(
        breakout_position + 1,
        len(recent)
    ):

        row = recent.iloc[i]

        high = _safe_number(row.get("high"))
        low = _safe_number(row.get("low"))
        close = _safe_number(row.get("close"))

        if (
            high is None
            or low is None
            or close is None
        ):
            continue

        if direction == "up":

            touched_level = (
                low <= upper_bound
                and high >= lower_bound
            )

            held_above = (
                close > level_price
            )

            if touched_level and held_above:
                return True

        elif direction == "down":

            touched_level = (
                high >= lower_bound
                and low <= upper_bound
            )

            held_below = (
                close < level_price
            )

            if touched_level and held_below:
                return True

    return False

def recent_breakout_and_retest(
    df,
    level_price,
    direction="up",
    lookback=8,
    tolerance_pct=1.0,
):
    result = {
        "breakout": False,
        "retest": False,
    }

    breakout_position = find_recent_breakout(
        df=df,
        level_price=level_price,
        direction=direction,
        lookback=lookback,
    )

    if breakout_position is None:
        return result

    result["breakout"] = True

    result["retest"] = has_recent_retest_after_breakout(
        df=df,
        level_price=level_price,
        breakout_position=breakout_position,
        direction=direction,
        tolerance_pct=tolerance_pct,
    )

    return result