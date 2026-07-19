"""
Intraday Scanner — Live Day Trading Alerts for Trading Analyser 2.0
Runs every 30 minutes during market hours via GitHub Actions.
Detects: breakouts, volume spikes, RSI reversals, MACD crosses, cycle signals.
Sends email alert when a strong intraday signal fires.
"""

import json
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, time, timedelta
import pytz
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from technical import analyse_technicals, calc_rsi, calc_macd, calc_volume_signal

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE, "data", "watchlist.json")
ALERTS_LOG = os.path.join(BASE, "data", "alerts_log.json")
INTRADAY_SIGNALS_FILE = os.path.join(BASE, "data", "intraday_signals.json")

def save_actionable_signal(ticker: str, sig: dict):
    """Persist HIGH priority BUY signals for agent_trader to act on."""
    if sig.get("priority") != "HIGH":
        return
    if not any(w in sig.get("action","") for w in ("BUY","MOMENTUM")):
        return
    try:
        signals = []
        if os.path.exists(INTRADAY_SIGNALS_FILE):
            with open(INTRADAY_SIGNALS_FILE) as f:
                signals = json.load(f)
        cutoff = datetime.now() - timedelta(minutes=60)
        signals = [s for s in signals if datetime.fromisoformat(s["time"]) > cutoff]
        signals.append({
            "ticker": ticker, "signal_type": sig["type"],
            "priority": sig["priority"], "action": sig["action"],
            "price": sig["price"], "rsi": sig.get("rsi"),
            "time": datetime.now().isoformat(), "message": sig["message"],
        })
        with open(INTRADAY_SIGNALS_FILE,"w") as f:
            json.dump(signals, f, indent=2)
    except Exception as e:
        print(f"  Signal save error: {e}")


GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
REPORT_EMAIL = os.environ.get("REPORT_EMAIL", GMAIL_ADDRESS)

ASX_TZ = pytz.timezone("Australia/Sydney")
NASDAQ_TZ = pytz.timezone("America/New_York")


def is_asx_open() -> bool:
    now_asx = datetime.now(ASX_TZ)
    if now_asx.weekday() >= 5:
        return False
    market_open = time(10, 0)
    market_close = time(16, 0)
    return market_open <= now_asx.time() <= market_close


def is_nasdaq_open() -> bool:
    now_ny = datetime.now(NASDAQ_TZ)
    if now_ny.weekday() >= 5:
        return False
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now_ny.time() <= market_close


def load_alerts_log() -> list:
    if os.path.exists(ALERTS_LOG):
        with open(ALERTS_LOG) as f:
            return json.load(f)
    return []


def save_alerts_log(log: list):
    with open(ALERTS_LOG, "w") as f:
        json.dump(log[-500:], f, indent=2, default=str)  # keep last 500


def already_alerted_today(ticker: str, signal_type: str) -> bool:
    """Prevent duplicate alerts for the same signal on the same day."""
    log = load_alerts_log()
    today = str(datetime.now().date())
    return any(
        a["ticker"] == ticker and
        a["signal_type"] == signal_type and
        a["date"] == today
        for a in log
    )


def log_alert(ticker: str, signal_type: str, message: str):
    log = load_alerts_log()
    log.append({
        "ticker": ticker,
        "signal_type": signal_type,
        "message": message,
        "date": str(datetime.now().date()),
        "time": str(datetime.now().time())[:8],
    })
    save_alerts_log(log)


def detect_intraday_signals(ticker: str) -> list:
    """
    Fetch recent intraday data and detect actionable signals.
    Uses 5-minute bars for the last 2 days.
    Returns list of signal dicts.
    """
    signals = []
    try:
        df_intra = yf.Ticker(ticker).history(period="2d", interval="5m")
        df_daily = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=True)

        if df_intra.empty or len(df_intra) < 20:
            return []

        close = df_intra["Close"]
        volume = df_intra["Volume"]
        high = df_intra["High"]
        low = df_intra["Low"]

        current_price = float(close.iloc[-1])
        prev_close = float(df_daily["Close"].iloc[-2]) if len(df_daily) > 1 else current_price

        # RSI on 5-min bars
        rsi = calc_rsi(close, period=14)
        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50
        rsi_prev = float(rsi.iloc[-2]) if len(rsi) > 1 else 50

        # MACD on 5-min
        macd_line, signal_line, histogram = calc_macd(close)
        macd_cross = (float(macd_line.iloc[-2]) < float(signal_line.iloc[-2])) and \
                     (float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]))
        macd_death = (float(macd_line.iloc[-2]) > float(signal_line.iloc[-2])) and \
                     (float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]))

        # Volume spike
        vol_signal = calc_volume_signal(volume, period=20)

        # Price change from prev close
        pct_change = round(((current_price - prev_close) / prev_close) * 100, 2)

        # 20-bar high/low breakout on intraday
        recent_high = float(high.iloc[-20:-1].max()) if len(high) > 20 else 0
        recent_low = float(low.iloc[-20:-1].min()) if len(low) > 20 else 999999

        # --- Signal detection ---

        # 1. RSI Oversold + turning up
        if rsi_val < 32 and rsi_val > rsi_prev:
            signals.append({
                "type": "RSI_OVERSOLD_REVERSAL",
                "priority": "HIGH",
                "message": f"RSI oversold reversal: RSI={rsi_val:.1f} turning up",
                "action": "POTENTIAL BUY"
            })

        # 2. RSI Overbought + turning down
        if rsi_val > 68 and rsi_val < rsi_prev:
            signals.append({
                "type": "RSI_OVERBOUGHT",
                "priority": "MEDIUM",
                "message": f"RSI overbought: RSI={rsi_val:.1f} — consider taking profit",
                "action": "TAKE PROFIT / REDUCE"
            })

        # 3. MACD bullish crossover
        if macd_cross:
            signals.append({
                "type": "MACD_BULLISH_CROSS",
                "priority": "HIGH",
                "message": "MACD bullish crossover on 5-min chart",
                "action": "BUY SIGNAL"
            })

        # 4. MACD death cross
        if macd_death:
            signals.append({
                "type": "MACD_DEATH_CROSS",
                "priority": "HIGH",
                "message": "MACD death cross on 5-min chart",
                "action": "SELL / SHORT SIGNAL"
            })

        # 5. Volume spike + price up
        if vol_signal["signal"] in ("HIGH_VOLUME", "EXTREME_SPIKE") and pct_change > 1.5:
            signals.append({
                "type": "VOLUME_BREAKOUT_UP",
                "priority": "HIGH" if vol_signal["signal"] == "EXTREME_SPIKE" else "MEDIUM",
                "message": f"Volume spike {vol_signal['ratio']}x avg + price +{pct_change}%",
                "action": "MOMENTUM BUY"
            })

        # 6. Volume spike + price down (panic sell / support break)
        if vol_signal["signal"] in ("HIGH_VOLUME", "EXTREME_SPIKE") and pct_change < -1.5:
            signals.append({
                "type": "VOLUME_SELLOFF",
                "priority": "HIGH",
                "message": f"Volume spike {vol_signal['ratio']}x avg + price {pct_change}% — selling pressure",
                "action": "AVOID / EXIT"
            })

        # 7. Intraday breakout above recent high
        if current_price > recent_high * 1.005 and recent_high > 0:
            signals.append({
                "type": "INTRADAY_BREAKOUT",
                "priority": "MEDIUM",
                "message": f"Breaking above 20-bar intraday high (${recent_high:.3f})",
                "action": "BREAKOUT BUY"
            })

        # 8. Big gap up (>3%)
        if pct_change > 3:
            signals.append({
                "type": "GAP_UP",
                "priority": "MEDIUM",
                "message": f"Gap up +{pct_change}% from previous close",
                "action": "MOMENTUM — watch for pullback entry"
            })

        # 9. Big gap down (>-3%)
        if pct_change < -3:
            signals.append({
                "type": "GAP_DOWN",
                "priority": "HIGH",
                "message": f"Gap down {pct_change}% — possible reversal opportunity OR continued sell",
                "action": "WATCH — wait for stabilisation before buying"
            })

        # Add price context to all signals
        for s in signals:
            s["ticker"] = ticker
            s["price"] = round(current_price, 4)
            s["pct_change"] = pct_change
            s["rsi"] = round(rsi_val, 1)
            s["volume_ratio"] = vol_signal["ratio"]
            s["time"] = str(datetime.now())[:16]

    except Exception as e:
        print(f"  Error scanning {ticker}: {e}")

    return signals


def send_alert_email(alerts: list):
    """Send intraday alert email."""
    if not alerts or not GMAIL_ADDRESS:
        return

    subject = f"🚨 Trading Alert — {len(alerts)} signal(s) | {datetime.now().strftime('%H:%M %d %b')}"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;">
    <h2 style="color:#cc0000;">🚨 Live Trading Alerts — {datetime.now().strftime('%H:%M, %d %B %Y')}</h2>
    <p>{len(alerts)} signal(s) detected across your watchlist</p>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%;">
    <tr style="background:#1a1a2e;color:white;">
        <th>Ticker</th><th>Signal</th><th>Priority</th>
        <th>Price</th><th>Change</th><th>RSI</th><th>Action</th>
    </tr>
    """

    for a in alerts:
        priority_color = "#cc0000" if a["priority"] == "HIGH" else "#ff8800"
        html += f"""
        <tr>
            <td><strong>{a['ticker']}</strong></td>
            <td>{a['message']}</td>
            <td style="color:{priority_color};font-weight:bold;">{a['priority']}</td>
            <td>${a['price']}</td>
            <td>{'+' if a['pct_change'] > 0 else ''}{a['pct_change']}%</td>
            <td>{a['rsi']}</td>
            <td><strong>{a['action']}</strong></td>
        </tr>
        """

    html += """
    </table>
    <p style="color:#666;font-size:12px;margin-top:20px;">
    Trading Analyser 2.0 | This is not financial advice. Always do your own research.
    </p>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = REPORT_EMAIL
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"Alert email sent: {len(alerts)} signals")
    except Exception as e:
        print(f"Failed to send alert email: {e}")


def run_intraday_scan():
    """Main intraday scan entry point."""
    print(f"\n{'='*60}")
    print(f"Intraday Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    asx_open = is_asx_open()
    nasdaq_open = is_nasdaq_open()

    if not asx_open and not nasdaq_open:
        print("Markets closed. No scan needed.")
        return

    watchlist = load_watchlist()
    tickers = []
    if asx_open:
        tickers += watchlist.get("asx", []) + watchlist.get("etf", [])
        print("ASX market: OPEN")
    if nasdaq_open:
        tickers += watchlist.get("nasdaq", [])
        print("NASDAQ market: OPEN")

    all_signals = []
    for ticker in tickers:
        print(f"  Scanning {ticker}...")
        signals = detect_intraday_signals(ticker)
        for sig in signals:
            # Only alert if not already alerted today for this signal type
            if not already_alerted_today(ticker, sig["type"]):
                all_signals.append(sig)
                log_alert(ticker, sig["type"], sig["message"])

    if all_signals:
        print(f"\n🚨 {len(all_signals)} NEW signals detected!")
        for s in all_signals:
            print(f"  {s['ticker']}: [{s['priority']}] {s['message']} → {s['action']}")
        send_alert_email(all_signals)
    else:
        print("No new signals this scan.")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_intraday_scan()
