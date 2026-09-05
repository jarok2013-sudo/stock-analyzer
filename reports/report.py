from colorama import Fore, Style, init
import pandas as pd
from utils.func import fmt_float, _safe_number
from utils import interpreter as interp

init(autoreset=True)


class Report:

    def __init__(self, analysis):
        self.analysis = analysis
        self.info = getattr(self.analysis, "instrument_info", {}) or {}
        self.currency = self.info.get("currency", "PLN")

    def print(self):
        self.report_header()
        self.print_dynamic_price_ladder()
        self.report_levels()
        self.report_total_score()
        self.report_sentiment_score()
        self.report_fundamental_score()
        self.report_quality_score()
        self.report_entry_score()
        self.report_trade()
        self.report_checklist()
        self.report_foter()

    def report(self):
        """Alternatywne wywołanie metody print()."""
        self.print()

    def report_header(self):
        long_name = self.info.get("longName", self.analysis.symbol)
        country = self.info.get("country", "N/A")
        sector = self.info.get("sector", "N/A")
        inst_type = self.info.get("type", "Akcje")

        trend_dict = getattr(self.analysis, "trend", {}) or {}
        t_code = trend_dict.get("trend", "N/A")
        t_desc = trend_dict.get("desc", "Brak opisu")

        print("\n" + "#" * 105)
        print(
            "⚠️ Uwaga: Gra w inwestowanie na własną odpowiedzialność — strata może zaboleć, gdy wygrasz - podziel się!"
        )
        print(
            "Raport edukacyjny, nie stanowi porady. Kod skanera: https://github.com/jarok2013-sudo/stock-analyzer ⚠️"
        )
        print("#" * 105 + "\n")

        print(f"Instrument   : {self.analysis.symbol} ({long_name})")
        print(f"Giełda/Sektor: {country} | {sector} | {inst_type}")
        print(f"Cena Rynkowa : {self.analysis.price:.2f} {self.currency}")
        print(f"Status Trendu: {t_code} ({t_desc})")
        print("-" * 75)

        # WSKAŹNIKI I INTERPRETER
        rsi_val = getattr(self.analysis, "rsi", None)
        macd_val = getattr(self.analysis, "macd", None)
        sig_val = getattr(self.analysis, "macd_signal", None)
        vol_val = getattr(self.analysis, "vol_ratio", None)
        atr_val = getattr(self.analysis, "atr", None)

        # Bezpieczne pobranie struktury MACD
        macd_data = interp.interpret_macd(macd_val, sig_val)
        if isinstance(macd_data, dict):
            m_str = macd_data.get("macd", fmt_float(macd_val, 3))
            s_str = macd_data.get("signal", fmt_float(sig_val, 3))
            st_str = macd_data.get("status", "")
            macd_fmt = f"MACD {m_str} / Signal: {s_str} ➔ {st_str}"
        else:
            macd_fmt = str(macd_data)

        print(f"Pęd (RSI 14)    : {interp.interpret_rsi(rsi_val)}")
        print(f"Sygnał MACD     : {macd_fmt}")
        print(
            f"Zmienność (ATR) : {interp.interpret_atr(atr_val, self.analysis.price, self.currency)}"
        )
        print(f"Aktywność Vol   : {interp.interpret_volume(vol_val)}")
        print("=" * 75)

    def print_dynamic_price_ladder(self):
        analysis = self.analysis
        price = analysis.price
        currency = self.currency

        levels = []

        # 1. TARGETY ANALITYKÓW (z dynamicznym wyróżnieniem statusu)
        target_defs = [
            ("targetHighPrice", "🏛️ TARGET MAX (Analitycy)", "MAX"),
            ("targetMeanPrice", "🏛️ TARGET ŚREDNI (Analitycy)", "AVG"),
            ("targetLowPrice", "🏛️ TARGET MIN (Analitycy)", "MIN"),
        ]

        for key, label_base, t_type in target_defs:
            t_price = self.info.get(key, None)
            if t_price is not None and t_price > 0:
                dist_target = ((t_price - price) / price) * 100
                
                # Dostosowanie ikony i opisu w zależności od tego, czy target jest powyżej czy poniżej ceny
                if t_price >= price:
                    detail_str = f"Potencjał: +{dist_target:.2f}%"
                    label_str = label_base
                else:
                    detail_str = f"Cena wyżej o: {abs(dist_target):.2f}%"
                    label_str = label_base.replace("🏛️", "⚠️")  # Ostrzeżenie: cena wyprzedza target

                levels.append({
                    "price": t_price,
                    "label_raw": label_str,
                    "color": Fore.MAGENTA,
                    "detail": detail_str,
                    "type": "TARGET",
                })

        # 2. NAJBLIŻSZY OPÓR (Nad ceną)
        res = getattr(analysis, "nearest_resistance", None)
        if res and res.get("price") and res["price"] > price:
            res_p = res["price"]
            tests = res.get("touches", 1)
            dist = getattr(analysis, "resistance_distance", 0)
            levels.append({
                "price": res_p,
                "label_raw": f"🔴 OPÓR (Resistance) [{tests}x]",
                "color": Fore.RED,
                "detail": f"Odstęp: +{dist:.2f}%",
                "type": "RESISTANCE",
            })

        # 3. PRZEBITE OPORY / STREFY RE-TESTU (Pod ceną)
        rated_resistances = getattr(analysis, "rated_resistances", [])
        broken = [
            r for r in rated_resistances
            if isinstance(r, dict) and r.get("price") and r["price"] < price
        ]
        if broken:
            # Najbliższy przełamany opór pod ceną (np. 156.67 PLN)
            last_broken = max(broken, key=lambda x: x["price"])
            b_price = last_broken["price"]
            dist_b = ((price - b_price) / price) * 100
            
            # Zapobiegamy dublowaniu, jeśli ten sam poziom jest oznaczony jako główne wsparcie
            supp_price = getattr(analysis, "nearest_support", {}).get("price") if getattr(analysis, "nearest_support", None) else None
            if not supp_price or abs(b_price - supp_price) > 0.01:
                levels.append({
                    "price": b_price,
                    "label_raw": "🟢 WSPARCIE (Dawny Opór/Flip)",
                    "color": Fore.LIGHTGREEN_EX,
                    "detail": f"Odstęp: -{dist_b:.2f}%",
                    "type": "SUPPORT_FLIP",
                })

        # 4. GŁÓWNE WSPARCIE
        supp = getattr(analysis, "nearest_support", None)
        if supp and supp.get("price"):
            sup_p = supp["price"]
            tests = supp.get("touches", 1)
            dist = getattr(analysis, "support_distance", 0)
            levels.append({
                "price": sup_p,
                "label_raw": f"🟢 WSPARCIE (Support) [{tests}x]",
                "color": Fore.GREEN,
                "detail": f"Odstęp: -{dist:.2f}%",
                "type": "SUPPORT",
            })

        # 5. TAKE PROFIT (TP)
        tp_val = getattr(analysis, "take_profit", None)
        if tp_val is not None:
            dist_tp = ((tp_val - price) / price) * 100
            levels.append({
                "price": tp_val,
                "label_raw": "🎯 TAKE PROFIT (TP)",
                "color": Fore.LIGHTCYAN_EX,
                "detail": f"Zysk: {dist_tp:+.2f}%",
                "type": "TP",
            })

        # 6. STOP LOSS (SL)
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

        # 7. ŚREDNIE EMA
        for ema_name in ["ema20", "ema50", "ema200"]:
            ema_val = getattr(analysis, ema_name, None)
            if ema_val is not None:
                dist_ema = ((ema_val - price) / price) * 100
                levels.append({
                    "price": ema_val,
                    "label_raw": f"🔷 {ema_name.upper()}",
                    "color": Fore.CYAN,
                    "detail": f"Średnia ({dist_ema:+.2f}%)",
                    "type": "EMA",
                })

        # 8. AKTUALNA CENA
        levels.append({
            "price": price,
            "label_raw": "💲 AKTUALNA CENA",
            "color": Fore.YELLOW,
            "detail": "Rynkowa",
            "type": "PRICE",
        })

        # Sortowanie poziomów od najpotężniejszego (najwyższa cena) do najniższego
        levels.sort(key=lambda x: x["price"], reverse=True)

        print("\n" + "=" * 70)
        print(f" 📊 DRABINA POZIOMÓW CENOWYCH: {analysis.symbol}")
        print("=" * 70)

        for i, lvl in enumerate(levels):
            p_str = f"{lvl['price']:.2f} {currency}"
            colored_label = f"{lvl['color']}{lvl['label_raw']:<32}{Style.RESET_ALL}"
            
            if lvl["type"] == "PRICE":
                print(f" --->  ►► {colored_label} : {p_str:<12} ({lvl['detail']}) ◄◄")
            else:
                print(f"       │  {colored_label} : {p_str:<12} ({lvl['detail']})")
            
            if i < len(levels) - 1:
                print("       │")
                
        print("=" * 70)

    def report_levels(self):
        print("\n========== KLUCZOWE POZIOMY I UKŁAD ŚREDNICH ==========")
        price = self.analysis.price

        print("\n📌 POŁOŻENIE CENY WZGLĘDEM ŚREDNICH (EMA):")
        ema20 = getattr(self.analysis, "ema20", None)
        ema50 = getattr(self.analysis, "ema50", None)
        ema200 = getattr(self.analysis, "ema200", None)

        print(
            "  • "
            + interp.interpret_ema_position(
                price, ema20, "EMA20 (Krótkoterminowa)", self.currency
            )
        )
        print(
            "  • "
            + interp.interpret_ema_position(
                price, ema50, "EMA50 (Średnioterminowa)", self.currency
            )
        )
        print(
            "  • "
            + interp.interpret_ema_position(
                price, ema200, "EMA200 (Długoterminowa)", self.currency
            )
        )

        print("\n🛡 POZIOMY WSPARCIA I OPORU:")
        supp = getattr(self.analysis, "nearest_support", None)
        res = getattr(self.analysis, "nearest_resistance", None)
        dist_s = getattr(self.analysis, "support_distance", None)
        dist_r = getattr(self.analysis, "resistance_distance", None)

        price_val = getattr(self.analysis, "price", None)
        rated_resistances = getattr(self.analysis, "rated_resistances", [])

        # WSPARCIE
        if supp and supp.get("price"):
            s_price = supp["price"]
            s_touches = supp.get("touches", 1)
            dist_str = interp.interpret_distance(dist_s, is_support=True) if dist_s is not None else "N/A"
            print(f"  • Najbliższe Wsparcie : {s_price:.2f} {self.currency} [{s_touches}x testy] ➔ Odstęp: {dist_str}")
        else:
            print("  • Najbliższe Wsparcie : BRAK / Nie wyznaczono")

        # OPÓR
        res_info = interp.interpret_resistance(
            resistance=res,
            rated_resistances=rated_resistances,
            price=price_val,
            resistance_distance=dist_r,
            currency=self.currency,
        )
        print(f"  • Najbliższy Opór     : {res_info}")

    def report_total_score(self):
        print("\n========================================================================")
        print("                     📊 TOTAL SCORE & CONFIDENCE                        ")
        print("========================================================================")

        confidence = self.analysis.calculate_confidence()

        s_score = getattr(self.analysis, "analyst_sentiment_score", getattr(self.analysis, "sentiment_score", 0)) or 0
        f_score = getattr(self.analysis, "fundamental_score", 0) or 0
        q_score = getattr(self.analysis, "quality_score", 0) or 0
        e_score = getattr(self.analysis, "entry_score", 0) or 0
        rr = getattr(self.analysis, "risk_reward", 0) or 0

        print(f"  Analyst Sentiment : {s_score:3d}/100 [Waga: 15%]")
        print(f"  Fundamentals      : {f_score:3d}/100 [Waga: 25%]")
        print(f"  Quality Score     : {q_score:3d}/100 [Waga: 25%]")
        print(f"  Entry Score       : {e_score:3d}/100 [Waga: 35%]")
        print("  ----------------------------------------")

        bar_length = 20
        filled_length = int(bar_length * confidence // 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        if rr <= 0 or e_score == 0:
            status_txt = f"{Fore.RED}REJECTED 🛑 (Brak profilu R/R lub błędny punkt wejścia){Style.RESET_ALL}"
        elif confidence >= 80:
            status_txt = f"{Fore.GREEN}{confidence:.1f}% 🟢 [WYSOKA PEWNOŚĆ / STRONG SETUP]{Style.RESET_ALL}"
        elif confidence >= 60:
            status_txt = f"{Fore.YELLOW}{confidence:.1f}% 🟡 [UMIARKOWANA PEWNOŚĆ / WATCHLIST]{Style.RESET_ALL}"
        else:
            status_txt = f"{Fore.RED}{confidence:.1f}% 🔴 [NISKA PEWNOŚĆ / OMIJAJ]{Style.RESET_ALL}"

        print(f"  CONFIDENCE INDEX  : [{bar}] {status_txt}")

    def report_sentiment_score(self):
        print("\n===== ANALYST SENTIMENT SCORE =====")
        score = getattr(self.analysis, "analyst_sentiment_score", getattr(self.analysis, "sentiment_score", 0))

        if score >= 80:
            print(f"{Fore.GREEN}● Bardzo silny byczy konsensus analityków")
        elif score >= 65:
            print(f"{Fore.YELLOW}● Pozytywne nastawienie Wall Street")
        elif score >= 50:
            print(f"{Fore.WHITE}● Neutralny sentyment analityków")
        else:
            print(f"{Fore.RED}● Negatywny konsensus / Słaby potencjał")

        print(f"Wynik: {score}/100\n")

        reasons = getattr(self.analysis, "analyst_sentiment_reasons", getattr(self.analysis, "sentiment_reasons", []))
        for reason in reasons:
            pts = reason.get("points", 0)
            sign = "+" if pts > 0 else ""
            print(f"{sign}{pts:2d} pkt | {reason.get('text', '')}")

    def report_fundamental_score(self):
        print("\n====== FUNDAMENTAL SCORE ======")
        score = getattr(self.analysis, "fundamental_score", 0)

        if score >= 80:
            print(f"{Fore.GREEN}● Wybitne fundamenty (Świetna wzrostowość i rentowność)")
        elif score >= 65:
            print(f"{Fore.YELLOW}● Zdrowa spółka (Dobre wskaźniki fin.)")
        elif score >= 50:
            print(f"{Fore.WHITE}● Średnia kondycja finansowa")
        else:
            print(f"{Fore.RED}● Zagrożone fundamenty / Wysokie ryzyko")

        print(f"Wynik: {score}/100\n")

        for reason in getattr(self.analysis, "fundamental_reasons", []):
            pts = reason.get("points", 0)
            sign = "+" if pts > 0 else ""
            print(f"{sign}{pts:2d} pkt | {reason.get('text', '')}")

    def report_quality_score(self):
        print("\n====== QUALITY SCORE ======")
        score = getattr(self.analysis, "quality_score", 0)

        if score >= 80:
            print(f"{Fore.GREEN}● Top okazja techniczna (Silny trend, układ byczy)")
        elif score >= 65:
            print(f"{Fore.YELLOW}● Dobra struktura wykresu")
        elif score >= 50:
            print(f"{Fore.WHITE}● Neutralna / Konsolidacja")
        else:
            print(f"{Fore.RED}● Słaby trend / Omijaj")

        print(f"Wynik: {score}/100\n")

        for reason in getattr(self.analysis, "quality_reasons", []):
            pts = reason.get("points", 0)
            sign = "+" if pts > 0 else ""
            print(f"{sign}{pts:2d} pkt | {reason.get('text', '')}")

    def report_entry_score(self):
        print("\n======= ENTRY SCORE =======")
        entry_score = getattr(self.analysis, "entry_score", 0)
        price = getattr(self.analysis, "price", None)
        res = getattr(self.analysis, "nearest_resistance", None)
        rated_resistances = getattr(self.analysis, "rated_resistances", [])

        
        # Wykrycie wybicia oporu / szczytu (ATH)
        # 1. Filtrujemy opory, które znajdują się strictly NAD aktualną ceną
        active_resistances_above = [
            r for r in rated_resistances
            if isinstance(r, dict) 
            and _safe_number(r.get("price")) is not None 
            and _safe_number(r.get("price")) > price
        ]

        # 2. ATH zachodzi tylko wtedy, gdy NIE MA żadnego oporu nad ceną
        is_ath = (
            getattr(self.analysis, "is_ath", False)
            or (res and res.get("is_ath", False))
            or (len(active_resistances_above) == 0)
        )
        

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
            if is_ath:
                print(
                    f"{Fore.RED}● ZAKAZ WEJŚCIA (Wykupienie / Ryzyko korekty po wybiciu ATH)"
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

        confidence = getattr(self.analysis, "confidence", 0) or 0
        rr = getattr(self.analysis, "risk_reward", None)
        sl = getattr(self.analysis, "stop_loss", None)
        tp = getattr(self.analysis, "take_profit", None)

        if confidence >= 80:
            signal = f"{Fore.GREEN}BUY (Strong Setup){Style.RESET_ALL}"
        elif confidence >= 60:
            signal = f"{Fore.YELLOW}ACCUMULATE / WATCH{Style.RESET_ALL}"
        else:
            signal = f"{Fore.RED}AVOID / NO TRADE{Style.RESET_ALL}"

        print(f"Signal      : {signal}")
        print(f"Confidence  : {confidence:.1f}%")
        print(f"RR Ratio    : {interp.interpret_risk_reward(rr)}")
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

        trend_dict = getattr(self.analysis, "trend", {}) or {}
        t_code = trend_dict.get("trend", "N/A")
        t_desc = trend_dict.get("desc", "")
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

        quality_reasons = getattr(self.analysis, "quality_reasons", [])
        macd_reason = next(
            (
                r["text"]
                for r in quality_reasons
                if "MACD" in r.get("text", "").upper()
            ),
            None,
        )

        macd = getattr(self.analysis, "macd", None)
        macd_sig = getattr(self.analysis, "macd_signal", None)

        if macd_reason:
            is_macd_ok = macd is not None and macd_sig is not None and macd > macd_sig
            self._line(is_macd_ok, f"MACD: {macd_reason}")
        elif macd is not None and macd_sig is not None:
            is_macd_ok = macd > macd_sig
            status_txt = "powyżej" if is_macd_ok else "poniżej"
            self._line(
                is_macd_ok,
                f"MACD ({macd:.3f}) {status_txt} linii Signal ({macd_sig:.3f})",
            )

        rsi = getattr(self.analysis, "rsi", None)
        if rsi is not None:
            self._line(rsi < 70, f"RSI nieprzegrzany (RSI = {rsi:.1f})")

        rr = getattr(self.analysis, "risk_reward", None)
        self._line(
            rr is not None and rr >= 2.0,
            f"Akceptowalny stosunek Zysk/Ryzyko (RR = {rr:.2f})"
            if rr is not None
            else "RR nieokreślone / zbyt niskie",
        )

    def report_foter(self):
        print("\n" + "#" * 112)
        print("⚠️ Disclaimer: For informational and educational purposes only. Not financial advice.")
        print(
            " Investments carry risk of loss — if you win, share the gains; if you lose, it's on you — use at your own risk.\n"
            " Project code: https://github.com/jarok2013-sudo/stock-analyzer ⚠️"
        )
        print("#" * 112)

    @staticmethod
    def icon(ok):
        if ok:
            return Fore.GREEN + "✔" + Style.RESET_ALL
        return Fore.RED + "✘" + Style.RESET_ALL

    def _line(self, ok, text):
        print(f"{self.icon(ok)}  {text}")