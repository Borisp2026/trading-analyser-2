"""
PDF Report Builder for Trading Analyser 2.0
Generates a detailed per-stock report with buy/sell reasoning, cycle analysis, and portfolio summary.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm

DARK_BLUE = colors.HexColor("#1a1a2e")
MID_BLUE = colors.HexColor("#16213e")
GREEN = colors.HexColor("#00aa00")
RED = colors.HexColor("#cc0000")
ORANGE = colors.HexColor("#ff9900")
LIGHT_GREY = colors.HexColor("#f5f5f5")
WHITE = colors.white

styles = getSampleStyleSheet()


def make_styles():
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, textColor=WHITE, spaceAfter=6, alignment=TA_CENTER)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=DARK_BLUE, spaceBefore=10, spaceAfter=4)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11, textColor=MID_BLUE, spaceBefore=6, spaceAfter=3)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, spaceAfter=3, leading=13)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey, spaceAfter=2)
    label = ParagraphStyle("Label", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    return h1, h2, h3, body, small, label


def rec_color(rec: str):
    if "STRONG BUY" in rec:
        return GREEN
    elif "BUY" in rec:
        return colors.HexColor("#44bb44")
    elif "HOLD" in rec:
        return ORANGE
    elif "WEAK" in rec:
        return colors.HexColor("#ff6600")
    return RED


def build_pdf_report(results: list, portfolio: dict, output_path: str):
    h1, h2, h3, body, small, label = make_styles()
    story = []
    today = datetime.now().strftime("%d %B %Y")

    # ── Cover page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 30 * mm))
    cover_table = Table([[Paragraph(f"Trading Analyser 2.0", h1),
                          Paragraph(f"Nightly Report", h1),
                          Paragraph(today, h1)]], colWidths=[PAGE_W - 2 * MARGIN])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 10 * mm))

    # Summary stats
    total = len(results)
    buys = sum(1 for r in results if "BUY" in r["reasoning"].get("recommendation", ""))
    holds = sum(1 for r in results if "HOLD" in r["reasoning"].get("recommendation", ""))
    avoids = total - buys - holds

    summary_data = [
        ["Stocks Scanned", "Buy Signals", "Hold/Watch", "Avoid"],
        [str(total), str(buys), str(holds), str(avoids)]
    ]
    summary_table = Table(summary_data, colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MID_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GREY, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))

    # ── Portfolio summary ────────────────────────────────────────────────────
    real = portfolio.get("real", {})
    paper = portfolio.get("paper", {})

    story.append(Paragraph("Portfolio Summary", h2))
    port_pnl = real.get("total_pnl", 0)
    port_data = [
        ["Metric", "Value"],
        ["Portfolio Value", f"${real.get('total_value', 0):,.2f}"],
        ["Total Cost", f"${real.get('total_cost', 0):,.2f}"],
        ["P&L", f"${port_pnl:+,.2f} ({real.get('total_pnl_pct', 0):+.1f}%)"],
        ["Annual Dividends", f"${real.get('total_annual_dividends', 0):,.2f}"],
        ["Paper Trade Win Rate", f"{paper.get('win_rate_pct', 0):.1f}%"],
        ["Paper Cash Balance", f"${paper.get('cash_balance', 0):,.2f}"],
    ]
    port_table = Table(port_data, colWidths=[(PAGE_W - 2 * MARGIN) * 0.5, (PAGE_W - 2 * MARGIN) * 0.5])
    port_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GREY, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TEXTCOLOR", (1, 3), (1, 3), GREEN if port_pnl >= 0 else RED),
    ]))
    story.append(port_table)
    story.append(Spacer(1, 5 * mm))

    # ── Holdings breakdown ────────────────────────────────────────────────────
    holdings = real.get("holdings", [])
    if holdings:
        story.append(Paragraph("Current Holdings", h3))
        hold_data = [["Ticker", "Shares", "Buy $", "Current $", "Value", "P&L", "Div Yield"]]
        for h in holdings:
            hold_data.append([
                h["ticker"], str(h["shares"]),
                f"${h['buy_price']:.3f}", f"${h['current_price']:.3f}",
                f"${h['value']:,.2f}",
                f"${h['pnl']:+,.2f} ({h['pnl_pct']:+.1f}%)",
                f"{h['div_yield_pct']:.1f}%",
            ])
        hold_table = Table(hold_data, colWidths=[(PAGE_W - 2 * MARGIN) / 7] * 7)
        hold_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MID_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GREY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(hold_table)
        story.append(Spacer(1, 5 * mm))

    # ── Top opportunities table ───────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Today's Opportunities", h2))
    opp_data = [["Ticker", "Recommendation", "Score", "Price", "Entry", "Stop", "Target", "R:R", "Confidence"]]
    for r in results[:20]:
        rec = r["reasoning"]
        t = r["tech"]
        rr = rec.get("risk_reward")
        opp_data.append([
            r["ticker"],
            rec.get("recommendation", "?"),
            f"{rec.get('blended_score', 0):.0f}",
            f"${t.get('price', 0):.3f}",
            f"${rec.get('entry_price', 0) or 0:.3f}",
            f"${rec.get('stop_loss', 0) or 0:.3f}",
            f"${rec.get('take_profit', 0) or 0:.3f}",
            f"{rr:.1f}:1" if rr else "—",
            rec.get("confidence", "?"),
        ])

    col_w = (PAGE_W - 2 * MARGIN) / 9
    opp_table = Table(opp_data, colWidths=[col_w] * 9)
    opp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GREY, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    # Colour recommendation cells
    for i, r in enumerate(results[:20], 1):
        rec_text = r["reasoning"].get("recommendation", "")
        opp_table.setStyle(TableStyle([
            ("TEXTCOLOR", (1, i), (1, i), rec_color(rec_text)),
            ("FONTNAME", (1, i), (1, i), "Helvetica-Bold"),
        ]))

    story.append(opp_table)

    # ── Per-stock detail pages ────────────────────────────────────────────────
    for r in results:
        story.append(PageBreak())
        rec = r["reasoning"]
        t = r["tech"] or {}
        cyc = r.get("cycle", {})

        # Stock header
        header_table = Table([[
            Paragraph(f"{r['ticker']} — {r.get('name', '')[:40]}", h2),
            Paragraph(rec.get("recommendation", "?"), ParagraphStyle(
                "RecBig", fontSize=14, textColor=rec_color(rec.get("recommendation", "")),
                fontName="Helvetica-Bold", alignment=TA_RIGHT
            ))
        ]], colWidths=[(PAGE_W - 2 * MARGIN) * 0.65, (PAGE_W - 2 * MARGIN) * 0.35])
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
        story.append(Spacer(1, 3 * mm))

        # Key metrics row
        metrics = [
            ["Price", f"${t.get('price', 0):.3f}"],
            ["1D Change", f"{t.get('price_1d_pct', 0):+.1f}%"],
            ["RSI", str(t.get("rsi", "—"))],
            ["Score", f"{rec.get('blended_score', 0):.0f}/100"],
            ["Confidence", rec.get("confidence", "?")],
        ]
        met_table = Table([
            [Paragraph(m[0], label) for m in metrics],
            [Paragraph(f"<b>{m[1]}</b>", body) for m in metrics],
        ], colWidths=[(PAGE_W - 2 * MARGIN) / 5] * 5)
        met_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ]))
        story.append(met_table)
        story.append(Spacer(1, 3 * mm))

        # Entry / Exit
        story.append(Paragraph("Entry / Exit Plan", h3))
        trade_data = [
            ["Timing", rec.get("timing", "—")],
            ["Entry", f"${rec.get('entry_price', '—')} | {rec.get('entry_type', '')}"],
            ["Stop Loss", f"${rec.get('stop_loss', '—')} | {rec.get('stop_note', '')}"],
            ["Target", f"${rec.get('take_profit', '—')}"],
            ["Risk:Reward", f"{rec.get('risk_reward', '—')}:1" if rec.get('risk_reward') else "—"],
        ]
        if rec.get("dividend_note"):
            trade_data.append(["Dividend", rec.get("dividend_note")])

        trade_table = Table(trade_data, colWidths=[(PAGE_W - 2 * MARGIN) * 0.2, (PAGE_W - 2 * MARGIN) * 0.8])
        trade_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(trade_table)
        story.append(Spacer(1, 3 * mm))

        # Why this stock
        story.append(Paragraph("Analysis & Reasoning", h3))
        reasons = rec.get("reasons", [])
        for reason in reasons:
            story.append(Paragraph(f"• {reason}", body))
        story.append(Spacer(1, 2 * mm))

        # Cycle summary
        if cyc and cyc.get("status") == "ok":
            story.append(Paragraph("Cycle Analysis (DJRTrading)", h3))
            cc = cyc.get("current_cycle", {})
            cycle_data = [
                ["Cycle Signal", cyc.get("cycle_signal", "?")],
                ["Cycle Length", f"{cyc.get('cycle_len', '?')} bars"],
                ["Translation", cc.get("translation", "?")],
                ["% Through Cycle", f"{cyc.get('pct_through_cycle', 0):.1f}%"],
                ["Trendline Break", "YES ⚠️" if cyc.get("trendline_break") else "No"],
                ["Confirmation Signal", "YES ✅" if cyc.get("confirmation_signal") else "No"],
                ["High Risk Zone", "YES 🔴" if cyc.get("high_risk_zone") else "No"],
            ]
            cyc_table = Table(cycle_data, colWidths=[(PAGE_W - 2 * MARGIN) * 0.3, (PAGE_W - 2 * MARGIN) * 0.7])
            cyc_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, WHITE]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(cyc_table)
            story.append(Paragraph(f"Entry: {cyc.get('entry_note', '')}", small))
            story.append(Paragraph(f"Exit: {cyc.get('exit_note', '')}", small))

        # Technicals mini-table
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Technical Indicators", h3))
        tech_data = [
            ["RSI", f"{t.get('rsi', '?')}", "Stoch %K", f"{t.get('stoch_k', '?')}"],
            ["MACD", f"{t.get('macd', '?'):.4f}" if t.get('macd') else "?", "MACD Signal", f"{t.get('macd_signal', '?'):.4f}" if t.get('macd_signal') else "?"],
            ["BB Upper", f"${t.get('bb_upper', '?'):.3f}" if t.get('bb_upper') else "?", "BB Lower", f"${t.get('bb_lower', '?'):.3f}" if t.get('bb_lower') else "?"],
            ["50D SMA", f"${t.get('moving_averages', {}).get('sma_50', '?'):.3f}" if t.get('moving_averages', {}).get('sma_50') else "?",
             "200D SMA", f"${t.get('moving_averages', {}).get('sma_200', '?'):.3f}" if t.get('moving_averages', {}).get('sma_200') else "?"],
            ["ATR", f"${t.get('atr', '?'):.4f}" if t.get('atr') else "?", "Volume Ratio", f"{t.get('volume_signal', {}).get('ratio', '?')}x"],
        ]
        tech_table = Table(tech_data, colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4)
        tech_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tech_table)

    # ── Footer / disclaimer ───────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph(
        "⚠️ DISCLAIMER: Trading Analyser 2.0 is for informational purposes only. "
        "This report does not constitute financial advice. Past performance is not "
        "indicative of future results. Always conduct your own research and consider "
        "seeking professional financial advice before making any investment decisions.",
        ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.grey, leading=12)
    ))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    doc.build(story)
    print(f"PDF saved: {output_path}")
