"""
Email report sender for Trading Analyser 2.0
Sends nightly summary email with PDF attachment.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
REPORT_EMAIL = os.environ.get("REPORT_EMAIL", GMAIL_ADDRESS)


def signal_color(rec: str) -> str:
    if "STRONG BUY" in rec:
        return "#00aa00"
    elif "BUY" in rec:
        return "#44bb44"
    elif "HOLD" in rec:
        return "#ff9900"
    elif "WEAK" in rec:
        return "#ff6600"
    return "#cc0000"


def send_email_report(results: list, portfolio: dict, pdf_path: str = None):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Email credentials not configured — skipping email")
        return

    today = datetime.now().strftime("%d %B %Y")
    top_buys = [r for r in results if "BUY" in r["reasoning"].get("recommendation", "")][:8]
    alerts = [r for r in results if r["reasoning"].get("blended_score", 0) >= 65]

    subject = f"📊 Trading Analyser 2.0 — {today} | {len(alerts)} opportunities"

    # Portfolio snippet
    real = portfolio.get("real", {})
    paper = portfolio.get("paper", {})
    portfolio_html = f"""
    <div style="background:#f0f0f0;padding:15px;border-radius:8px;margin-bottom:20px;">
        <h3 style="margin:0 0 10px 0;">📁 Portfolio Snapshot</h3>
        <table style="width:100%;border-collapse:collapse;">
        <tr>
            <td><strong>Real Portfolio Value:</strong></td>
            <td>${real.get('total_value', 0):,.2f}</td>
            <td><strong>P&amp;L:</strong></td>
            <td style="color:{'green' if real.get('total_pnl',0)>=0 else 'red'}">
                ${real.get('total_pnl', 0):+,.2f} ({real.get('total_pnl_pct', 0):+.1f}%)
            </td>
        </tr>
        <tr>
            <td><strong>Annual Dividends:</strong></td>
            <td>${real.get('total_annual_dividends', 0):,.2f}</td>
            <td><strong>Paper Trade Win Rate:</strong></td>
            <td>{paper.get('win_rate_pct', 0):.1f}%</td>
        </tr>
        </table>
    </div>
    """

    # Top picks table
    rows = ""
    for r in top_buys:
        rec = r["reasoning"].get("recommendation", "?")
        score = r["reasoning"].get("blended_score", 0)
        price = r["tech"].get("price", 0)
        change = r["tech"].get("price_1d_pct", 0)
        entry = r["reasoning"].get("entry_price", "—")
        stop = r["reasoning"].get("stop_loss", "—")
        target = r["reasoning"].get("take_profit", "—")
        confidence = r["reasoning"].get("confidence", "—")

        rows += f"""
        <tr>
            <td><strong>{r['ticker']}</strong><br><small>{r.get('name','')[:25]}</small></td>
            <td style="color:{signal_color(rec)};font-weight:bold;">{rec}</td>
            <td style="text-align:center;">{score:.0f}</td>
            <td>${price:.3f} ({'+' if change>0 else ''}{change:.1f}%)</td>
            <td style="color:green;">${entry if entry else '—'}</td>
            <td style="color:red;">${stop if stop else '—'}</td>
            <td style="color:blue;">${target if target else '—'}</td>
            <td>{confidence}</td>
        </tr>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px;">

    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:25px;border-radius:10px;margin-bottom:25px;">
        <h1 style="margin:0;">📊 Trading Analyser 2.0</h1>
        <p style="margin:5px 0 0 0;opacity:0.8;">Nightly Report — {today}</p>
    </div>

    {portfolio_html}

    <h2>🏆 Today's Top Opportunities</h2>
    <table border="1" cellpadding="10" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:14px;">
    <tr style="background:#1a1a2e;color:white;">
        <th>Stock</th><th>Signal</th><th>Score</th><th>Price</th>
        <th>Entry</th><th>Stop Loss</th><th>Target</th><th>Confidence</th>
    </tr>
    {rows}
    </table>

    <p style="margin-top:20px;font-size:13px;">
    See PDF attachment for full analysis including cycle positions, detailed reasoning, and portfolio breakdown.<br>
    View live dashboard at your GitHub Pages URL.
    </p>

    <p style="color:#999;font-size:11px;border-top:1px solid #eee;padding-top:10px;margin-top:20px;">
    Trading Analyser 2.0 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} AWST<br>
    ⚠️ This is not financial advice. Always do your own research before trading.
    </p>

    </body></html>
    """

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = REPORT_EMAIL

        msg.attach(MIMEText(html, "html"))

        # Attach PDF
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(pdf_path)}"')
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"Report email sent to {REPORT_EMAIL}")

    except Exception as e:
        print(f"Failed to send email: {e}")
