import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from config import DB
from utils.func import safe_date_str


def load_prices(symbol):

    conn = sqlite3.connect(DB)

    query = """
    SELECT 
        date,
        open,
        high,
        low,
        close,
        volume

    FROM prices

    WHERE symbol=?

    ORDER BY date
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(symbol,)
    )

    conn.close()


    df["date"] = pd.to_datetime(df["date"])

    df.set_index(
        "date",
        inplace=True
    )

    return df

def load_instrument(symbol):

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row  # Zwraca rekordy jako obiekty podobne do słownika
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM instruments WHERE symbol = ?", (symbol,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # Konwertuje wynik bezpośrednio na zwykły słownik w Pythonie
        return dict(row)
    return None



def should_update(symbol: str, max_age_hours: int = 20) -> bool:
    """Sprawdza, czy od ostatniej aktualizacji minęło więcej niż X godzin."""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT updatedAt FROM instruments WHERE symbol = ?", (symbol.upper(),))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            return True  # Brak wpisu – wymuś pobranie
            
        last_update = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_update > timedelta(hours=max_age_hours)

def save_instrument(info: dict, symbol: str) -> dict:
    data = {
        "symbol": symbol.upper(),
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "exchange": info.get("exchange"),
        "currency": info.get("currency", "USD"),
        "country": info.get("country"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "quoteType": info.get("quoteType"),
        
        # Bezpieczne wyznaczenie ceny
        "currentPrice": info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice"),
        
        "targetMeanPrice": info.get("targetMeanPrice"),
        "targetHighPrice": info.get("targetHighPrice"),
        "targetLowPrice": info.get("targetLowPrice"),
        "recommendationKey": info.get("recommendationKey"),
        "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
        
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "priceToBook": info.get("priceToBook"),
        "debtToEquity": info.get("debtToEquity"),
        "totalDebt": info.get("totalDebt"),
        "profitMargins": info.get("profitMargins"),
        "returnOnAssets": info.get("returnOnAssets"),
        "returnOnEquity": info.get("returnOnEquity"),
        
        "dividendYield": info.get("dividendYield"),
        "exDividendDate": safe_date_str(info.get("exDividendDate")),
        "payoutRatio": info.get("payoutRatio"),
        
        "earningsDate": safe_date_str(info.get("earningsDate")),
        "trailingEps": info.get("trailingEps"),
        "forwardEps": info.get("forwardEps"),
        
        "beta": info.get("beta"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "averageVolume": info.get("averageVolume"),
        "shortRatio": info.get("shortRatio"),
        "heldPercentInstitutions": info.get("heldPercentInstitutions"),
        "marketCap": info.get("marketCap"),

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

        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    query = """
    INSERT INTO instruments (
        symbol, shortName, longName, exchange, currency, country, sector, industry, quoteType,
        targetMeanPrice, targetHighPrice, targetLowPrice, recommendationKey, numberOfAnalystOpinions,
        trailingPE, forwardPE, priceToBook, debtToEquity, totalDebt, profitMargins, returnOnAssets, returnOnEquity,
        dividendYield, exDividendDate, payoutRatio,
        earningsDate, trailingEps, forwardEps,
        beta, fiftyTwoWeekHigh, fiftyTwoWeekLow, averageVolume, shortRatio, heldPercentInstitutions,
        updatedAt, currentPrice, marketCap, revenueGrowth, earningsGrowth, earningsQuarterlyGrowth, 
        grossMargins, operatingMargins, freeCashflow, operatingCashflow, totalCash, enterpriseValue, enterpriseToEbitda
    ) VALUES (
        :symbol, :shortName, :longName, :exchange, :currency, :country, :sector, :industry, :quoteType,
        :targetMeanPrice, :targetHighPrice, :targetLowPrice, :recommendationKey, :numberOfAnalystOpinions,
        :trailingPE, :forwardPE, :priceToBook, :debtToEquity, :totalDebt, :profitMargins, :returnOnAssets, :returnOnEquity,
        :dividendYield, :exDividendDate, :payoutRatio,
        :earningsDate, :trailingEps, :forwardEps,
        :beta, :fiftyTwoWeekHigh, :fiftyTwoWeekLow, :averageVolume, :shortRatio, :heldPercentInstitutions,
        :updatedAt, :currentPrice, :marketCap, :revenueGrowth, :earningsGrowth, :earningsQuarterlyGrowth,
        :grossMargins, :operatingMargins, :freeCashflow, :operatingCashflow, :totalCash, :enterpriseValue, :enterpriseToEbitda
    )
    ON CONFLICT(symbol) DO UPDATE SET
        shortName=excluded.shortName,
        longName=excluded.longName,
        exchange=excluded.exchange,
        currency=excluded.currency,
        country=excluded.country,
        sector=excluded.sector,
        industry=excluded.industry,
        quoteType=excluded.quoteType,
        currentPrice=excluded.currentPrice,
        targetMeanPrice=excluded.targetMeanPrice,
        targetHighPrice=excluded.targetHighPrice,
        targetLowPrice=excluded.targetLowPrice,
        recommendationKey=excluded.recommendationKey,
        numberOfAnalystOpinions=excluded.numberOfAnalystOpinions,
        trailingPE=excluded.trailingPE,
        forwardPE=excluded.forwardPE,
        priceToBook=excluded.priceToBook,
        debtToEquity=excluded.debtToEquity,
        totalDebt=excluded.totalDebt,
        profitMargins=excluded.profitMargins,
        returnOnAssets=excluded.returnOnAssets,
        returnOnEquity=excluded.returnOnEquity,
        dividendYield=excluded.dividendYield,
        exDividendDate=excluded.exDividendDate,
        payoutRatio=excluded.payoutRatio,
        earningsDate=excluded.earningsDate,
        trailingEps=excluded.trailingEps,
        forwardEps=excluded.forwardEps,
        beta=excluded.beta,
        fiftyTwoWeekHigh=excluded.fiftyTwoWeekHigh,
        fiftyTwoWeekLow=excluded.fiftyTwoWeekLow,
        averageVolume=excluded.averageVolume,
        shortRatio=excluded.shortRatio,
        heldPercentInstitutions=excluded.heldPercentInstitutions,
        updatedAt=excluded.updatedAt,
        marketCap=excluded.marketCap,
        revenueGrowth=excluded.revenueGrowth,
        earningsGrowth=excluded.earningsGrowth,
        earningsQuarterlyGrowth=excluded.earningsQuarterlyGrowth,
        grossMargins=excluded.grossMargins,
        operatingMargins=excluded.operatingMargins,
        freeCashflow=excluded.freeCashflow,
        operatingCashflow=excluded.operatingCashflow,
        totalCash=excluded.totalCash,
        enterpriseValue=excluded.enterpriseValue,
        enterpriseToEbitda=excluded.enterpriseToEbitda;
    """
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute(query, data)
            conn.commit()
            print(f"Zapisano/Zaktualizowano dane w bazie dla: {symbol}")
    except sqlite3.Error as e:
        print(f"❌ Błąd zapisu do bazy SQL dla {symbol}: {e}")

    return data

def _load_fundamentals_from_db(symbol):
    try:
        with sqlite3.connect(DB) as conn:
            df = pd.read_sql_query("SELECT * FROM instruments WHERE symbol = ?", conn, params=(symbol,))
            if not df.empty:
                return df.iloc[0].to_dict()
    except Exception:
        pass
    return None

def save_prices(symbol,data):

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()


    for index, row in data.iterrows():

        cursor.execute("""
        INSERT OR IGNORE INTO prices
        (
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume
        )
        VALUES (?,?,?,?,?,?,?)
        """,

        (
        symbol,
        index.strftime("%Y-%m-%d"),
        float(row["open"]),
        float(row["high"]),
        float(row["low"]),
        float(row["close"]),
        int(row["volume"])
        ))

    conn.commit()
    conn.close()


def create_database():

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()


    cursor.execute("""
        CREATE TABLE instruments (
    symbol TEXT PRIMARY KEY,
    shortName TEXT,
    longName TEXT,
    exchange TEXT,
    currency TEXT,
    country TEXT,
    sector TEXT,
    industry TEXT,
    quoteType TEXT,
    targetMeanPrice REAL,
    targetHighPrice REAL,
    targetLowPrice REAL,
    recommendationKey TEXT,
    numberOfAnalystOpinions INTEGER,
    trailingPE REAL,
    forwardPE REAL,
    priceToBook REAL,
    debtToEquity REAL,
    totalDebt REAL,
    profitMargins REAL,
    returnOnAssets REAL,
    returnOnEquity REAL,
    dividendYield REAL,
    exDividendDate TEXT,
    payoutRatio REAL,
    earningsDate TEXT,
    trailingEps REAL,
    forwardEps REAL,
    beta REAL,
    fiftyTwoWeekHigh REAL,
    fiftyTwoWeekLow REAL,
    averageVolume INTEGER,
    shortRatio REAL,
    heldPercentInstitutions REAL,
    updatedAt DATETIME,
    currentPrice REAL, 
    marketCap REAL, 
    revenueGrowth REAL, 
    earningsGrowth REAL, 
    earningsQuarterlyGrowth REAL, 
    grossMargins REAL, 
    operatingMargins REAL, 
    freeCashflow REAL, 
    operatingCashflow REAL, 
    totalCash REAL, 
    enterpriseValue REAL, 
    enterpriseToEbitda REAL)
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prices (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,

        UNIQUE(symbol,date)

    )
    """)


    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print("Baza gotowa")