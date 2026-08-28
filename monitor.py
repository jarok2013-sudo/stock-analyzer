import json
import os
import requests
import yfinance as yf

# Ścieżka do pliku z Twoim portfelem
PORTFOLIO_FILE = "portfolios/positions.json"

# Opcjonalne powiadomienia na Telegram (darmowe i bardzo wygodne)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TUTAJ_WKLEJ_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "TUTAJ_WKLEJ_CHAT_ID")


def send_telegram_alert(message: str):
    """Wysyła alert bezpośrednio na Twój telefon przez Telegram."""
    if TELEGRAM_BOT_TOKEN == "TWÓJ_BOT_TOKEN":
        print(f"[ALERT] {message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Błąd wysyłania alertu: {e}")


def check_positions():
    """Sprawdza aktualne ceny dla otwartych pozycji i porównuje z SL/TP."""
    if not os.path.exists(PORTFOLIO_FILE):
        print("Brak pliku portfolio.json. Utwórz go, aby monitorować pozycje.")
        return

    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    print("🔍 Sprawdzanie otwartych pozycji...\n")

    for item in portfolio:
        symbol = item["symbol"]
        buy_price = item["buy_price"]
        sl = item["stop_loss"]
        tp = item["take_profit"]

        ticker = yf.Ticker(symbol)
        current_price = ticker.fast_info.get("lastPrice")

        if not current_price:
            print(f"❌ Nie udało się pobrać ceny dla {symbol}")
            continue

        pnl_pct = ((current_price - buy_price) / buy_price) * 100
        print(
            f"📈 {symbol} | Kupno: {buy_price:.2f} | Aktualna: {current_price:.2f} PLN ({pnl_pct:+.2f}%)"
        )

        # 1. Sprawdzenie STOP LOSS
        if current_price <= sl:
            msg = (
                f"🚨 **ALERT: STOP LOSS PRZEKROCZONY!**\n\n"
                f"Spółka: **{symbol}**\n"
                f"Aktualna cena: **{current_price:.2f} PLN** <= SL ({sl:.2f} PLN)\n"
                f"Rozważ natychmiastowe zamknięcie pozycji na giełdzie!"
            )
            send_telegram_alert(msg)

        # 2. Sprawdzenie TAKE PROFIT
        elif current_price >= tp:
            msg = (
                f"🎯 **ALERT: TAKE PROFIT OSIĄGNIĘTY!**\n\n"
                f"Spółka: **{symbol}**\n"
                f"Aktualna cena: **{current_price:.2f} PLN** >= TP ({tp:.2f} PLN)\n"
                f"Czas na realizację zysku!"
            )
            send_telegram_alert(msg)


if __name__ == "__main__":
    check_positions()