import yfinance as yf
import pandas as pd
from datetime import datetime
from config import *
from database import save_prices

#DB = "stocks.db"

class InvalidTickerError(Exception):
    """Nie znaleziono instrumentu."""
    pass



def get_instrument_info(symbol: str) -> dict:
    stock = yf.Ticker(symbol)
    info = stock.info or {}
    try:
        calendar = stock.calendar
        if calendar is not None:
            # Sygnalizuje datę nadchodzących wyników
            earnings_date = calendar.get("Earnings Date")
    except Exception as e:
        earnings_date = None

    instrument = {
        "symbol": symbol.upper(),
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "exchange": info.get("exchange"),
        "currency": info.get("currency", "USD"),
        "country": info.get("country"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "quoteType": info.get("quoteType"),
        "currentPrice": info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice"),
        "regularMarketPrice": info.get("regularMarketPrice"),
        "marketCap": info.get("marketCap"),

        # --- Rekomendacje i wyceny Yahoo ---
        "targetMeanPrice": info.get("targetMeanPrice"),
        "targetHighPrice": info.get("targetHighPrice"),
        "targetLowPrice": info.get("targetLowPrice"),
        "recommendationKey": info.get("recommendationKey"),
        "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),

        # --- Fundamenty i Wycena ---
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "priceToBook": info.get("priceToBook"),
        "debtToEquity": info.get("debtToEquity"),
        "totalDebt": info.get("totalDebt"),
        "profitMargins": info.get("profitMargins"),
        "returnOnAssets": info.get("returnOnAssets"),
        "returnOnEquity": info.get("returnOnEquity"),

        "revenueGrowth": info.get("revenueGrowth"),
        "earningsGrowth": info.get("earningsGrowth"),
        "earningsQuarterlyGrowth": info.get("earningsQuarterlyGrowth"),
        "grossMargins": info.get("grossMargins"),
        "operatingMargins": info.get("operatingMargins"),
        "freeCashflow": info.get("freeCashflow"),
        "operatingCashflow": info.get("operatingCashflow"),
        "totalCash": info.get("totalCash"),
        "enterpriseValue": info.get("enterpriseValue"),
        "enterpriseToEbitda": info.get("enterpriseToEbitda"),

        # --- Dywidendy ---
        "dividendYield": info.get("dividendYield"),
        "exDividendDate": info.get("exDividendDate"),
        "payoutRatio": info.get("payoutRatio"),
        
        # --- Wyniki i Kalendarz ---
        "earningsDate": info.get("earningsDate") if info.get("earningsDate") is not None else earnings_date,
        "trailingEps": info.get("trailingEps"),
        "forwardEps": info.get("forwardEps"),
        
        # --- Statystyka Ryzyka i Wolumenu ---
        "beta": info.get("beta"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "averageVolume": info.get("averageVolume"),
        "shortRatio": info.get("shortRatio"),
        "heldPercentInstitutions": info.get("heldPercentInstitutions"),
        
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return instrument

def download_prices(symbol):
    data = yf.download(
        symbol,
        period=DEFAULT_PERIOD,
        interval=DEFAULT_INTERVAL,
        auto_adjust=False
    )
    if data.empty:
        raise InvalidTickerError(
            f"Nie znaleziono notowań dla {symbol}"
        )
    
    

    return data

"""
Przygotowanie danych
spłaszczanie kolumn, 
zamiana nazw kolumn na małe litery, 
czyszczenie NaN dla kluczowych kolumn cenowych
sortowanie danych (od najstarszych do najnowszych)

"""
def prepare_prices(df):
    
    # 1. Spłaszczenie kolumn
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    #małe liter
    df.columns = [c.lower() for c in df.columns]
    # 2. Czyszczenie
    df = clean_prices(df)

    if isinstance(df.index, pd.DatetimeIndex):
        df = df.sort_index()
    elif "Date" in df.columns or "date" in df.columns:
        date_col = "Date" if "Date" in df.columns else "date"
        df = df.sort_values(by=date_col)
    else:
        df = df.copy()    

    return df

def clean_prices(df):

    df = df.dropna(
        subset=["open","high","low","close"]
    )

    df = df[df["volume"] > 0]

    return df

def fetch_data(symbol: str):
    """
    Wykonuje pełną ścieżkę analizy dla JEDNEJ wybranej spółki:
    1. Pobranie i czyszczenie danych
    2. Zapis do bazy danych
    3. Wyliczenie wskaźników
    4. Uruchomienie modelu StockAnalysis
    5. Wygenerowanie wykresu (ChartBuilder)
    6. Wyświetlenie raportu konsolowego i PDF
    7. Wydruk debugujący
    """
    symbol = symbol.upper().strip()
    print(f"\n" + "=" * 65)
    print(f"🚀 URUCHAMIANIE PEŁNEJ ANALIZY DLA: {symbol}")
    print("=" * 65)

    # 1. Pobieranie danych
    try:
        df = download_prices(symbol)
    except InvalidTickerError as e:
        print(f"❌ Błąd: {e}")
        return None
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd pobierania danych dla {symbol}: {e}. Lub nieprawidłowy ticker")
        return None

    # 2. Przygotowanie danych
    df = prepare_prices(df)
    if df.empty:
        print(f"⚠️ Brak danych po oczyszczeniu dla {symbol}. Lub nieprawidłowy ticker")
        return None

    # 3. Zapis do bazy danych
    try:
        save_prices(symbol, df)
    except Exception as e:
        print(f"⚠️ Uwaga: Błąd zapisu do bazy danych: {e}")

    return df



