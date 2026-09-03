from colorama import Fore, Style, init
import pandas as pd
from utils.func import fmt_float

init(autoreset=True)


class Report:

    def __init__(self, analysis):
        self.analysis = analysis
        # Pobieramy walutę dynamicznie dla całego raportu
        self.info = getattr(self.analysis, "instrument_info", {}) or {}
        self.currency = self.info.get("currency", "PLN")

    def print(self):
        self.report_header()
        self.print_dynamic_price_ladder()
        self.report_fundamentals()
        self.report_levels()
        self.report_quality_score()
        self.report_entry_score()
        self.report_trade()
        self.report_checklist()
        self.report_foter()

    def report(self):
        """Alternatywne wywołanie metody print()."""
        self.print()

    def report_header(self):
        #info = getattr(self.analysis, "instrument_info", {}) or {}
        long_name = self.info.get("longName", self.analysis.symbol)
        country = self.info.get("country", "N/A")
        sector = self.info.get("sector", "N/A")
        inst_type = self.info.get("type", "Akcje")

        trend_dict = getattr(self.analysis, "trend", {}) or {}
        trend_code = trend_dict.get("trend", "N/A")
        trend_desc = trend_dict.get("desc", "Brak opisu")

        print("\n" + "#" * 105)
        print("⚠️ Uwaga: Gra w inwestowanie na własną odpowiedzialność — strata może zaboleć, gdy wygrasz - podziel się!")
        print("Raport edukacyjny, nie stanowi porady. Kod skanera: https://github.com/jarok2013-sudo/stock-analyzer ⚠️")
        print( "#" * 105)
        print("\n" )
        print(f"Instrument : {self.analysis.symbol}")
        print(
            f"Full info  : {long_name} ({self.currency}, {country}, {sector}, {inst_type})"
        )
        print(f"Cena       : {self.analysis.price:.2f} {self.currency}")
        print(f"Trend      : {trend_code} - {trend_desc}")
        print()

        ema20_str = fmt_float(getattr(self.analysis, "ema20", None))
        ema50_str = fmt_float(getattr(self.analysis, "ema50", None))
        ema200_str = fmt_float(getattr(self.analysis, "ema200", None))

        print(
            f"EMA20  : {ema20_str:<8} EMA50  : {ema50_str:<8} EMA200 : {ema200_str}"
        )
        print()

        rsi = getattr(self.analysis, "rsi", None)
        macd = getattr(self.analysis, "macd", None)
        signal = getattr(self.analysis, "macd_signal", None)
        atr = getattr(self.analysis, "atr", None)
        vol_ratio = getattr(self.analysis, "vol_ratio", None)

        rsi_str = f"{rsi:.1f}" if rsi is not None else "N/D"
        macd_str = f"{macd:.3f}" if macd is not None else "N/D"
        sig_str = f"{signal:.3f}" if signal is not None else "N/D"
        atr_str = (
            f"{atr:.2f} {self.currency}" if atr is not None else "N/D"
        )
        vol_str = f"{vol_ratio:.2f}x" if vol_ratio is not None else "N/D"

        print(
            f"RSI    : {rsi_str:<8} MACD   : {macd_str:<8} Signal : {sig_str}"
        )
        print(f"ATR(14): {atr_str:<8} Vol/SMA20: {vol_str}")
        print("=" * 70)

    def print_dynamic_price_ladder(self):
        analysis = self.analysis
        price = analysis.price
        currency = self.currency

        levels = []

        # Target Price Analityków w drabinie cenowej
        target_p = getattr(analysis, "target_mean_price", None)
        if target_p:
            dist_target = ((target_p - price) / price) * 100
            levels.append({
                "price": target_p,
                "label_raw": "🎯 TARGET ANALITYKÓW",
                "color": Fore.MAGENTA,
                "detail": f"Potencjał: {dist_target:+.2f}%",
                "type": "TARGET",
            })

        # 1. OPÓR
        res = getattr(analysis, "nearest_resistance", None)
        if res and res.get("price"):
            res_p = res["price"]
            tests = res.get("touches", 1)
            dist = getattr(analysis, "resistance_distance", 0)
            levels.append({
                "price": res_p,
                "label_raw": f"🔴 OPÓR (Resistance) [{tests}x]",
                "color": Fore.RED,
                "detail": f"Odstęp: {dist:.2f}%",
                "type": "RESISTANCE",
            })

        # 2. WSPARCIE
        supp = getattr(analysis, "nearest_support", None)
        if supp and supp.get("price"):
            sup_p = supp["price"]
            tests = supp.get("touches", 1)
            dist = getattr(analysis, "support_distance", 0)
            levels.append({
                "price": sup_p,
                "label_raw": f"🟢 WSPARCIE (Support) [{tests}x]",
                "color": Fore.LIGHTGREEN_EX,
                "detail": f"Odstęp: {dist:.2f}%",
                "type": "SUPPORT",
            })

        # 3. TAKE PROFIT (TP)
        tp_val = getattr(analysis, "take_profit", None)
        if tp_val is not None:
            dist_tp = ((tp_val - price) / price) * 100
            levels.append({
                "price": tp_val,
                "label_raw": "🎯 TAKE PROFIT (TP)",
                "color": Fore.GREEN,
                "detail": f"Zysk: +{dist_tp:.2f}%",
                "type": "TP",
            })

        # 4. STOP LOSS (SL)
        sl_val = getattr(analysis, "stop_loss", None)
        if sl_val is not None:
            dist_sl = ((price - sl_val) / price) * 100
            levels.append({
                "price": sl_val,
                "label_raw": "🛑 STOP LOSS (SL)",
                "color": Fore.LIGHTRED_EX,
                "detail": f"Ryzyko: -{dist_sl:.2f}%",
                "type": "SL",
            })

        # 5. ŚREDNIE KROCZĄCE
        for ema_name in ["ema20", "ema50", "ema200"]:
            ema_val = getattr(analysis, ema_name, None)
            if ema_val is not None:
                levels.append({
                    "price": ema_val,
                    "label_raw": f"🔷 {ema_name.upper()}",
                    "color": Fore.CYAN,
                    "detail": "Średnia",
                    "type": "EMA",
                })

        # 6. AKTUALNA CENA
        levels.append({
            "price": price,
            "label_raw": "💲 AKTUALNA CENA",
            "color": Fore.YELLOW,
            "detail": "Rynkowa",
            "type": "PRICE",
        })

        # Sortowanie od najczytelniejszego (najwyższa cena na górze)
        levels.sort(key=lambda x: x["price"], reverse=True)

        # Renderowanie drabiny
        print("\n" + "=" * 70)
        print(f" 📊 DRABINA POZIOMÓW CENOWYCH: {analysis.symbol}")
        print("=" * 70)

        for i, lvl in enumerate(levels):
            p_str = f"{lvl['price']:.2f} {currency}"
            colored_label = f"{lvl['color']}{lvl['label_raw']:<28}{Style.RESET_ALL}"
            if lvl["type"] == "PRICE":
                print(f" --->  ►► {colored_label} : {p_str:<12} ({lvl['detail']}) ◄◄")
            else:
                print(f"       │  {colored_label} : {p_str:<12} ({lvl['detail']})")
            if i < len(levels) - 1:
                print("       │")
        print("=" * 70)

    def report_levels(self):
        print("\n========== LEVELS ==========")

        dist_s = getattr(self.analysis, "support_distance", None)
        dist_r = getattr(self.analysis, "resistance_distance", None)

        # 1. OBSŁUGA WSPARCIA
        supp = getattr(self.analysis, "nearest_support", None)
        if supp and supp.get("is_atl"):
            print("Support    : BRAK (Spadek poniżej minimów / ATL) ⚠️")
            print("Distance S : N/A")
        elif supp and supp.get("price") is not None:
            touches = supp.get("touches", 1)
            last_test = supp.get("last_test", "Brak daty")
            print(
                f"Support    : {supp['price']:.2f} {self.currency} ({touches}x)  Ostatni test: {last_test}"
            )
            print(
                f"Distance S : {dist_s:.2f}%"
                if dist_s is not None
                else "Distance S : N/A"
            )
        else:
            print("Support    : Nie wyznaczono")
            print("Distance S : N/A")

        # 2. OBSŁUGA OPORU
        res = getattr(self.analysis, "nearest_resistance", None)
        if res and res.get("is_ath"):
            print("Resistance : BRAK (Wybicie szczytów / ATH) 🚀")
            print("Distance R : Otwarta droga do wzrostów")
        elif res and res.get("price") is not None:
            touches = res.get("touches", 1)
            last_test = res.get("last_test", "Brak daty")
            print(
                f"Resistance : {res['price']:.2f} {self.currency} ({touches}x)  Ostatni test: {last_test}"
            )
            print(
                f"Distance R : {dist_r:.2f}%"
                if dist_r is not None
                else "Distance R : N/A"
            )
        else:
            print("Resistance : Nie wyznaczono")
            print("Distance R : N/A")

    def report_quality_score(self):
        print("\n====== QUALITY SCORE ======")
        score = getattr(self.analysis, "quality_score", 0)

        if score >= 80:
            print(f"{Fore.GREEN}● Top okazja (Silny trend, wysoka jakość)")
        elif score >= 65:
            print(f"{Fore.YELLOW}● Dobra spółka (Solidny układ, warta uwagi)")
        elif score >= 50:
            print(f"{Fore.WHITE}● Neutralna / Średniak")
        else:
            print(f"{Fore.RED}● Słaba / Omijaj")

        print(f"Wynik: {score}/100\n")

        for reason in getattr(self.analysis, "quality_reasons", []):
            pts = reason.get("points", 0)
            sign = "+" if pts > 0 else ""
            print(f"{sign}{pts:2d} pkt | {reason.get('text', '')}")

    def report_entry_score(self):
        print("\n======= ENTRY SCORE =======")
        entry_score = getattr(self.analysis, "entry_score", 0)

        if entry_score >= 80:
            print(
                f"{Fore.GREEN}● KUPUJ / SPUST POLUZOWANY (Idealny timing i R/R)"
            )
        elif entry_score >= 65:
            print(
                f"{Fore.YELLOW}● OBSERWUJ / GOTOWOŚĆ (Dobre wejście, blisko bazy)"
            )
        elif entry_score >= 50:
            print(
                f"{Fore.WHITE}● NEUTRALNY / SPASUJ (Słaby moment na naciśnięcie spustu)"
            )
        else:
            print(
                f"{Fore.RED}● ZAKAZ WEJŚCIA (Zły moment, wysokie ryzyko / kupno pod oporem)"
            )

        print(f"Wynik: {entry_score}/100\n")

        for reason in getattr(self.analysis, "entry_reasons", []):
            pts = reason.get("points", 0)
            sign = "+" if pts > 0 else ""
            print(f"{sign}{pts:2d} pkt | {reason.get('text', '')}")

    def report_trade(self):
        print("\n=========== TRADE ==========")
        signal = getattr(self.analysis, "trade_signal", "NEUTRAL")
        rr = getattr(self.analysis, "risk_reward", None)
        sl = getattr(self.analysis, "stop_loss", None)
        tp = getattr(self.analysis, "take_profit", None)

        print(f"Signal      : {signal}")
        print(f"RR          : {rr:.2f}" if rr is not None else "RR          : N/A")
        print(
            f"Stop Loss   : {sl:.2f} {self.currency}"
            if sl is not None
            else "Stop Loss   : N/A"
        )
        print(
            f"Take Profit : {tp:.2f} {self.currency}"
            if tp is not None
            else "Take Profit : N/A"
        )

    def report_checklist(self):
        print("\n======== CHECKLIST ========")

        rr = getattr(self.analysis, "risk_reward", None)
        rsi = getattr(self.analysis, "rsi", None)
        trend = getattr(self.analysis, "trend", {}) or {}

        t_code = trend.get("trend", "N/A")
        t_desc = trend.get("desc", "")

        self._line(
            t_code in ("UP", "STRONG_UP"),
            f"Trend wzrostowy: {t_code} ({t_desc})",
        )

        ema20 = getattr(self.analysis, "ema20", None)
        if ema20 is not None:
            self._line(
                self.analysis.price > ema20,
                f"Cena powyżej EMA20 ({ema20:.2f} {self.currency})",
            )

        macd = getattr(self.analysis, "macd", None)
        macd_sig = getattr(self.analysis, "macd_signal", None)
        if macd is not None and macd_sig is not None:
            self._line(macd > macd_sig, "MACD powyżej linii Signal (Byczy sygnał)")

        if rsi is not None:
            self._line(rsi < 70, f"RSI nieprzegrzany (RSI = {rsi:.1f})")

        self._line(
            rr is not None and rr >= 2.0,
            f"Akceptowalny stosunek Zysk/Ryzyko (RR = {rr:.2f})"
            if rr is not None
            else "RR nieokreślone / zbyt niskie",
        )

    def report_fundamentals(self):
        """Nowa sekcja w konsoli ze szczegółami fundamentów."""
        print("\n======== FUNDAMENTALS & TARGETS ========")
        target = getattr(self.analysis, "target_mean_price", None)
        rec = getattr(self.analysis, "recommendation_key", "N/D")
        pe = getattr(self.analysis, "pe_ratio", None)
        roe = getattr(self.analysis, "roe", None)
        div = getattr(self.analysis, "dividend_yield", None)

        pe_str = f"{pe:.2f}" if pe else "N/D"
        roe_str = f"{roe*100:.1f}%" if roe is not None else "N/D"
        div_str = f"{div:.1f}%" if div is not None else "N/D"
        target_str = f"{target:.2f} {self.currency}" if target else "N/D"

        print(f"Target Analityków : {target_str}")
        print(f"Konsensus         : {str(rec).upper()}")
        print(f"P/E: {pe_str:<12} ROE: {roe_str:<12} Dywidenda: {div_str}")
        print(f"Fund. Score       : {getattr(self.analysis, 'fundamental_score', 0)}/100")

    def report_foter(self):
        print("\n" + "#" * 112)
        print("⚠️ Disclaimer: For informational and educational purposes only. Not financial advice.")
        print(" Investments carry risk of loss — if you win, share the gains; if you lose, it's on you — use at your own risk. \
              \n Project code: https://github.com/jarok2013-sudo/stock-analyzer ⚠️")
        print("#" * 112)

    @staticmethod
    def icon(ok):
        if ok:
            return Fore.GREEN + "✔" + Style.RESET_ALL
        return Fore.RED + "✘" + Style.RESET_ALL

    def _line(self, ok, text):
        print(f"{self.icon(ok)}  {text}")