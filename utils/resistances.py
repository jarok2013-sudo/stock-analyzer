import sys
from pathlib import Path
# Dodajemy katalog nadrzędny (../) do ścieżek wyszukiwania modułów Pythona
parent_dir = Path(__file__).resolve().parent.parent
import numpy as np
from config import ZONE_TOLERANCE


def find_resistance_zones(maxima, tolerance=ZONE_TOLERANCE):
    zones = []

    for pkt_max in maxima:
        price = pkt_max["price"]
        date = pkt_max["date"]

        best_zone = None
        min_distance = float("inf")

        # 1. Szukamy Najbliższej strefy w obrębie tolerancji
        for zone in zones:
            avg_price = zone["price"]
            dist_pct = abs(price - avg_price) / avg_price

            if dist_pct < tolerance and dist_pct < min_distance:
                min_distance = dist_pct
                best_zone = zone

        # 2. Dopasowujemy do istniejącej strefy lub tworzymy nową
        if best_zone is not None:
            best_zone["prices"].append(price)
            best_zone["dates"].append(date)

            # Aktualizacja statystyk strefy
            best_zone["price"] = round(float(np.mean(best_zone["prices"])), 2)
            best_zone["last_test"] = max(best_zone["dates"])
            best_zone["first_test"] = min(best_zone["dates"])
            best_zone["touches"] = len(best_zone["prices"])
        else:
            # Tworzymy nową strefę
            zones.append(
                {
                    "price": price,
                    "prices": [price],
                    "dates": [date],
                    "last_test": date,
                    "first_test": date,
                    "touches": 1,
                }
            )

    return zones


def rate_resistances(zones):
    results = []

    for zone in zones:
        price = zone["price"]
        touches = zone["touches"]

        if touches >= 5:
            strength = "★★★★★"
        elif touches >= 4:
            strength = "★★★★☆"
        elif touches >= 3:
            strength = "★★★☆☆"
        else:
            strength = "★★☆☆☆"

        results.append(
            {
                "price": price,
                "touches": touches,
                "strength": strength,
                "last_test": zone.get("last_test"),
                "first_test": zone.get("first_test"),
            }
        )

    return results

"""
zwraca najbliższy opór i
"""
def find_nearest_resistance(current_price, resistances):
    """Zwraca najbliższy opór POWYŻEJ obecnej ceny.
    Jeśli cena przebiła wszystkie opory, zwraca informację o braku oporu
    (ATH).
    """
    if not resistances:
        return None

    valid_resistances = [r for r in resistances if r["price"] > current_price]

    if not valid_resistances:
        # Cena jest powyżej wszystkich oporów z historii (Wybicie szczytów / ATH)
        # Zwracamy czytelny słownik informacyjny
        highest_past_resistance = max(resistances, key=lambda x: x["price"])
        return {
            "price": None,
            "is_ath": True,
            "touches": 0,
            "strength": "N/A",
            "last_test": None,
            "message": f"Przekroczono najwyższy opór ({highest_past_resistance['price']:.2f} zł) - otwarta droga do wzrostów",
        }

    # Jeśli są opory powyżej obecnej ceny, wybieramy ten najbliższy (najmniejszy z większych od ceny)
    nearest = min(valid_resistances, key=lambda x: x["price"])
    nearest["is_ath"] = False
    return nearest