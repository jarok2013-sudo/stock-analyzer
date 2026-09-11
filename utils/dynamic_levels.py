from utils.func import _safe_number
from utils.levels import recent_breakout_and_retest


def calculate_dynamic_levels(self):
    """
    Aktualizuje aktywne wsparcia i opory po potwierdzonych wybiciach.

    Dawny opór, który został rzeczywiście wybity górą,
    może stać się wsparciem typu FLIP.

    Dawne wsparcie wybite dołem nie jest traktowane
    jako aktywne wsparcie.
    """

    price = _safe_number(self.price)

    if price is None or price <= 0:
        self.dynamic_supports = []
        self.dynamic_resistances = []
        self.nearest_dynamic_support = None
        self.nearest_dynamic_resistance = None
        self.dynamic_support_distance = None
        self.dynamic_resistance_distance = None
        return

    # Pobieramy DataFrame z obiektu self (StockAnalysis)
    df = getattr(self, "df", getattr(self, "data", None))

    # ------------------------------------------------------------
    # 1. Zwykłe wsparcia znajdujące się POD ceną
    # ------------------------------------------------------------

    dynamic_supports = []

    for support in getattr(self, "rated_supports", []) or []:

        if not isinstance(support, dict):
            continue

        support_price = _safe_number(
            support.get("price")
        )

        if support_price is None:
            continue

        if support_price < price:

            level = dict(support)

            level["source"] = "SUPPORT"
            level["active"] = True

            dynamic_supports.append(level)

    # ------------------------------------------------------------
    # 2. Potwierdzone FLIP SUPPORT
    #
    # Dawny opór poniżej ceny:
    #
    # resistance
    #      ↓ breakout
    #      ↓ retest
    # resistance → support
    # ------------------------------------------------------------

    for resistance in getattr(
        self,
        "rated_resistances",
        []
    ) or []:

        if not isinstance(resistance, dict):
            continue

        resistance_price = _safe_number(
            resistance.get("price")
        )

        if resistance_price is None:
            continue

        # Interesują nas tylko stare opory POD ceną
        if resistance_price >= price:
            continue

        level = dict(resistance)

        # Sprawdzamy rzeczywiste wybicie przekazując prawidłowy DataFrame (df)
        breakout_state = recent_breakout_and_retest(
            df=df,
            level_price=resistance_price,
            direction="up",
            lookback=8,
            tolerance_pct=1.0,
        )

        if breakout_state.get("breakout"):

            level["source"] = "RESISTANCE_FLIP"

            level["active"] = True

            level["breakout_confirmed"] = True

            level["retest_confirmed"] = bool(
                breakout_state.get("retest")
            )

            dynamic_supports.append(level)

    # ------------------------------------------------------------
    # 3. Usuwamy duplikaty poziomów
    # ------------------------------------------------------------

    unique_supports = {}

    for level in dynamic_supports:

        level_price = _safe_number(
            level.get("price")
        )

        if level_price is None:
            continue

        key = round(level_price, 2)

        # Jeżeli mamy zwykłe wsparcie i FLIP
        # w praktycznie tym samym miejscu,
        # FLIP ma pierwszeństwo.
        existing = unique_supports.get(key)

        if existing is None:
            unique_supports[key] = level

        elif (
            level.get("source") == "RESISTANCE_FLIP"
            and existing.get("source") != "RESISTANCE_FLIP"
        ):
            unique_supports[key] = level

    self.dynamic_supports = list(
        unique_supports.values()
    )

    # ------------------------------------------------------------
    # 4. Aktywne opory = tylko opory NAD ceną
    # ------------------------------------------------------------

    self.dynamic_resistances = []

    for resistance in getattr(
        self,
        "rated_resistances",
        []
    ) or []:

        if not isinstance(resistance, dict):
            continue

        resistance_price = _safe_number(
            resistance.get("price")
        )

        if resistance_price is None:
            continue

        if resistance_price > price:

            level = dict(resistance)

            level["source"] = "RESISTANCE"
            level["active"] = True

            self.dynamic_resistances.append(level)

    # ------------------------------------------------------------
    # 5. Najbliższe dynamiczne wsparcie
    # ------------------------------------------------------------

    if self.dynamic_supports:

        self.nearest_dynamic_support = min(
            self.dynamic_supports,
            key=lambda x: abs(
                _safe_number(x.get("price")) - price
            )
        )

    else:

        self.nearest_dynamic_support = None

    # ------------------------------------------------------------
    # 6. Najbliższy dynamiczny opór
    # ------------------------------------------------------------

    if self.dynamic_resistances:

        self.nearest_dynamic_resistance = min(
            self.dynamic_resistances,
            key=lambda x: abs(
                _safe_number(x.get("price")) - price
            )
        )

    else:

        self.nearest_dynamic_resistance = None

    # ------------------------------------------------------------
    # 7. Odległości
    # ------------------------------------------------------------

    support = self.nearest_dynamic_support
    resistance = self.nearest_dynamic_resistance

    if support:

        support_price = _safe_number(
            support.get("price")
        )

        self.dynamic_support_distance = (
            (price - support_price) / price
        ) * 100.0

    else:

        self.dynamic_support_distance = None

    if resistance:

        resistance_price = _safe_number(
            resistance.get("price")
        )

        self.dynamic_resistance_distance = (
            (resistance_price - price) / price
        ) * 100.0

    else:

        self.dynamic_resistance_distance = None