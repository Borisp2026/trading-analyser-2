"""Day Trading Strategy Engine — ORB + VWAP + RSI
Opening Range Breakout with VWAP confirmation.
Target: +5% per trade | Stop: -2% | Max 2 positions.
"""
import pandas as pd
import numpy as np
from datetime import datetime, time, date
import pytz

AEST = pytz.timezone('Australia/Sydney')
NYSE  = pytz.timezone('America/New_York')
TARGET_PCT  = 0.05   # 5% take profit
STOP_PCT    = 0.02   # 2% stop loss
ORB_BARS    = 30     # Opening range = first 30 x 1-min bars
MAX_POSITIONS = 2
MIN_MACRO   = 50     # Skip all trades if macro gate < 50


def _rsi(series, period=7):
    d = series.diff()
    g = d.clip(lower=0).rolling(period).mean()
    l = (-d.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + g / l)


def _vwap(df):
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * df['Volume']).cumsum() / df['Volume'].cumsum()


def check_entry(ticker, df, macro_score=100):
    """
    Evaluate entry conditions for one ticker.
    Returns dict with signal=BUY or SKIP plus full reasoning.
    """
    if df is None or len(df) < ORB_BARS + 5:
        return {"ticker": ticker, "signal": "SKIP", "reasons": ["Insufficient bars"]}

    if macro_score < MIN_MACRO:
        return {"ticker": ticker, "signal": "SKIP", "reasons": [f"Macro gate {macro_score:.0f} < {MIN_MACRO} — sit out"]}

    # Today's bars only
    today = df.index.date[-1]
    day = df[df.index.date == today]
    if len(day) < ORB_BARS + 2:
        return {"ticker": ticker, "signal": "SKIP", "reasons": ["Not enough today's bars yet"]}

    orb = day.iloc[:ORB_BARS]
    now = day.iloc[-1]

    orb_high = float(orb['High'].max())
    orb_low  = float(orb['Low'].min())
    price    = float(now['Close'])
    vol      = float(now['Volume'])
    avg_vol  = float(day['Volume'].mean())

    vwap_series = _vwap(day)
    vwap    = float(vwap_series.iloc[-1])
    rsi_ser = _rsi(day['Close'], 7)
    rsi     = float(rsi_ser.iloc[-1]) if not pd.isna(rsi_ser.iloc[-1]) else 50.0

    conditions = {
        "ORB breakout":    price > orb_high,
        "Above VWAP":      price > vwap,
        "RSI 45-75":       45 <= rsi <= 75,
        "Volume spike":    vol >= avg_vol * 1.2,
        "Not overextended": price < orb_high * 1.08,
    }

    met     = [k for k, v in conditions.items() if v]
    not_met = [k for k, v in conditions.items() if not v]
    score   = len(met)

    if score >= 3:
        return {
            "ticker":         ticker,
            "signal":         "BUY",
            "entry_price":    round(price, 3),
            "target":         round(price * (1 + TARGET_PCT), 3),
            "stop":           round(price * (1 - STOP_PCT), 3),
            "vwap":           round(vwap, 3),
            "rsi":            round(rsi, 1),
            "orb_high":       round(orb_high, 3),
            "orb_low":        round(orb_low, 3),
            "conditions_met": score,
            "reasons":        [f"✓ {c}" for c in met],
            "timestamp":      datetime.now().isoformat(),
        }

    return {
        "ticker":         ticker,
        "signal":         "SKIP",
        "price":          round(price, 3),
        "vwap":           round(vwap, 3),
        "rsi":            round(rsi, 1),
        "conditions_met": score,
        "reasons":        [f"✓ {c}" for c in met] + [f"✗ {c}" for c in not_met],
        "timestamp":      datetime.now().isoformat(),
    }


def check_exit(position, current_price):
    """Check target/stop/EOD exit for an open position."""
    entry  = position['entry_price']
    target = position['target']
    stop   = position['stop']
    pnl    = round((current_price - entry) / entry * 100, 2)

    now_aest = datetime.now(AEST)
    if current_price >= target:
        return {"exit": True,  "reason": "TARGET HIT ✓", "pnl_pct": pnl, "exit_price": round(current_price, 3)}
    if current_price <= stop:
        return {"exit": True,  "reason": "STOP HIT ✗",   "pnl_pct": pnl, "exit_price": round(current_price, 3)}
    if now_aest.hour >= 15 and now_aest.minute >= 30:
        return {"exit": True,  "reason": "EOD EXIT",      "pnl_pct": pnl, "exit_price": round(current_price, 3)}
    return {"exit": False, "reason": "HOLDING",           "pnl_pct": pnl, "current_price": round(current_price, 3)}


def is_trading_window(ticker):
    """Return True if within valid trading window (30 min after open, before 3:30pm)."""
    if ticker.endswith('.AX'):
        now = datetime.now(AEST)
        open_h, open_m = 10, 30   # 30 min after ASX open
        close_h, close_m = 15, 30
    else:
        now = datetime.now(NYSE)
        open_h, open_m = 10, 0
        close_h, close_m = 15, 30

    after_open  = (now.hour > open_h) or (now.hour == open_h and now.minute >= open_m)
    before_close = (now.hour < close_h) or (now.hour == close_h and now.minute <= close_m)
    return now.weekday() < 5 and after_open and before_close
