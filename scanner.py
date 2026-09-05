import json
import os
import pandas as pd
import yfinance as yf

from models.stock_analysis import StockAnalysis
from signals.signal_generator import SignalGenerator
from utils.indicators import add_indicators
from download import fetch_data, get_instrument_info
from reports.pdf_generator import generate_summary_pdf_report
from datetime import datetime

from pathlib import Path

OUTPUT_HTML_DIR = Path("output/html")

def calculate_ytd_change(df: pd.DataFrame) -> float | None:
    """Oblicza zmianę procentową YTD (od początku bieżącego roku)."""
    if df.empty or "close" not in df.columns:
        return None

    current_year = pd.Timestamp.now().year

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df_current_year = df[df.index.year == current_year]

    if not df_current_year.empty:
        first_price_year = df_current_year["close"].iloc[0]
        latest_price = df["close"].iloc[-1]
        return ((latest_price - first_price_year) / first_price_year) * 100

    return None


def generate_html_report(results: list, portfolio_name: str = "default", filename: str = None) -> Path:
    """
    Generuje zbiorczy raport HTML z wynikami skanowania i zapisuje go w output/html/
    nazwanym według szablonu: raport_<nazwa_portfela>.html
    """
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        clean_name = Path(portfolio_name).stem.lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = OUTPUT_HTML_DIR / f"raport_{clean_name}_{timestamp}.html"
    else:
        target_path = Path(filename)

    categories_config = [
        ("STRONG_BUY", "🔥 ALERTY TRANSAKCYJNE (Idealne wejście tu i teraz)", "#2ea043"),
        ("WATCHLIST", "👀 LISTA OBSERWACYJNA (Świetna jakość – czekamy na impuls / RR)", "#58a6ff"),
        ("ACCUMULATION", "⏳ KONSOLIDACJA / BUDOWANIE BAZY (Solidna jakość, Szukanie okazji)", "#e3b341"),
        ("REJECTED", "⚠️ ODRZUCONE (Słabość / Trend spadkowy / Sygnał AVOID)", "#f85149"),
    ]

    sections_html = ""

    for cat_key, cat_title, color in categories_config:
        items = results[cat_key]
        rows = ""

        if not items:
            rows = '<tr><td colspan="18" style="text-align: center; color: #8b949e;">Brak spółek w tej kategorii.</td></tr>'
        else:
            for item in items:
                curr = item.get("currency", "")
                company_name = item.get("name", item["ticker"])

                sl_str = f"{item['sl']:.2f} {curr}" if item["sl"] is not None else "Brak"
                tp_str = f"{item['tp']:.2f} {curr}" if item["tp"] is not None else "Brak"

                chg_val = item.get("change_1d")
                if chg_val is not None:
                    chg_color = "#2ea043" if chg_val >= 0 else "#f85149"
                    chg_str = f'<span style="color: {chg_color}; font-weight: bold;">{chg_val:+.2f}%</span>'
                else:
                    chg_str = "N/D"

                ytd_val = item.get("ytd_change")
                if ytd_val is not None:
                    ytd_color = "#2ea043" if ytd_val >= 0 else "#f85149"
                    ytd_str = f'<span style="color: {ytd_color}; font-weight: bold;">{ytd_val:+.2f}%</span>'
                else:
                    ytd_str = "N/D"

                if item["rr"] is not None:
                    rr_color = "#2ea043" if item["rr"] >= 2.0 else ("#e3b341" if item["rr"] >= 1.2 else "#f85149")
                    rr_str = f'<span style="color: {rr_color}; font-weight: bold;">1 : {item["rr"]:.2f}</span>'
                else:
                    rr_str = "N/D"

                supp_str = f"{item['support']:.2f} ({item['dist_supp_pct']:+.1f}%)" if item["support"] is not None else "Brak"
                res_str = f"{item['resistance']:.2f} ({item['dist_res_pct']:+.1f}%)" if item["resistance"] is not None else "ATH"

                target_val = item.get("target_price")
                target_str = f"{target_val:.2f} {curr}" if target_val else "N/D"

                pe_val = item.get("pe_ratio")
                pe_str = f"{pe_val:.1f}" if pe_val else "N/D"

                div_val = item.get("div_yield")
                div_str = f"{div_val*100:.1f}%" if div_val else "0.0%"

                rows += f"""
                <tr>
                    <td><strong>{item['ticker']}</strong></td>
                    <td><span style="color: #8b949e;">{company_name}</span></td>
                    <td>{item['price']:.2f} {curr}</td>
                    <td style="color: #d2a8ff; font-weight: bold;">{target_str}</td>
                    <td>{chg_str}</td>
                    <td>{ytd_str}</td>
                    <td>{pe_str}</td>
                    <td style="color: #7ee787;">{div_str}</td>
                    <td>{supp_str}</td>
                    <td>{res_str}</td>
                    <td style="color: #f85149; font-weight: bold;">{sl_str}</td>
                    <td style="color: #2ea043; font-weight: bold;">{tp_str}</td>
                    <td>{rr_str}</td>
                    <td><span class="badge" style="background-color: #238636;">{item['q_score']} pkt</span></td>
                    <td><span class="badge" style="background-color: #1f6feb;">{item['e_score']} pkt</span></td>
                    <td><span class="badge" style="background-color: #8957e5;">{item['total_score']:.1f}</span></td>
                    <td>{item['obv_status']}</td>
                    <td><strong>{item['trade_signal']}</strong></td>
                </tr>
                """

        sections_html += f"""
        <div class="category-block">
            <h2 style="color: {color}; border-left: 4px solid {color}; padding-left: 10px;">
                {cat_title} <span style="font-size: 0.8em; color: #8b949e;">({len(items)})</span>
            </h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Nazwa Spółki</th>
                        <th>Cena</th>
                        <th>Target</th>
                        <th>1D %</th>
                        <th>YTD %</th>
                        <th>P/E</th>
                        <th>Div %</th>
                        <th>Wsparcie (Dyst. %)</th>
                        <th>Opór (Dyst. %)</th>
                        <th>SL</th>
                        <th>TP</th>
                        <th>RR</th>
                        <th>Qual</th>
                        <th>Entr</th>
                        <th>TOTAL</th>
                        <th>Status OBV</th>
                        <th>Sygnał</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <header>
        <h5 style="color: #ff0000;">⚠️ Uwaga: Gra w inwestowanie na własną odpowiedzialność — strata może zaboleć, gdy wygrasz - podziel się!
        Raport edukacyjny, nie stanowi porady. Kod skanera: <a href="https://github.com/jarok2013-sudo/stock-analyzer" style="color: red;">https://github.com/jarok2013-sudo/stock-analyzer ⚠️</a></h5>
    </header>
    <title>Raport Skanera Giełdowego</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
        .container {{ max-width: 1750px; margin: 0 auto; }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        .category-block {{ margin-bottom: 35px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background-color: #161b22; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #30363d; font-size: 0.9em; }}
        th {{ background-color: #21262d; color: #8b949e; text-transform: uppercase; font-size: 0.78em; letter-spacing: 0.5px; }}
        tr:hover {{ background-color: #1f242c; }}
        .badge {{ color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.85em; font-weight: bold; }}
        header {{  color: red; padding: 1rem; text-align: center;}}
        footer {{  color: red; padding: 1rem; text-align: center;}}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Raport Skanera Giełdowego</h1>
        {sections_html}
    </div>
    <!-- STOPKA STRONY -->
    <footer>
        <h5>⚠️ Disclaimer: For informational and educational purposes only. Not financial advice.
        Investments carry risk of loss — if you win, share the gains; if you lose, it's on you — use at your own risk. 
        <br>Project code: <a href="https://github.com/jarok2013-sudo/stock-analyzer" style="color: red;">https://github.com/jarok2013-sudo/stock-analyzer ⚠️</a></h5>
    </footer>
</body>
</html>
"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[HTML] Raport wygenerowany pomyślnie i zapisany w pliku: {target_path}")


def scan_watchlist(tickers: list[str], portfolio_name: str = "default"):
    results = {
        "STRONG_BUY": [],
        "WATCHLIST": [],
        "ACCUMULATION": [],
        "REJECTED": [],
    }

    if portfolio_name == "positions":
        tickers = [item["symbol"] for item in load_portfolio(portfolio_name)]

    print(f"\n🚀 URUCHAMIANIE SKANERA DLA {len(tickers)} SPÓŁEK...")
    print("=" * 185)

    for ticker in tickers:
        try:
            print(f" ⏳ Analiza: {ticker:<8}...", end="\r")

            df = fetch_data(ticker)

            change_1d = None
            if len(df) >= 2:
                change_1d = ((df["close"].iloc[-1] / df["close"].iloc[-2]) - 1) * 100

            ytd_change = calculate_ytd_change(df)

            df = add_indicators(df)

            analysis = StockAnalysis(ticker, df)
            analysis.run()

            trade_signal = getattr(analysis, "trade_signal", "NEUTRAL")

            info = getattr(analysis, "instrument_info", None) or get_instrument_info(ticker) or {}
            waluta = info.get("currency", "USD")
            company_name = info.get("shortName") or info.get("longName") or ticker

            q_score = getattr(analysis, "quality_score", 0)
            e_score = getattr(analysis, "entry_score", 0)
            total_score = round((q_score * 0.4) + (e_score * 0.6), 1)

            obv_status = "⚪ Płaski"
            if getattr(analysis, "obv_bullish_div", False):
                obv_status = "🚀 Bycza dyw."
            elif getattr(analysis, "obv_bearish_div", False):
                obv_status = "⚠️ Niedźwiedzia dyw."
            elif getattr(analysis, "obv_rising", False):
                obv_status = "🟢 OBV rośnie"

            sl_val = getattr(analysis, "stop_loss", None)
            tp_val = getattr(analysis, "take_profit", None)
            rr_val = getattr(analysis, "risk_reward", None)

            supp_obj = getattr(analysis, "nearest_support", None)
            res_obj = getattr(analysis, "nearest_resistance", None)

            supp_price = supp_obj.get("price") if isinstance(supp_obj, dict) else None
            res_price = res_obj.get("price") if isinstance(res_obj, dict) else None

            price = analysis.price
            dist_supp_pct = ((price - supp_price) / price * 100) if supp_price else 0.0
            dist_res_pct = ((res_price - price) / price * 100) if res_price else 0.0

            item = {
                "ticker": ticker,
                "name": company_name,
                "price": price,
                "currency": waluta,
                "change_1d": change_1d,
                "ytd_change": ytd_change,
                "sl": sl_val,
                "tp": tp_val,
                "rr": rr_val,
                "support": supp_price,
                "resistance": res_price,
                "dist_supp_pct": dist_supp_pct,
                "dist_res_pct": dist_res_pct,
                "q_score": q_score,
                "e_score": e_score,
                "total_score": total_score,
                "obv_status": obv_status,
                "trade_signal": trade_signal,

                # --- NOWE POLA FUNDAMENTALNE ---
                "target_price": getattr(analysis, "target_mean_price", None),
                "pe_ratio": getattr(analysis, "pe_ratio", None),
                "div_yield": getattr(analysis, "dividend_yield", None),
                "rec_key": getattr(analysis, "recommendation_key", "N/D"),
            }

            if trade_signal in ["STRONG BUY", "BUY"]:
                results["STRONG_BUY"].append(item)
            elif trade_signal in ["WATCH", "WAIT"]:
                results["WATCHLIST"].append(item)
            elif q_score >= 45 and trade_signal != "AVOID":
                results["ACCUMULATION"].append(item)
            else:
                results["REJECTED"].append(item)

        except Exception as e:
            print(f"\n❌ Błąd analizy {ticker}: {e}")

    print(" " * 60, end="\r")

    for cat in results:
        results[cat] = sorted(
            results[cat],
            key=lambda x: (x["total_score"], x["e_score"]),
            reverse=True,
        )

    def print_section(title, items, icon):
        print(f"\n{icon} {title} ({len(items)})")
        print("=" * 185)
        if not items:
            print("  Brak spółek w tej kategorii.")
            return

        print(
            f"{'Ticker':<8} | {'Nazwa':<20} | {'Cena':<11} | {'1D %':<7} | {'YTD %':<7} | "
            f"{'Supp %':<8} | {'Res %':<8} | {'SL':<8} | {'TP':<8} | "
            f"{'RR':<6} | {'Qual':<5} | {'Entr':<5} | {'TOTAL':<5} | "
            f"{'Status OBV':<19} | {'Trade Signal':<10}"
        )
        print("-" * 185)
        for res in items:
            chg_str = f"{res['change_1d']:+.2f}%" if res["change_1d"] is not None else "N/D"
            ytd_str = f"{res['ytd_change']:+.2f}%" if res["ytd_change"] is not None else "N/D"
            sl_c = f"{res['sl']:.2f}" if res["sl"] is not None else "N/D"
            tp_c = f"{res['tp']:.2f}" if res["tp"] is not None else "N/D"
            rr_c = f"1:{res['rr']:.2f}" if res["rr"] is not None else "N/D"
            price_str = f"{res['price']:.2f} {res['currency']}"
            
            supp_pct_str = f"-{res['dist_supp_pct']:.1f}%" if res["support"] else "Brak"
            res_pct_str = f"+{res['dist_res_pct']:.1f}%" if res["resistance"] else "ATH"

            # Przycinanie zbyt długich nazw do konsoli
            name_truncated = (res['name'][:18] + '..') if len(res['name']) > 20 else res['name']

            print(
                f"{res['ticker']:<8} | "
                f"{name_truncated:<20} | "
                f"{price_str:<11} | "
                f"{chg_str:>7} | "
                f"{ytd_str:>7} | "
                f"{supp_pct_str:>8} | "
                f"{res_pct_str:>8} | "
                f"{sl_c:<8} | "
                f"{tp_c:<8} | "
                f"{rr_c:<6} | "
                f"{res['q_score']:>3} pkt | "
                f"{res['e_score']:>3} pkt | "
                f"{res['total_score']:>5.1f} | "
                f"{res['obv_status']:<19} | "
                f"{res['trade_signal']:<10}"
            )

    print_section("ALERTY TRANSAKCYJNE (Idealne wejście tu i teraz)", results["STRONG_BUY"], "🔥")
    print_section("LISTA OBSERWACYJNA (Świetna jakość – czekamy na impuls / RR)", results["WATCHLIST"], "👀")
    print_section("KONSOLIDACJA / BUDOWANIE BAZY (Średnia jakość – warta podglądu)", results["ACCUMULATION"], "⏳")
    print_section("ODRZUCONE (Brak trendu / Słabość / Sygnał AVOID)", results["REJECTED"], "⚠️")

    print("\n" + "=" * 185)
    generate_html_report(results,portfolio_name)
    

    generate_summary_pdf_report(results, portfolio_name)


def load_portfolio(portfolio_name: str = "default") -> list:
    if os.path.exists(f"portfolios/{portfolio_name}.json"):
        try:
            with open(f"portfolios/{portfolio_name}.json", "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return []
    return []


if __name__ == "__main__":
    my_watchlist = [
        "NVDA", "AAPL", "MSFT", "AMD", "TSLA", 
        "AMZN", "GOOGL", "META", "PLTR", "NOW", 
        "FWIA.DE", "KRU.WA", "PKO.WA", "CCJ"
    ]

    portfolio = load_portfolio()
    if len(portfolio) != 0:
        my_watchlist = portfolio

    scan_watchlist(my_watchlist)