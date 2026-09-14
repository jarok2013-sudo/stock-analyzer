from datetime import datetime
import io
import logging
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from charts.chart_builder import ChartBuilder
import config

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

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


def generate_pdf_report(analysis, filename=None):
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

    # Drabina cenowa (z ew. uwzględnieniem wartości ATR)
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
            col = COLOR_RED if lvl["type"] in ["RES", "SL"] else (COLOR_GREEN if lvl["type"] in ["SUP", "TP"] else COLOR_PRIMARY)
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
        (rsi is not None and rsi < config.RSI_OVERBOUGHT, f"RSI nieprzegrzany ({rsi:.1f})" if rsi else "Brak RSI"),
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

    doc.build(story)
    print(f" Wygenerowano PDF: {target_path}")