import numpy as np
from config import ZONE_TOLERANCE


def find_support_zones(minima, tolerance=ZONE_TOLERANCE):
    zones = []

    for pkt_min in minima:
        price = pkt_min["price"]
        date = pkt_min["date"]

        best_zone = None
        min_distance = float("inf")

        # 1. Szukamy najbliższej geograficznie strefy w promieniu tolerancji
        for zone in zones:
            avg_price = zone["price"]
            dist_pct = abs(price - avg_price) / avg_price

            if dist_pct < tolerance and dist_pct < min_distance:
                min_distance = dist_pct
                best_zone = zone

        # 2. Przypisujemy do istniejącej strefy lub tworzymy nową
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


def rate_supports(zones):
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
zwraca najbliższy opór 
"""
def find_nearest_support(current_price, supports):
    """Zwraca najbliższe wsparcie PONIŻEJ obecnej ceny."""
    if not supports:
        return None

    valid_supports = [s for s in supports if s["price"] < current_price]

    if not valid_supports:
        # Cena spadła poniżej najniższego wsparcia z historii
        lowest_past_support = min(supports, key=lambda x: x["price"])
        return {
            "price": None,
            "is_atl": True,
            "touches": 0,
            "strength": "N/A",
            "last_test": None,
            "message": f"Spadek poniżej najniższego wsparcia ({lowest_past_support['price']:.2f} zł) - linia w tle",
        }

    # Wybieramy wsparcie najbliższe cenie (największe z mniejszych od ceny)
    nearest = max(valid_supports, key=lambda x: x["price"])
    nearest["is_atl"] = False
    return nearest
