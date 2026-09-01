from datetime import datetime
import logging
import os
from pathlib import Path
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)

from charts.chart_builder import ChartBuilder
from utils.func import fmt_num, fmt_date
import config

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# -------------------------------------------------------------------------
# OBSŁUGA CZCIONEK DLA POLSKICH ZNAKÓW
# -------------------------------------------------------------------------
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

try:
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        font_bold_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("CustomFont", font_path))
        pdfmetrics.registerFont(TTFont("CustomFont-Bold", font_bold_path))
        FONT_NAME = "CustomFont"
        FONT_BOLD = "CustomFont-Bold"
except Exception as e:
    print(f"Ostrzeżenie czcionki: {e}")

OUTPUT_PDF_DIR = Path("output/pdf")


# -------------------------------------------------------------------------
# DYNAMICZNA NUMERACJA STRON W STOPCE
# -------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    """Canvas dodający stopkę z numeracją stron (np. Strona 1 z 3)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont(FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#8b949e"))
        page_width = self._pagesize[0]
        page_text = f"Strona {self._pageNumber} z {page_count}"
        self.drawRightString(page_width - 30, 20, page_text)
        self.drawString(30, 20, "Raport Skanera Giełdowego | Wygenerowano automatycznie")


# =========================================================================
# 1. RAPORT INDYWIDUALNY DLA JEDNEJ SPÓŁKI (2 STRONY + WYKRESY)
# =========================================================================
def generate_pdf_report(analysis, filename=None):


    
    
    """Generuje szczegółowy, 2-stronicowy raport PDF z wykresami dla wybranego waloru."""
    symbol = getattr(analysis, "symbol", "WALOR")
    info = getattr(analysis, "instrument_info", {}) or {}
    currency = info.get("currency", "PLN")

    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    target_path = OUTPUT_PDF_DIR / f"raport_{symbol}.pdf" if filename is None else Path(filename)

    doc = SimpleDocTemplate(
        str(target_path),
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=30,
        bottomMargin=30,
    )
    story = []
    styles = getSampleStyleSheet()

    COLOR_PRIMARY = colors.HexColor("#0f172a")
    COLOR_CARD_BG = colors.HexColor("#f8fafc")
    COLOR_BORDER = colors.HexColor("#e2e8f0")
    COLOR_GREEN = colors.HexColor("#16a34a")
    COLOR_RED = colors.HexColor("#dc2626")
    COLOR_PRICE = colors.HexColor("#2563eb")
    COLOR_TARGET = colors.HexColor("#e616f9")

    title_style = ParagraphStyle(
        "HeaderTitle", parent=styles["Heading1"], fontName=FONT_BOLD, fontSize=14, textColor=colors.whitesmoke, alignment=1
    )
    section_title = ParagraphStyle(
        "SectionTitle", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=10.5, textColor=COLOR_PRIMARY, spaceBefore=4, spaceAfter=3
    )
    cell_style = ParagraphStyle(
        "CellText", parent=styles["Normal"], fontName=FONT_NAME, fontSize=8, leading=10, textColor=COLOR_PRIMARY
    )
    cell_bold = ParagraphStyle("CellBold", parent=cell_style, fontName=FONT_BOLD)

    # -------------------------------------------------------------------------
    # STRONA 1: NAGŁÓWEK + WYKRES DETALICZNY 90 DNI (BOLLINGER BANDS + RSI)
    # -------------------------------------------------------------------------
    full_name = info.get("longName", symbol)
    header_table = Table([[Paragraph(f"📊 ANALIZA TECHNICZNA: {symbol} - {full_name}", title_style)]], colWidths=[525])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # --- DANE Z YAHOO FINANCE & WYCENA ---
    if info:
        # Wycena spółki i akcji
        mcap = info.get("marketCap") or (info.get("marketCap"))
        current_price = info.get("currentPrice") or (info.get("regularMarketPrice"))
        #current_price=getattr(analysis, "price", 0.0)
        
        story.append(Paragraph("<b>WYCENA SPÓŁKI I WSKAŹNIKI FUNDAMENTALNE</b>", section_title))
        
        fund_data = [
            [
                Paragraph(f"<b>Wartość spółki (MCap):</b> {fmt_num(mcap, currency)}", cell_style),
                Paragraph(f"<b>Cena C/Z (Trailing P/E):</b> {fmt_num(info.get('trailingPE'))}", cell_style),
                Paragraph(f"<b>Stopa dywidendy:</b> {fmt_num(info.get('dividendYield'), is_pct=True)}", cell_style)
            ],
            [
                Paragraph(f"<b>Cena 1 akcji:</b> {fmt_num(current_price, currency)}", cell_style),
                Paragraph(f"<b>Przyszłe C/Z (Forward P/E):</b> {fmt_num(info.get('forwardPE'))}", cell_style),
                Paragraph(f"<b>Dzień dywidendy:</b> {fmt_date(info.get('exDividendDate'))}", cell_style)
            ],
            [
                Paragraph(f"<b>Wskaźnik C/WK (P/B):</b> {fmt_num(info.get('priceToBook'))}", cell_style),
                Paragraph(f"<b>EPS (Trailing / Fwd):</b> {fmt_num(info.get('trailingEps'))} / {fmt_num(info.get('forwardEps'))}", cell_style),
                Paragraph(f"<b>Wskaźnik wypłaty:</b> {fmt_num(info.get('payoutRatio'), is_pct=True)}", cell_style)
            ],
            [
                Paragraph(f"<b>Dług / Kapitał:</b> {fmt_num(info.get('debtToEquity'))}", cell_style),
                Paragraph(f"<b>Rentowność aktywów (ROA):</b> {fmt_num(info.get('returnOnAssets'), is_pct=True)}", cell_style),
                Paragraph(f"<b>Marża zysku:</b> {fmt_num(info.get('profitMargins'), is_pct=True)}", cell_style)
            ],
            [
                Paragraph(f"<b>Dług całkowity:</b> {fmt_num(info.get('totalDebt'), currency)}", cell_style),
                Paragraph(f"<b>Rentowność kapitału (ROE):</b> {fmt_num(info.get('returnOnEquity'), is_pct=True)}", cell_style),
                Paragraph(f"<b>Data wyników:</b> {fmt_date(info.get('earningsDate'))}", cell_style)
            ]
        ]
        t_fund = Table(fund_data, colWidths=[190, 175, 175])
        t_fund.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_fund)
        story.append(Spacer(1, 4))

        # Konsensus i Ryzyko
        story.append(Paragraph("<b>KONSENSUS ANALITYKÓW I STATYSTYKI RYZYKA</b>", section_title))
        reco_key = str(info.get("recommendationKey", "-")).upper()
        
        analyst_data = [
            [
                Paragraph(f"<b>Rekomendacja:</b> {reco_key} ({info.get('numberOfAnalystOpinions', 0)} analityków)", cell_style),
                Paragraph(f"<b>Beta (Zmienność):</b> {fmt_num(info.get('beta'))}", cell_style),
                Paragraph(f"<b>Średni wolumen:</b> {fmt_num(info.get('averageVolume'))}", cell_style)
            ],
            [
                Paragraph(f"<b>Średnia cena docelowa:</b> {fmt_num(info.get('targetMeanPrice'), currency)}", cell_style),
                Paragraph(f"<b>Max 52-tyg:</b> {fmt_num(info.get('fiftyTwoWeekHigh'), currency)}", cell_style),
                Paragraph(f"<b>Short Ratio:</b> {fmt_num(info.get('shortRatio'))}", cell_style)
            ],
            [
                Paragraph(f"<b>Zakres docelowy:</b> {fmt_num(info.get('targetLowPrice'))} - {fmt_num(info.get('targetHighPrice'))} {currency}", cell_style),
                Paragraph(f"<b>Min 52-tyg:</b> {fmt_num(info.get('fiftyTwoWeekLow'), currency)}", cell_style),
                Paragraph(f"<b>Udział instytucji:</b> {fmt_num(info.get('heldPercentInstitutions'), is_pct=True)}", cell_style)
            ]
        ]
        t_analyst = Table(analyst_data, colWidths=[175, 175, 175])
        t_analyst.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_analyst)
        story.append(Spacer(1, 4))

    # Wykres 1: Wstęgi Bollingera + RSI (90 dni)
    if hasattr(analysis, "df") and analysis.df is not None:
        builder_short = ChartBuilder(analysis, days=90)
        builder_short.add_bollinger_bands()
        builder_short.add_rsi()
        builder_short.create()
        builder_short.add_support_zones()
        builder_short.add_resistance_zones()
        builder_short.add_current_price()
        builder_short.add_trade_levels()

        chart_short_buf = builder_short.save_to_buffer()
        story.append(Paragraph("<b>WYKRES DETALICZNY (90 DNI) - WSTĘGI BOLLINGERA + RSI</b>", section_title))
        story.append(Image(chart_short_buf, width=525, height=195))
        story.append(Spacer(1, 4))

    # Drabina cenowa
    story.append(Paragraph("<b>DRABINA POZIOMÓW CENOWYCH</b>", section_title))
    price = getattr(analysis, "price", 0.0)
    levels = []

    res = getattr(analysis, "nearest_resistance", None)
    if res and res.get("price"):
        dist = getattr(analysis, "resistance_distance", 0) or 0
        levels.append({"price": res["price"], "label": f"OPÓR [{res.get('touches', 1)}x]", "detail": f"Odstęp: {dist:.2f}%", "type": "RES"})

    supp = getattr(analysis, "nearest_support", None)
    if supp and supp.get("price"):
        dist = getattr(analysis, "support_distance", 0) or 0
        levels.append({"price": supp["price"], "label": f"WSPARCIE [{supp.get('touches', 1)}x]", "detail": f"Odstęp: {dist:.2f}%", "type": "SUP"})

    tp_val = getattr(analysis, "take_profit", None)
    if tp_val is not None:
        dist_tp = ((tp_val - price) / price) * 100 if price else 0
        levels.append({"price": tp_val, "label": "🎯 TAKE PROFIT (TP)", "detail": f"Zysk: +{dist_tp:.2f}%", "type": "TP"})

    sl_val = getattr(analysis, "stop_loss", None)
    if sl_val is not None:
        dist_sl = ((price - sl_val) / price) * 100 if price else 0
        levels.append({"price": sl_val, "label": "🛑 STOP LOSS (SL)", "detail": f"Ryzyko: -{dist_sl:.2f}%", "type": "SL"})

    for ema_name in ["ema20", "ema50", "ema200"]:
        ema_val = getattr(analysis, ema_name, None)
        if ema_val is not None:
            levels.append({"price": ema_val, "label": f"{ema_name.upper()}", "detail": "Średnia", "type": "EMA"})

    levels.append({"price": price, "label": "AKTUALNA CENA", "detail": "Rynkowa", "type": "PRICE"})

    target_p = getattr(analysis, "target_mean_price", None)
    if target_p is not None:
        dist_target = ((target_p - price) / price) * 100
        levels.append({"price": target_p, "label": "🎯 TARGET ANALITYKÓW", "detail": f"Potencjał: {dist_target:+.2f}%", "type": "TARGET"})

    levels.sort(key=lambda x: x["price"], reverse=True)

    ladder_table_data = []
    for lvl in levels:
        p_str = f"{lvl['price']:.2f} {currency}"
        if lvl["type"] == "PRICE":
            ladder_table_data.append([
                Paragraph(f"<b>► {lvl['label']}</b>", ParagraphStyle("P", parent=cell_bold, textColor=COLOR_PRICE)),
                Paragraph(f"<b>{p_str}</b>", ParagraphStyle("P", parent=cell_bold, textColor=COLOR_PRICE)),
                Paragraph(f"<b>{lvl['detail']}</b>", ParagraphStyle("P", parent=cell_bold, textColor=COLOR_PRICE)),
            ])
        else:
            col = COLOR_RED if lvl["type"] in ["RES", "SL"] else (COLOR_GREEN if lvl["type"] in ["SUP", "TP"] else COLOR_TARGET) if lvl["type"] == "TARGET" else COLOR_PRIMARY
            ladder_table_data.append([
                Paragraph(lvl["label"], ParagraphStyle("L", parent=cell_bold, textColor=col)),
                Paragraph(p_str, cell_bold),
                Paragraph(lvl["detail"], cell_style),
            ])

    ladder_table = Table(ladder_table_data, colWidths=[210, 140, 175])
    ladder_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ladder_table)
    story.append(Spacer(1, 6))

    # Parametry transakcji + Checklista
    trade_signal = getattr(analysis, "trade_signal", "NEUTRAL")
    trade_rr = getattr(analysis, "risk_reward", None)
    rr_str = f"{trade_rr:.2f}" if trade_rr is not None else "N/A"
    atr_val = getattr(analysis, "atr", None)
    atr_str = f"{atr_val:.2f} {currency}" if atr_val is not None else "N/A"

    trade_text = [
        Paragraph("<b>PARAMETRY TRANSAKCJI</b>", cell_bold),
        Spacer(1, 2),
        Paragraph(f"<b>Sygnał:</b> {trade_signal}", cell_style),
        Paragraph(f"<b>R/R Ratio:</b> {rr_str}", cell_style),
        Paragraph(f"<b>Zmienność ATR:</b> {atr_str}", cell_style),
        Paragraph(f"<b>Stop Loss:</b> {sl_val:.2f} {currency}" if sl_val else "<b>Stop Loss:</b> N/A", ParagraphStyle("SL", parent=cell_style, textColor=COLOR_RED)),
        Paragraph(f"<b>Take Profit:</b> {tp_val:.2f} {currency}" if tp_val else "<b>Take Profit:</b> N/A", ParagraphStyle("TP", parent=cell_style, textColor=COLOR_GREEN)),
    ]

    chk_text = [Paragraph("<b>CHECKLISTA SYGNAŁOWA</b>", cell_bold), Spacer(1, 2)]
    trend_dict = getattr(analysis, "trend", {}) or {}
    t_code = trend_dict.get("trend", "N/A")
    t_desc = trend_dict.get("desc", "")
    ema20 = getattr(analysis, "ema20", None)
    macd = getattr(analysis, "macd", None)
    macd_sig = getattr(analysis, "macd_signal", None)
    rsi = getattr(analysis, "rsi", None)

    checklist_items = [
        (t_code in ("UP", "STRONG_UP"), f"Trend: {t_code} ({t_desc})"),
        (ema20 is not None and price > ema20, f"Cena > EMA20 ({ema20:.2f})" if ema20 else "Brak EMA20"),
        (macd is not None and macd_sig is not None and macd > macd_sig, "MACD > Signal (Byczy sygnał)"),
        (rsi is not None and rsi < getattr(config, 'RSI_OVERBOUGHT', 70), f"RSI nieprzegrzany ({rsi:.1f})" if rsi else "Brak RSI"),
        (trade_rr is not None and trade_rr >= 2.0, f"Zysk/Ryzyko ok (RR = {rr_str})"),
    ]

    for is_ok, label in checklist_items:
        icon, color = ("✔", "#16a34a") if is_ok else ("✘", "#dc2626")
        chk_text.append(Paragraph(f"<font color='{color}'><b>{icon}</b></font>  {label}", cell_style))

    bottom_table = Table([[trade_text, chk_text]], colWidths=[257, 268])
    bottom_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (0, 0), 1, COLOR_BORDER),
        ("BOX", (1, 0), (1, 0), 1, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(bottom_table)

    # -------------------------------------------------------------------------
    # STRONA 2: WYKRES LONG-TERM 360 DNI (EMA + MACD) + OZNACZENIA SCORE
    # -------------------------------------------------------------------------
    story.append(PageBreak())

    # Wykres 2: Średnie EMA + MACD (360 dni)
    if hasattr(analysis, "df") and analysis.df is not None:
        builder_long = ChartBuilder(analysis, days=360)
        builder_long.add_ema()
        builder_long.add_macd()
        builder_long.create()
        builder_long.add_support_zones()
        builder_long.add_resistance_zones()

        chart_long_buf = builder_long.save_to_buffer()
        story.append(Paragraph("<b>WYKRES TRENDU (360 DNI) - ŚREDNIE EMA + MACD</b>", section_title))
        story.append(Image(chart_long_buf, width=525, height=210))
        story.append(Spacer(1, 8))

    # Sekcja Score'ów
    quality_score = getattr(analysis, "quality_score", 0)
    quality_desc = "<font color='#16a34a'>● Top okazja</font>" if quality_score >= 80 else ("<font color='#d97706'>● Dobra spółka</font>" if quality_score >= 65 else "<font color='#dc2626'>● Słaba / Omijaj</font>")

    entry_score = getattr(analysis, "entry_score", 0)
    entry_desc = "<font color='#16a34a'>● KUPUJ</font>" if entry_score >= 80 else ("<font color='#d97706'>● OBSERWUJ</font>" if entry_score >= 65 else "<font color='#dc2626'>● ZAKAZ WEJŚCIA</font>")

    q_content = [Paragraph(f"<b>QUALITY SCORE: {quality_score}/100</b> | {quality_desc}", cell_bold), Spacer(1, 4)]
    for reason in getattr(analysis, "quality_reasons", []):
        pts = reason.get("points", 0) if isinstance(reason, dict) else 0
        txt = reason.get("text", str(reason)) if isinstance(reason, dict) else str(reason)
        sign = "+" if pts > 0 else ""
        q_content.append(Paragraph(f"<b>{sign}{pts:2d} pkt</b> | {txt}", cell_style))

    e_content = [Paragraph(f"<b>ENTRY SCORE: {entry_score}/100</b> | {entry_desc}", cell_bold), Spacer(1, 4)]
    for reason in getattr(analysis, "entry_reasons", []):
        pts = reason.get("points", 0) if isinstance(reason, dict) else 0
        txt = reason.get("text", str(reason)) if isinstance(reason, dict) else str(reason)
        sign = "+" if pts > 0 else ""
        e_content.append(Paragraph(f"<b>{sign}{pts:2d} pkt</b> | {txt}", cell_style))

    scores_table = Table([[q_content, e_content]], colWidths=[257, 268])
    scores_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (0, 0), 1, COLOR_BORDER),
        ("BOX", (1, 0), (1, 0), 1, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(scores_table)

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer, canvasmaker=NumberedCanvas)
    print(f" Wygenerowano PDF spółki: {target_path}")


# =========================================================================
# 2. RAPORT ZBIORCZY DLA CAŁEGO PORTFELA / SKANERA (TABELA LANDSCAPE)
# =========================================================================
def generate_summary_pdf_report(results: dict, portfolio_name: str = "default", filename: str = None) -> Path:
    """Generuje zbiorczy raport PDF ze skanera dla wielu spółek (układ poziomy Landscape A4)."""
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        clean_name = Path(portfolio_name).stem.lower()
        target_path = OUTPUT_PDF_DIR / f"raport_zbiorczy_{clean_name}.pdf"
    else:
        target_path = Path(filename)

    # Marginesy dostosowane do nagłówka i stopki (topMargin=25, bottomMargin=30)
    doc = SimpleDocTemplate(
        str(target_path),
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=25,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = FONT_NAME

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=18,
        textColor=colors.HexColor("#58a6ff"),
    )

    cat_style = ParagraphStyle(
        "CategoryTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
    )

    cell_style = ParagraphStyle(
        "SummaryCellText",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#c9d1d9"),
    )

    cell_bold = ParagraphStyle(
        "SummaryCellBold",
        parent=cell_style,
        fontName=FONT_BOLD,
        textColor=colors.HexColor("#f0f6fc"),
    )

    header_style = ParagraphStyle(
        "SummaryHeaderCell",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=7,
        leading=8,
        textColor=colors.HexColor("#ffffff"),
    )

    story = []

    # Nagłówek zbiorczego dokumentu
    now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"📊 Raport Skanera Giełdowego — PORTFEL: {portfolio_name.upper()}", title_style))
    story.append(Paragraph(f"<font color='#8b949e' size=7.5>Wygenerowano: {now_str}</font>", styles["Normal"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#30363d"), spaceAfter=8))

    categories_config = [
        ("STRONG_BUY", "ALERTY TRANSAKCYJNE (Idealne wejście)", colors.HexColor("#2ea043")),
        ("WATCHLIST", "LISTA OBSERWACYJNA (Gotowość do wejścia)", colors.HexColor("#58a6ff")),
        ("ACCUMULATION", "KONSOLIDACJA / BUDOWANIE BAZY", colors.HexColor("#d29922")),
        ("REJECTED", "ODRZUCONE (Słabość / Trend spadkowy)", colors.HexColor("#f85149")),
    ]

    for cat_key, cat_title, color in categories_config:
        items = results.get(cat_key, [])

        cat_p = Paragraph(f"<font color='{color.hexval()}'>■ {cat_title}</font> ({len(items)})", cat_style)
        story.append(cat_p)

        if not items:
            story.append(Paragraph("<font color='#8b949e' size=7.5>Brak spółek w tej kategorii.</font>", styles["Normal"]))
            story.append(Spacer(1, 8))
            continue

        headers = [
            "Ticker", "Nazwa", "Cena", "Target", "1D %", "YTD %", 
            "P/E", "Div %", "Wsparcie", "Opór", "SL", "TP", 
            "RR", "Qual", "Entr", "TOTAL", "Sygnał"
        ]

        table_data = [[Paragraph(h, header_style) for h in headers]]

        for item in items:
            chg_val = item.get("change_1d")
            chg_c = "#3fb950" if chg_val and chg_val >= 0 else "#f85149"
            chg_str = f"<font color='{chg_c}'>{chg_val:+.1f}%</font>" if chg_val is not None else "-"

            ytd_val = item.get("ytd_change")
            ytd_c = "#3fb950" if ytd_val and ytd_val >= 0 else "#f85149"
            ytd_str = f"<font color='{ytd_c}'>{ytd_val:+.1f}%</font>" if ytd_val is not None else "-"

            rr_val = item.get("rr")
            rr_str = f"1:{rr_val:.2f}" if rr_val else "-"

            sl_str = f"{item['sl']:.2f}" if item.get("sl") else "-"
            tp_str = f"{item['tp']:.2f}" if item.get("tp") else "-"

            supp_str = f"{item['support']:.2f}" if item.get("support") else "-"
            res_str = f"{item['resistance']:.2f}" if item.get("resistance") else "ATH"

            row = [
                Paragraph(item["ticker"], cell_bold),
                Paragraph(item["name"][:12], cell_style),
                Paragraph(f"{item['price']:.2f}", cell_style),
                Paragraph(f"{item['target_price']:.2f}" if item.get("target_price") else "-", cell_style),
                Paragraph(chg_str, cell_style),
                Paragraph(ytd_str, cell_style),
                Paragraph(f"{item['pe_ratio']:.1f}" if item.get("pe_ratio") else "-", cell_style),
                Paragraph(f"{item['div_yield']*100:.1f}%" if item.get("div_yield") else "0%", cell_style),
                Paragraph(supp_str, cell_style),
                Paragraph(res_str, cell_style),
                Paragraph(f"<font color='#f85149'>{sl_str}</font>", cell_style),
                Paragraph(f"<font color='#3fb950'>{tp_str}</font>", cell_style),
                Paragraph(rr_str, cell_bold),
                Paragraph(str(item["q_score"]), cell_style),
                Paragraph(str(item["e_score"]), cell_style),
                Paragraph(f"<b>{item['total_score']:.1f}</b>", cell_style),
                Paragraph(f"<font color='#f85149'>{item['trade_signal']}</font>", cell_bold),
            ]
            table_data.append(row)

        col_widths = [42, 65, 42, 42, 42, 44, 32, 35, 44, 44, 42, 42, 42, 28, 28, 35, 55]

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21262d")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#30363d")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0d1117"), colors.HexColor("#161b22")]),
        ]))

        story.append(t)
        story.append(Spacer(1, 8))

    # Generowanie dokumentu ze stopką i nagłówkiem na każdej stronie
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    
    print(f" Wygenerowano zbiorczy PDF: {target_path}")
    return target_path



def draw_header_footer(canvas, doc):
    """Rysuje nagłówek i stopkę z klauzulą wyłączenia odpowiedzialności (A4 Landscape)."""
    canvas.saveState()
    
    # Parametry strony A4 Landscape (szerokość: 841.89 pt, wysokość: 595.27 pt)
    page_width, page_height = landscape(A4)
    margin = 20
    
    # 1. NAGŁÓWEK (Po polsku)
    canvas.setFont(FONT_NAME, 6.5)
    canvas.setFillColor(colors.HexColor("#fe0808"))
    
    header_line = (
        "Uwaga: Gra w inwestowanie na własną odpowiedzialność — strata może zaboleć, gdy wygrasz po prostu podziel się! "
        "Raport edukacyjny, nie stanowi porady. Kod skanera: https://github.com/jarok2013-sudo/stock-analyzer"
    )
    canvas.drawString(margin, page_height - 12, header_line)
    
    # Linia pod nagłówkiem
    canvas.setStrokeColor(colors.HexColor("#30363d"))
    canvas.setLineWidth(0.5)
    canvas.line(margin, page_height - 16, page_width - margin, page_height - 16)
    
    # 2. STOPKA (Po angielsku + Numeracja stron)
    
    canvas.line(margin, 27, page_width - margin, 27)
    
    footer_text = (
        "Disclaimer: For informational and educational purposes only. Not financial advice. "
        "Investments carry risk of loss — if you win, share the gains; if you lose, it's on you — use at your own risk.\n Project code: https://github.com/jarok2013-sudo/stock-analyzer"
    )
    #canvas.drawString(margin, 12, footer_text)
    footer_line1="Disclaimer: For informational and educational purposes only. Not financial advice. " 
    canvas.drawString(margin, 18, footer_line1)
    footer_line2="Investments carry risk of loss — if you win, share the gains; if you lose, it's on you — use at your own risk. Project code: https://github.com/jarok2013-sudo/stock-analyzer"
    canvas.drawString(margin, 8, footer_line2)
    
    # Numeracja stron po prawej stronie
    canvas.setFillColor(colors.HexColor("#8b949e"))
    page_num = f"Strona {doc.page}"
    canvas.drawRightString(page_width - margin, 12, page_num)
    
    canvas.restoreState()