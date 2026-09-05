# interpreter.py
import config


def interpret_rsi(rsi: float | None) -> str:
    """Interpretuje wartość wskaźnika RSI."""
    if rsi is None:
        return "Brak danych"

    rsi_so = getattr(config, "RSI_STRONG_OVERBOUGHT", 80)
    rsi_ob = getattr(config, "RSI_OVERBOUGHT", 70)
    rsi_id = getattr(config, "RSI_IDEAL", 60)
    rsi_gd = getattr(config, "RSI_GOOD", 50)
    rsi_os = getattr(config, "RSI_OVERSOLD", 30)
    rsi_sos = getattr(config, "RSI_STRONG_OVERSOLD", 20)

    if rsi >= rsi_so:
        return f"{rsi:.1f} ⚠️ [Skrajne Przegrzanie / Bardzo Wysokie Ryzyko]"
    elif rsi >= rsi_ob:
        return f"{rsi:.1f} 🔴 [Wykupienie / Ryzyko Lokalnej Korekty]"
    elif rsi >= rsi_id:
        return f"{rsi:.1f} 🟢 [Silny Pęd Wzrostowy / Kupujący Rządzą]"
    elif rsi >= rsi_gd:
        return f"{rsi:.1f} 🟡 [Umiarkowany Pęd Wzrostowy / Neutralnie]"
    elif rsi >= rsi_os:
        return f"{rsi:.1f} 📉 [Słabość Rynku / Przewaga Podaży]"
    elif rsi >= rsi_sos:
        return f"{rsi:.1f} 🟢 [Mocne Wyprzedanie / Szansa na Odbicie]"
    else:
        return f"{rsi:.1f} 🚀 [Skrajne Wyprzedanie / Ekstremalny Okazja]"


def interpret_macd(macd: float | None, signal: float | None) -> dict:
    """Interpretuje wskaźnik MACD względem linii Signal."""
    if macd is None or signal is None:
        return {
            "macd": "N/D",
            "signal": "N/D",
            "status": "Brak danych",
            "is_bullish": False,
        }

    is_bullish = macd > signal
    diff = macd - signal

    if is_bullish:
        status = f"🟢 BYCZY (MACD nad Signal, różnica: +{diff:.3f})"
    else:
        status = f"🔴 NIEDŹWIEDZI / KOREKTA (MACD pod Signal, różnica: {diff:.3f})"

    return {
        "macd": f"{macd:.3f}",
        "signal": f"{signal:.3f}",
        "status": status,
        "is_bullish": is_bullish,
    }


def interpret_volume(vol_ratio: float | None) -> str:
    """Interpretuje stosunek bieżącego wolumenu do średniej 20-sesyjnej."""
    if vol_ratio is None:
        return "Brak danych"

    if vol_ratio >= 2.0:
        return f"{vol_ratio:.2f}x 🔥 [Potężny Skok Wolumenu / Duże Ruchy]"
    elif vol_ratio >= 1.2:
        return f"{vol_ratio:.2f}x 📈 [Podwyższona Aktywność Kapitału]"
    elif vol_ratio >= 0.8:
        return f"{vol_ratio:.2f}x ⚖️ [Standardowy Wolumen / Norma]"
    else:
        return f"{vol_ratio:.2f}x 💤 [Niska Aktywność / Uśpienie Rynku]"


def interpret_atr(atr: float | None, price: float | None, currency: str = "PLN") -> str:
    """Interpretuje ATR w kwocie i w ujęciu procentowym względem ceny."""
    if atr is None or price is None or price == 0:
        return "Brak danych"

    atr_pct = (atr / price) * 100
    if atr_pct > 4.0:
        desc = "Wysoka Zmienność ⚠️"
    elif atr_pct >= 1.5:
        desc = "Umiarkowana Zmienność ⚖️"
    else:
        desc = "Niska Zmienność / Stabilność 💤"

    return f"{atr:.2f} {currency} ({atr_pct:.2f}% ceny) ➔ {desc}"


def interpret_ema_position(price: float | None, ema_val: float | None, ema_name: str, currency: str = "PLN") -> str:
    """Interpretuje położenie kursu względem wybranej średniej EMA."""
    if price is None or ema_val is None:
        return f"{ema_name}: Brak danych"

    diff_pct = ((price - ema_val) / price) * 100
    if price > ema_val:
        return f"{ema_name}: {ema_val:.2f} {currency} ➔ POWYŻEJ 🟢 (+{diff_pct:.2f}%)"
    else:
        return f"{ema_name}: {ema_val:.2f} {currency} ➔ PONIŻEJ 🔴 ({diff_pct:.2f}%)"


def interpret_distance(dist: float | None, is_support: bool = True) -> str:
    """Interpretuje dystans procentowy do wsparcia lub oporu."""
    if dist is None:
        return "Brak danych"

    level_type = "wsparcia" if is_support else "oporu"
    if dist <= 1.5:
        return f"{dist:.2f}% ⚠️ [Test Poziomu! Bardzo Blisko {level_type}]"
    elif dist <= 4.5:
        return f"{dist:.2f}% 🎯 [W Strefie Zasięgu {level_type}]"
    else:
        return f"{dist:.2f}% 🛡️ [Bezpieczna Odległość od {level_type}]"


def interpret_risk_reward(rr: float | None) -> str:
    """Interpretuje wskaźnik Risk/Reward Ratio."""
    if rr is None:
        return "Brak danych"

    if rr >= 3.0:
        return f"1:{rr:.2f} 🌟 [Wybitny Stosunek Zysk/Ryzyko]"
    elif rr >= 2.0:
        return f"1:{rr:.2f} 🟢 [Akceptowalny / Poprawny Setup]"
    elif rr >= 1.5:
        return f"1:{rr:.2f} 🟡 [Przeciętny / Podwyższone Ryzyko]"
    else:
        return f"1:{rr:.2f} 🔴 [Słaby / Unikaj Wejścia]"

def interpret_resistance(
    resistance: dict | None,
    rated_resistances: list = None,
    price: float | None = None,
    resistance_distance: float | None = None,
    currency: str = "PLN",
) -> str:
    """Interpretuje najbliższy opór lub wybicie szczytów (ATH)."""
    rated_resistances = rated_resistances or []

    # 1. Sprawdzamy, czy istnieje aktywny opór PRAWIDŁOWO zawieszony POWYŻEJ obecnej ceny
    if (
        isinstance(resistance, dict)
        and resistance.get("price") is not None
        and price is not None
        and resistance["price"] > price
    ):
        r_price = resistance["price"]
        r_touches = resistance.get("touches", 1)
        dist_str = (
            interpret_distance(resistance_distance, is_support=False)
            if resistance_distance is not None
            else "N/A"
        )
        return f"{r_price:.2f} {currency} [{r_touches}x testy] ➔ Odstęp: {dist_str}"

    # 2. Jeśli brakuje oporu nad ceną (wybicie/ATH) – szukamy ostatnio przebitego oporu POD ceną
    broken_resistances = [
        r
        for r in rated_resistances
        if isinstance(r, dict)
        and r.get("price") is not None
        and price is not None
        and r["price"] < price
    ]

    if broken_resistances:
        last_broken = max(broken_resistances, key=lambda x: x["price"])
        b_price = last_broken["price"]
        b_dist = (((price - b_price) / price) * 100.0) if price else 0.0
        return f"Ostatni przebity {b_price:.2f} {currency} (+{b_dist:.2f}%) 🚀 ➔ Wybicie szczytów / ATH (Otwarta droga)"

    # 3. Fallback – gdy brak jakichkolwiek przełamanych oporów w historii / czysty wykres
    return "BRAK (Wybicie szczytów / ATH) 🚀 ➔ Otwarta droga do wzrostów"