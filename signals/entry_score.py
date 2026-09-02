
"""
dwuwarstwowy system decyzyjny używany przez profesjonalny trading algorytmiczny:
Quality Score >= 75-80 $\rightarrow$ Skaner tworzy listę obserwacyjną ("To są świetne spółki z silnym trendem").
Entry Score >= 80-85 $\rightarrow$ Skaner wyrzuca natychmiastowy alert transakcyjny ("I właśnie w tej sekundzie masz idealny punkt do zajęcia pozycji z małym ryzykiem").

Przedział,Kolor,Stan / Sygnał,Co oznacza w praktyce?
85 – 100+ pkt,🟢 Zielony,KUPUJ / SPUST POLUZOWANY,"Idealny moment: Świetny R/R (≥2.5-3.0), cena na wsparciu/BB, potwierdzony wolumen i wyzwalacz (MACD/Stoch)."
65 – 84 pkt,🟡 Żółty,OBSERWUJ / GOTOWOŚĆ,"Przyzwoite wejście, ale brakuje wyzwalacza (np. MACD jeszcze nie opadł) lub wolumen jest przeciętny."
45 – 64 pkt,⚪ Szary,NEUTRALNY / SPASUJ,Słaby R/R lub cena zbyt daleko od poziomów obronnych (SL musiałby być zbyt szeroki).
0 – 44 pkt,🔴 Czerwony,ZAKAZ WEJŚCIA,Brak wsparcia pod nogami, fatalny R/R lub kupowanie tuż pod oporem.

do 100
┌─────────────────────────┬─────────┐
│ R/R                     │ 35 pkt  │
├─────────────────────────┼─────────┤
│ Proximity               │ 25 pkt  │
├─────────────────────────┼─────────┤
│ MACD trigger            │ 20 pkt  │
│ Stochastic trigger      │  5 pkt  │
│ ADX/DI confirmation     │  5 pkt  │
├─────────────────────────┼─────────┤
│ Volume                  │ 10 pkt  │
├─────────────────────────┼─────────┤
│ SUMA                    │ 100 pkt │
└─────────────────────────┴─────────┘
"""
import sys
import pandas as pd
from pathlib import Path

# Dodajemy katalog nadrzędny (../) do ścieżek wyszukiwania modułów Pythona
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import config  # Teraz 'config' jest dostępny jako obiekt!


def add_reason(reasons, category, points, text):
    reasons.append({
        "category": category,
        "points": points,
        "text": text
    })


def calculate_entry_score(analysis):
    score = 0
    reasons = []

    if getattr(analysis, "risk_reward", None) is None:
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak możliwości wyliczenia R/R - brak poziomu wejścia",
        )
        return 0, reasons

    scorers = [
        score_entry_rr,
        score_entry_proximity,
        score_entry_trigger,
        score_entry_volume,
    ]

    for scorer in scorers:
        pts, msgs = scorer(analysis)
        score += pts
        reasons.extend(msgs)

    final_score = max(0, score)
    return final_score, reasons


def score_entry_rr(analysis):
    score = 0
    reasons = []

    # Bezpieczne pobranie R/R (zabezpieczenie przed None)
    rr = getattr(analysis, "risk_reward", None)

    min_rr = getattr(config, "MIN_RR", 2.0)
    entry_pts_rr = getattr(config, "ENTRY_POINTS_RR", 35)

    # 1. Obsługa braku wyliczonego R/R
    if rr is None or pd.isna(rr):
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Brak możliwości wyliczenia profilu R/R (brak stref wsparcia/oporu)",
        )
        return score, reasons

    # 2. Ocena na podstawie wartości R/R
    if rr >= 3.0:
        score += entry_pts_rr
        add_reason(
            reasons, "Risk/Reward", entry_pts_rr, f"Wybitny profil R/R = {rr:.2f}"
        )
    elif rr >= min_rr:
        pts = int(entry_pts_rr * 0.7)
        score += pts
        add_reason(reasons, "Risk/Reward", pts, f"Dobre R/R = {rr:.2f}")
    elif rr > 0:
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            f"R/R zbyt niskie ({rr:.2f} < {min_rr:.1f}) - zły stosunek ryzyka do zysku",
        )
    else:
        add_reason(
            reasons,
            "Risk/Reward",
            0,
            "Negatywny profil R/R - Stop Loss powyżej/na poziomie ceny",
        )

    return score, reasons


def score_entry_proximity(analysis):
    score = 0
    reasons = []

    price = getattr(analysis, "price", None)
    support = getattr(analysis, "nearest_support", None)
    max_dist = getattr(config, "MAX_SUPPORT_DISTANCE", 2.5)
    entry_pts_support = getattr(config, "ENTRY_POINTS_SUPPORT", 25)

    if price is None or pd.isna(price) or price <= 0:
        add_reason(
            reasons, "Proximity", 0, "Brak aktualnej ceny do wyznaczenia bliskości"
        )
        return score, reasons

    # --- A. BADANIE ODLEGŁOŚCI OD WSPARCIA ---
    dist_supp = None
    touches = 1

    if support is not None and support.get("price") is not None:
        supp_price = support["price"]
        # Wyliczamy odchylenie w % (dodatnie = cena NAD wsparciem, ujemne = cena POD wsparciem)
        dist_supp = ((price - supp_price) / price) * 100
        #touches = support.get("touches", 1) ## poprawka kodu poniżej
        raw_touches = support.get("touches") if support else None
        touches = raw_touches if (raw_touches is not None) else 1

    # --- B. BADANIE ODLEGŁOŚCI OD EMA20 I BOLLINGERA ---
    dist_ema20 = None
    ema20 = getattr(analysis, "ema20", None)
    if ema20 is not None and not pd.isna(ema20) and ema20 > 0:
        dist_ema20 = abs((price - ema20) / ema20) * 100

    bb_lower = getattr(analysis, "bb_lower", None)
    bb_squeeze = getattr(analysis, "bb_squeeze", False)

    # --- C. MAIN SCORING LOGIC ---
    # 1. Główny test: Bliskość wsparcia (z obsługą lekkiego naruszenia do -0.5%)
    if dist_supp is not None and -0.5 <= dist_supp <= max_dist:
        # Bezpieczne pobranie flagi ATH (domyślnie False)
        is_near_ath = bool(getattr(analysis, "is_near_ath", False))
        # 1. LOGIKA DLA ATH / NOWYCH SZCZYTÓW
        if is_near_ath:
            # Na ATH wyznaczamy premie za SAM FAKT testu dawnego szczytu (zasada biegunowości)
            # Nie wymagamy wielu testów! 1 lub 2 testy są idealne.
            bonus_strength = 5 if touches <= 2 else 0
            bonus_msg = " [Obrona poziomu wybicia ATH]"
        # 2. LOGIKA KLASYCZNA (Konsolidacja / Zwykły trend)
        else:
            # Premia za mocną strefę wsparcia (na bazie Twojego rate_supports)
            bonus_strength = 5 if touches >= 4 else 0
            bonus_msg = f" [Silna strefa: {touches} testów]" if bonus_strength > 0 else ""
        
        total_pts = entry_pts_support + bonus_strength

        score += total_pts

        add_reason(
            reasons,
            "Proximity",
            total_pts,
            f"Idealne miejsce: cena tuż przy wsparciu ({dist_supp:.2f}%){bonus_msg}",
        )

    # 2. Alternatywny test: Bliskość średniej EMA20 (UJEDNOLICONE PROGI)
    elif dist_ema20 is not None and dist_ema20 <= 2.0:
        pts = int(entry_pts_support * 0.8)  # np. 24 pkt
        score += pts
        add_reason(
            reasons,
            "Proximity",
            pts,
            f"Dobre wejście: test średniej EMA20 (odchylenie {dist_ema20:.2f}%)",
        )

    # 3. Dodatkowy przedział: Umiarkowany odlot od EMA20 (2.0% - 4.0%)
    elif dist_ema20 is not None and 2.0 < dist_ema20 <= 4.0:
        pts = int(entry_pts_support * 0.3)  # mała premia (np. 9 pkt)
        score += pts
        add_reason(
            reasons,
            "Proximity",
            pts,
            f"Lekki odlot od EMA20 (+{dist_ema20:.2f}%) - brak bezpośredniego wsparcia pod nogami",
        )

    # 4. Alternatywny test: Dolna Wstęga Bollingera
    elif (
        bb_lower is not None
        and not pd.isna(bb_lower)
        and price <= bb_lower * 1.01
    ):
        pts = int(entry_pts_support * 0.7)
        score += pts
        add_reason(
            reasons,
            "Proximity",
            pts,
            f"Test dolnej Wstęgi Bollingera ({bb_lower:2f}) (strefa wyprzedania)",
        )

    # 5. Znaczny odlot
    else:
        add_reason(
            reasons,
            "Proximity",
            0,
            f"Cena w powietrzu (ponad 4% od wsparcia, EMA20 ({ema20:2f}) i dolnej BB ({bb_lower:2f}))",
        )

    # --- D. DODATKOWA PREMIA: BOLLINGER SQUEEZE ---
    if bb_squeeze:
        score += 5
        add_reason(
            reasons,
            "Proximity",
            5,
            "Ściśnięcie Wstęg Bollingera (Squeeze) – tuż przed wybuchem zmienności",
        )

    return score, reasons


"""
score_entry_trigger (MACD + Stochastic + DI)
Rozszerzamy wyzwalacze o Stochastic (dla szybkiego impulsu ze strefy wyprzedania) oraz opcjonalny dodatek za ADX/DI
"""
def score_entry_trigger(analysis):
    score = 0
    reasons = []

    macd_above = getattr(analysis, "macd", 0) > getattr(
        analysis, "macd_signal", 0
    )
    hist_rising = getattr(analysis, "histogram_rising", False)

    stoch_k = getattr(analysis, "stoch_k", None)
    stoch_d = getattr(analysis, "stoch_d", None)

    entry_pts_macd = getattr(config, "ENTRY_POINTS_MACD", 25)

    # 1. MACD Trigger (Główny impuls momentum)
    if macd_above and hist_rising:
        score += entry_pts_macd
        add_reason(
            reasons,
            "Trigger",
            entry_pts_macd,
            "MACD rośnie i potwierdza dynamikę wejścia",
        )
    elif macd_above:
        pts = int(entry_pts_macd * 0.5)
        score += pts
        add_reason(
            reasons,
            "Trigger",
            pts,
            "MACD w strefie wzrostowej (brak świeżego pędu)",
        )
    else:
        add_reason(reasons, "Trigger", 0, "Brak sygnału popytowego na MACD")

    # 2. STOCHASTIC TRIGGER (Świeży sygnał z dołka - premia punktowa)
    if stoch_k is not None and stoch_d is not None:
        # Złote przecięcie na Stochastyku w strefie wyprzedania (<25)
        if stoch_k < 25 and stoch_k > stoch_d:
            score += 10
            add_reason(
                reasons,
                "Trigger",
                10,
                f"Szybki trigger: Stochastic wybija z wyprzedania (%K={stoch_k:.1f})",
            )

    return score, reasons


def score_entry_volume(analysis):
    score = 0
    reasons = []
    vol_ratio = getattr(analysis, "vol_ratio", 1.0)
    pts = getattr(config, "ENTRY_POINTS_VOLUME", 10)

    if vol_ratio >= 1.3:
        score += pts
        add_reason(
            reasons,
            "Volume",
            pts,
            f"Wejście potwierdzone obrotami ({vol_ratio:.1f}x średniej)",
        )
    else:
        add_reason(reasons, "Volume", 0, "Przeciętny wolumen na wejściu")

    return score, reasons