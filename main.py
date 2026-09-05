import json
import os
import sys
from pathlib import Path

import pandas as pd

# --- IMPORTY TWOICH MODUŁÓW ---
from database import save_prices
from download import fetch_data
from knowledge.indicators import INDICATORS
from models.stock_analysis import StockAnalysis
from reports.report import Report
from reports.report_pdf import generate_pdf_report
from utils.indicators import add_indicators
from reports.pdf_generator import generate_pdf_report

# Podłączenie ChartBuildera
try:
    from charts.chart_builder import ChartBuilder
except ImportError:
    ChartBuilder = None

# Generator HTML / Skaner
try:
    from scanner import scan_watchlist
except ImportError:
    scan_watchlist = None

PORTFOLIOS_DIR = Path("portfolios")
DEFAULT_WATCHLIST = ["NVDA", "AAPL", "MSFT", "AMD", "TSLA", "AMZN", "GOOGL", "META", "PLTR", "NOW"]

# ==============================================================================
# ZARZĄDZANIE PORTFELAMI (WIELE WATCHLIST)
# ==============================================================================


def ensure_portfolios_dir():
    """Tworzy katalog portfolios i domyślną listę, jeśli nie istnieją."""
    PORTFOLIOS_DIR.mkdir(exist_ok=True)
    default_file = PORTFOLIOS_DIR / "default.json"
    if not default_file.exists():
        with open(default_file, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_WATCHLIST, f, indent=4)


def list_portfolios() -> list[Path]:
    """Zwraca listę dostępnych plików portfeli JSON."""
    ensure_portfolios_dir()
    return list(PORTFOLIOS_DIR.glob("*.json"))


def load_portfolio_by_name(name: str) -> list[str]:
    """Wczytuje konkretny portfel na podstawie nazwy pliku."""
    file_path = PORTFOLIOS_DIR / f"{name}.json"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Błąd odczytu portfela {name}: {e}")
    return DEFAULT_WATCHLIST


def save_portfolio_by_name(name: str, tickers: list[str]):
    """Zapisuje listę tickerów do pliku portfela."""
    ensure_portfolios_dir()
    file_path = PORTFOLIOS_DIR / f"{name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(set(tickers))), f, indent=4)


def select_portfolio_interactive() -> tuple[list[str], str]:
    """
    Interaktywne menu wyboru portfela do skanowania.
    :return: Krotka (lista_tickerow, nazwa_portfela)
    """
    files = list_portfolios()
    if not files:
        return DEFAULT_WATCHLIST, "default"

    print("\n📁 DOSTĘPNE PORTFELE / WATCHLISTY:")
    for idx, file in enumerate(files, 1):
        print(f"  {idx}. 📄 {file.stem}")

    choice = input(f"Wybierz portfel (1-{len(files)}) [Domyślnie: 1]: ").strip()
    if not choice:
        name = files[0].stem
        return load_portfolio_by_name(name), name

    try:
        selected_idx = int(choice) - 1
        if 0 <= selected_idx < len(files):
            name = files[selected_idx].stem
            return load_portfolio_by_name(name), name
    except ValueError:
        pass

    print("⚠️ Nieprawidłowy wybór, ładuję domyślny portfel.")
    name = files[0].stem
    return load_portfolio_by_name(name), name


def prompt_add_to_portfolio(symbol: str):
    """Pytanie po analizie ad-hoc: czy dodać ticker do wybranego portfela."""
    symbol = symbol.upper()
    print(f"\n❓ Czy chcesz dodać spółkę {symbol} do swojej watchlisty?")
    choice = input(" [T]ak / [N]ie: ").strip().lower()

    if choice in ["t", "tak", "y", "yes"]:
        files = list_portfolios()
        print("\nWybierz do którego portfela dodać:")
        for idx, file in enumerate(files, 1):
            print(f"  {idx}. 📄 {file.stem}")
        print(f"  {len(files) + 1}. ➕ Utwórz nowy portfel")

        p_choice = input("Wybierz opcję: ").strip()
        try:
            p_idx = int(p_choice) - 1
            if 0 <= p_idx < len(files):
                target_name = files[p_idx].stem
            else:
                target_name = input("Podaj nazwę nowego portfela (np. GPW, ETF): ").strip().lower()
                if not target_name:
                    target_name = "moje_spolki"
        except ValueError:
            target_name = "default"

        current_list = load_portfolio_by_name(target_name)
        if symbol not in current_list:
            current_list.append(symbol)
            save_portfolio_by_name(target_name, current_list)
            print(f"✅ Dodano {symbol} do portfela '{target_name}'!")
        else:
            print(f"ℹ️ Spółka {symbol} znajduje się już w portfelu '{target_name}'.")


# ==============================================================================
# LOGIKA ANALIZY I SKANOWANIA
# ==============================================================================


def analyze_single_symbol(symbol: str, show_chart: bool = True, generate_pdf: bool = True):
    symbol = symbol.upper()
    df = fetch_data(symbol)
    if df is None or df.empty:
        print(f"❌ Brak danych dla symbolu {symbol}.")
        return None

    df = add_indicators(df)
    analysis = StockAnalysis(symbol, df)
    analysis.run()

    if show_chart and ChartBuilder is not None:
        try:
            print("📈 Generowanie interaktywnego wykresu...")
            chart = ChartBuilder(analysis)
            if hasattr(chart, "add_ema"): chart.add_ema()
            if hasattr(chart, "add_macd"): chart.add_macd()
            if hasattr(chart, "add_SMA20"): chart.add_SMA20()

            chart.create()

            if hasattr(chart, "add_support_zones"): chart.add_support_zones()
            if hasattr(chart, "add_resistance_zones"): chart.add_resistance_zones()
            if hasattr(chart, "add_current_price"): chart.add_current_price()
            if hasattr(chart, "add_summary_panel"): chart.add_summary_panel()

            chart.show()
        except Exception as e:
            print(f"⚠️ Nie udało się wygenerować wykresu dla {symbol}: {e}")

    print("\n📋 RAPORT KONSOLOWY:")
    report = Report(analysis)
    report.print()

    if generate_pdf:
        # try:
        #     generate_pdf_report(analysis)
        #     print(f"📄 Raport PDF wygenerowany dla {symbol}.")
        # except Exception as e:
        #     print(f"⚠️ Błąd podczas tworzenia raportu PDF: {e}")
    

        generate_pdf_report(analysis)

    return analysis


def compare_two_symbols(symbol1: str, symbol2: str):
    print(f"\n📊 Analiza porównawcza: {symbol1} vs {symbol2}")

    df1 = fetch_data(symbol1)
    if df1 is None: return
    analysis1 = StockAnalysis(symbol1, add_indicators(df1))
    analysis1.run()

    df2 = fetch_data(symbol2)
    if df2 is None: return
    analysis2 = StockAnalysis(symbol2, add_indicators(df2))
    analysis2.run()

    if ChartBuilder is not None:
        chart1 = ChartBuilder(analysis1)
        if hasattr(chart1, "add_ema"): chart1.add_ema()
        if hasattr(chart1, "add_macd"): chart1.add_macd()
        chart1.create()

        chart2 = ChartBuilder(analysis2)
        if hasattr(chart2, "add_ema"): chart2.add_ema()
        if hasattr(chart2, "add_macd"): chart2.add_macd()
        chart2.create()

        chart1.show(block=False)
        chart2.show(block=False)

    Report(analysis1).print()
    Report(analysis2).print()

    input("\n⌨️  Naciśnij [ENTER], aby kontynuować...")


# ==============================================================================
# MENU GŁÓWNE
# ==============================================================================


def main_menu():
    ensure_portfolios_dir()

    while True:
        print("\n" + "═" * 55)
        print("        📈 STOCK ANALYZER & SCANNER SYSTEM")
        print("═" * 55)
        print("1. 🚀 Skanuj wybraną Watchlistę (Konsola + Raport HTML)")
        print("2. 🔍 Analizuj pojedynczą spółkę (Wykres + PDF + Dodaj do listy)")
        print("3. ⚔️ Porównaj 2 spółki (Wykresy obok siebie)")
        print("4. ⚙️ Zarządzaj Portfelami / Watchlistami")
        print("0. 🚪 Wyjście")
        print("═" * 55)

        choice = input("Wybierz opcję (0-4): ").strip()

        if choice == "1":
            selected_watchlist, portfolio_name = select_portfolio_interactive()
            if scan_watchlist:
                scan_watchlist(selected_watchlist, portfolio_name=portfolio_name)
            else:
                print("⚠️ Brak podłączonego modułu scanner.py!")

        elif choice == "2":
            ticker = input("\nPodaj ticker spółki (np. TSLA, CDR.WA, NVDA): ").strip()
            if ticker:
                res = analyze_single_symbol(ticker, show_chart=True, generate_pdf=True)
                if res is not None:
                    prompt_add_to_portfolio(ticker)

        elif choice == "3":
            s1 = input("Podaj pierwszy ticker (np. AMD): ").strip().upper()
            s2 = input("Podaj drugi ticker (np. INTC): ").strip().upper()
            if s1 and s2:
                compare_two_symbols(s1, s2)

        elif choice == "4":
            print("\n📁 AKTUALNE PORTFELE:")
            files = list_portfolios()
            for f in files:
                data = load_portfolio_by_name(f.stem)
                print(f" • {f.stem:<15} ({len(data)} spółek): {', '.join(data[:6])}{'...' if len(data)>6 else ''}")

            print("\n1. Utwórz nowy portfel")
            print("2. Powrót")
            sub_c = input("Wybierz opcję: ").strip()
            if sub_c == "1":
                name = input("Podaj nazwę nowego portfela: ").strip().lower()
                raw_tickers = input("Podaj tickery po przecinku (np. PKO.WA, PZU.WA): ").strip()
                t_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
                save_portfolio_by_name(name, t_list)
                print(f"✅ Utworzono portfel '{name}' z {len(t_list)} spółkami.")

        elif choice == "0":
            print("\nPraca zakończona. Powodzenia na rynku! 👋")
            sys.exit(0)

        else:
            print("\n⚠️ Nieprawidłowa opcja. Spróbuj ponownie.")


if __name__ == "__main__":
    main_menu()