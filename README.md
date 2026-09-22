# 🚀 Stock Analyzer & Portfolio Monitor

Kompleksowy system w języku Python przeznaczony do automatycznej analizy technicznej i fundamentalnej instrumentów finansowych (akcje, ETF-y, kontrakty CFD) oraz bieżącego monitorowania otwartych pozycji portfela z powiadomieniami w czasie rzeczywistym.

---

## 📋 Spis treści

* [O projekcie]
* [Główne funkcjonalności]
* [Wymagania i Instalacja]
* [Szybki start]
* [Konfiguracja Monitora Pozycji (`monitor.py`)]
* [Automatyzacja w tle (Linux Cron)]
* [Licencja i Warunki Użytkowania]
---

## 🎯 O projekcie

Projekt służy do wspomagania decyzji inwestycyjnych i tradingowych poprzez połączenie:

1. **Analizy Technicznej i Fundamentalnej:** Wyliczanie punktacji (*Quality Score*, *Entry Score*, *Confidence Index*) dla wskazanych walorów na podstawie wskaźników cenowych (EMA, RSI, MACD, ATR) oraz danych sprawozdawczych ($P/E$, $P/B$, ROE, dywidendy).
2. **Narzędzia Wykonawczego (CFD/Akcje/ETF):** Wykorzystania czystych rynkowych danych historycznych z Yahoo Finance jako silnika analitycznego do generowania sygnałów dla akcji oraz ich pochodnych instrumentów CFD[cite: 2].
3. **Pętli Monitorującej (`monitor.py`):** Śledzenia cen w czasie rzeczywistym dla otwartych pozycji, pilnowania poziomów *Stop Loss* ($SL$) / *Take Profit* ($TP$) oraz wysyłania alertów na komunikator Telegram[cite: 2].

---

## ✨ Główne funkcjonalności

* **Automatyczna drabina poziomów cenowych:** Wyznaczanie kluczowych oporów, wsparć oraz dynamicznych średnich ($EMA20$, $EMA50$, $EMA200$).
* **Zbalansowany scoring:** Podział na *Analyst Sentiment*, *Fundamentals*, *Quality Score* oraz *Entry Score*.
* **Generowanie raportów i wykresów:** Export wyników do konsoli, plików PDF oraz generowanie wykresów z wstęgami i wskaźnikami impetu.
* **Aktywne alerty $SL/TP$:** Automatyczne sprawdzanie warunków wyjścia z pozycji i natychmiastowe powiadomienia na telefon[cite: 2].

---

## 💻 Wymagania i Instalacja

### Wymagania wstępne

* **Python:** v3.10 lub nowszy
* **Git:** Zainstalowany w systemie

### 1. Pobranie kodu (Klonowanie)

Otwórz terminal (lub wiersz poleceń) i sklonuj repozytorium:

```bash
git clone https://github.com/jarok2013-sudo/stock-analyzer.git
cd nazwa-repozytorium

```

### 2. Utworzenie wirtualnego środowiska `venv`

* **Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate

```


* **Windows (CMD / PowerShell):**
```cmd
python -m venv venv
venv\Scripts\activate

```



### 3. Instalacja zależności

Pobierz pakiete wymagane do uruchomienia projektu (`yfinance`, `pandas`, `requests`, `matplotlib` itp.):

```bash
pip install -r requirements.txt

```

---

## ⚡ Szybki start

Po aktywacji środowiska `venv` możesz od razu uruchomić główny analizator rynku:

```bash
python main.py

```
Do szybszej analizy
Skanowanei wszystkich portfeli

```bash
python scanner_zbiorczy.py

```

---

## 🔔 Konfiguracja Monitora Pozycji (`monitor.py`)

Skrypt `monitor.py` odpowiada za automatyczną kontrolę otwartych transakcji w Twoim portfelu[cite: 2].

### 1. Przygotowanie pliku pozycji

Utwórz katalog `portfolios/` oraz plik `portfolios/positions.json` zawierający zestawienie Twoich pozycji[cite: 2]:

```json
[
  {
    "symbol": "KGH.WA",
    "buy_price": 334.50,
    "stop_loss": 318.69,
    "take_profit": 370.20
  },
  {
    "symbol": "PKN.WA",
    "buy_price": 65.00,
    "stop_loss": 61.50,
    "take_profit": 72.00
  }
]

```

### 2. Powiadomienia Telegram (Opcjonalnie)

Aby otrzymywać powiadomienia $SL/TP$ bezpośrednio na telefon[cite: 2]:

1. Stwórz bota przez `@BotFather` na Telegramie i pobierz token API.
2. Pobierz swój prywatny `CHAT_ID` (np. przez `@userinfobot`).
3. Ustaw zmienne środowiskowe w systemie przed uruchomieniem skryptu[cite: 2]:

* **Linux / macOS:**
```bash
export TELEGRAM_BOT_TOKEN="Twój_Token_Bota"
export TELEGRAM_CHAT_ID="Twój_Chat_ID"

```


* **Windows (CMD):**
```cmd
set TELEGRAM_BOT_TOKEN="Twój_Token_Bota"
set TELEGRAM_CHAT_ID="Twój_Chat_ID"

```



### 3. Ręczne sprawdzenie pozycji

Aby uruchomić jednorazowy sprawdzian otwartych pozycji[cite: 2]:

```bash
python monitor.py

```

---

## 🕒 Automatyzacja w tle (Linux Cron)

Aby skrypt `monitor.py` automatycznie sprawdzał stan Twojego portfela w tle (np. co 15 minut w dni robocze od poniedziałku do piątku), dodaj zadanie do demona `cron`:

1. Otwórz edytor zadań crona:
```bash
crontab -e

```


2. Dodaj wpis (dostosuj ścieżkę do swojego projektu):
```bash
*/15 * * * 1-5 cd /sciezka/do/projekty && /sciezka/do/projekty/venv/bin/python monitor.py >> monitor.log 2>&1

```



---

## 📜 Licencja i Warunki Użytkowania

Projekt udostępniany jest na zasadach otwartej licencji **Copyleft** (np. GNU General Public License v3.0 / CC BY-SA 4.0).

### Warunki użytkowania:

* **Wolność użycia i modyfikacji:** Masz pełne prawo do uruchamiania, analizowania, ulepszania i dostosowywania kodu do własnych celów edukacyjnych i prywatnych.
* **Obowiązek udostępniania źródła (Copyleft):** Jeśli zmodyfikujesz ten kod lub wykorzystasz go jako bazę do własnego projektu i będziesz go rozpowszechniać, **masz obowiązek udostępnić pełny kod źródłowy publicznie** na tej samej licencji i tych samych warunkach.
* **Wyłączenie odpowiedzialności (Disclaimer):** Oprogramowanie dostarczane jest w stanie takim, jakim jest (*AS IS*). Autorzy nie ponoszą odpowiedzialności za decyzje inwestycyjne ani ewentualne straty finansowe wynikające z użycia tego programu. Wygenerowane analizy mają charakter wyłącznie edukacyjny i informacyjny.