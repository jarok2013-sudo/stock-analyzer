# def find_local_minima(df):
   
#     minima = []

#     for i in range(2, len(df)-2):

#         current = df.iloc[i]["low"]

#         window = df.iloc[i-2:i+3]["low"]

#         if current == window.min():

#             minima.append(
#                  {
#                     "date": df.index[i],
#                     "index": i,
#                     "price": round(current,2),
#                     "volumen": df.iloc[i]["volume"],
#                     "type": "minimum"
#                 }
#             )
        
#         # debug
#         # print("----------------")
#         # print(f"\nSprawdzam dzień: {df.index[i].date()}")
#         # print(window)
#         # print(f"Minimum w oknie: {window.min()}")
#         # print(f"Bieżąca wartość: {current}")
    
#     return minima

# def find_local_maxima(df):

#     maxima = []

#     for i in range(2, len(df)-2):

#         current = df.iloc[i]["high"]

#         window = df.iloc[i-2:i+3]["high"]

#         if current == window.max():

#             maxima.append(
#                 {
#                     "date": df.index[i],
#                     "index": i,
#                     "price": round(current,2),
#                     "volumen": df.iloc[i]["volume"],
#                     "type": "maximum"
#                 }
#             )
           

#     return maxima

def find_local_nearest_minmax(df):
   
    minmax = []

    for i in range(2, len(df)-2):

        currentmin = df.iloc[i]["low"]
        windowmin = df.iloc[i-2:i+3]["low"]

        currentmax = df.iloc[i]["high"]
        windowmax = df.iloc[i-2:i+3]["high"]

        if currentmin == windowmin.min():

            minmax.append(
                 {
                    "date": df.index[i],
                    "index": i,
                    "price": round(currentmin,2),
                    "volumen": df.iloc[i]["volume"],
                    "type": "minimum"
                }
            )

        if currentmax == windowmax.max():

            minmax.append(
                {
                    "date": df.index[i],
                    "index": i,
                    "price": round(currentmax,2),
                    "volumen": df.iloc[i]["volume"],
                    "type": "maximum"
                }
            )
        
        # debug
        # print("----------------")
        # print(f"\nSprawdzam dzień: {df.index[i].date()}")
        # print(window)
        # print(f"Minimum w oknie: {window.min()}")
        # print(f"Bieżąca wartość: {current}")
    
    return minmax


def find_local_minmax_vectorized(df, window_size=2):
    """
    Znajduje lokalne dołki i szczyty w oknie (2*window_size + 1).
    Domyślnie sprawdza 2 świece wstecz i 2 w przód.
    """
    df = df.copy()
    full_window = 2 * window_size + 1

    # Wyznaczenie ekstremów w oknie ze wyśrodkowaniem
    min_roll = df["low"].rolling(window=full_window, center=True).min()
    max_roll = df["high"].rolling(window=full_window, center=True).max()

    # Maski logiczne dla dołków i szczytów
    is_min = (df["low"] == min_roll)
    is_max = (df["high"] == max_roll)

    # Tworzenie listy wyników
    results = []

    for idx, row in df[is_min | is_max].iterrows():
        i = df.index.get_loc(idx)
        
        # Opcjonalne zabezpieczenie przed krawędziami DataFrame
        if i < window_size or i >= len(df) - window_size:
            continue

        if is_min.loc[idx]:
            results.append({
                "date": idx,
                "index": i,
                "price": round(row["low"], 2),
                "volume": row["volume"],
                "type": "minimum"
            })
        
        if is_max.loc[idx]:
            results.append({
                "date": idx,
                "index": i,
                "price": round(row["high"], 2),
                "volume": row["volume"],
                "type": "maximum"
            })

    return results

# def calculate_fibo_levels(
#     swing_high: float, swing_low: float, trend: str = "UP"
# ) -> dict:
#     """Wylicza poziomy zniesień Fibonacciego dla podanej fali cenowej.

#     :param swing_high: Maksimum wybranej fali
#     :param swing_low: Minimum wybranej fali
#     :param trend: "UP" (korekta spada od szczytu) lub "DOWN" (odbicie rośnie od
#     dołka)
#     :return: Słownik w formacie {'38.2': cena, '50.0': cena, '61.8': cena, ...}
#     """
#     if not swing_high or not swing_low or swing_high <= swing_low:
#         return {}

#     diff = swing_high - swing_low
#     ratios = [0.236, 0.382, 0.500, 0.618, 0.786]
#     fibo_dict = {}

#     if trend.upper() == "UP":
#         for r in ratios:
#             fibo_dict[f"{r*100:.1f}"] = round(swing_high - (diff * r), 2)
#     else:
#         for r in ratios:
#             fibo_dict[f"{r*100:.1f}"] = round(swing_low + (diff * r), 2)

#     return fibo_dict