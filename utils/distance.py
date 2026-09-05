def distance_to_support(price, support):
    # Sprawdzamy czy wsparcie istnieje i czy ma przypisaną cenę
    if (
        support is None
        or support.get("price") is None
        or price is None
        or price <= 0
    ):
        return None

    return (price - support["price"]) / price * 100


def distance_to_resistance(price, resistance):
    # Sprawdzamy czy opór istnieje i czy ma przypisaną cenę (np. przy ATH price to None)
    if (
        resistance is None
        or resistance.get("price") is None
        or price is None
        or price <= 0
    ):
        return None

    return (resistance["price"] - price) / price * 100

"""
W miejscu formatowania wyników wystarczy wtedy napisać prosty warunek:

dist_r = distance_to_resistance(analysis.price, analysis.nearest_resistance)

if dist_r is not None:
    print(f"Distance R : {dist_r:.2f}%")
else:
    print("Distance R : BRAK (Wybicie szczytów / ATH)")


"""
