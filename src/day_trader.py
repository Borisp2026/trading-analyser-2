"""Day Trading Strategy Engine — ORB + VWAP + MACD + SuperTrend + BB Squeeze + ATR
8 conditions, require 5/8 for BUY signal.
Target: +5% net (incl fees) | Stop: 1.5x ATR | Max 2 positions.
"""
import pandas as pd
import numpy as np
import sys, os
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from indicators import calc_macd, calc_supertrend, calc_bollinger, calc_atr

AEST = pytz.timezone('Australia/Sydney')
NYSE = pytz.timezone('America/New_York')
TARGET_PCT   = 0.052  # 5% net after ~0.2% round-trip fees
FEES_PCT     = 0.001  # 0.1% per side (Moomoo ASX)
ATR_MULT     = 1.5    # stop = 1.5 × ATR
MAX_ATR_STOP = 0.035  # cap stop at 3.5%
MIN_ATR_STOP = 0.015  # floor stop at 1.5%
ORB_BARS     = 30
MAX_POSITIONS= 2
MIN_MACRO    = 50
REQUIRED_CONDITIONS = 3   # out of 8


def _rsi(series, period=7):
    d = series.diff()
    g = d.clip(lower=0).rolling(period).mean()
    l = (-d.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + g / l)


def _vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


def check_entry(ticker, df, macro_score=100):
    """
    Evaluate 8 entry conditions for one ticker.
    Returns dict with signal=BUY or SKIP plus full reasoning.
    """
    if df is None or len(df) < ORB_BARS + 10:
        return {"ticker": ticker, "signal": "SKIP", "reasons": ["Insufficient bars"]}

    if macro_score < MIN_MACRO:
        return {"ticker": ticker, "signal": "SKIP",
                "reasons": [f"Macro gate {macro_score:.0f} < {MIN_MACRO}"]}

    today = df.index.date[-1]
    day   = df[df.index.date == today]
    if len(day) < ORB_BARS + 5:
        return {"ticker": ticker, "signal": "SKIP", "reasons": ["Insufficient today bars"]}

    orb   = day.iloc[:ORB_BARS]
    now   = day.iloc[-1]

    orb_high = float(orb["High"].max())
    orb_low  = float(orb["Low"].min())
    price    = float(now["Close"])
    vol      = float(now["Volume"])
    avg_vol  = float(day["Volume"].mean()) or 1

    # VWAP
    vwap_ser = _vwap(day)
    vwap     = float(vwap_ser.iloc[-1])

    # RSI
    rsi_ser  = _rsi(day["Close"], 7)
    rsi      = float(rsi_ser.iloc[-1]) if not pd.isna(rsi_ser.iloc[-1]) else 50.0

    # ATR-based stop
    atr_info = calc_atr(day, 14)
    atr_pct  = atr_info["atr_pct"] / 100
    stop_pct = max(MIN_ATR_STOP, min(MAX_ATR_STOP, ATR_MULT * atr_pct))

    # MACD (use longer history if available)
    hist_bars = df.tail(100)
    macd_info = calc_macd(hist_bars["Close"]) if len(hist_bars) >= 35 else {"bullish": False, "crossed_up": False}

    # SuperTrend (use longer history)
    st_df     = df.tail(60) if len(df) >= 60 else df
    st_info   = calc_supertrend(st_df) if len(st_df) >= 20 else {"bullish": False}

    # Bollinger Bands on today's bars
    bb_info   = calc_bollinger(day["Close"]) if len(day) >= 25 else {"squeeze": False, "breakout_upper": False, "pct_b": 0.5}

    conditions = {
        "ORB breakout":       price > orb_high,
        "Above VWAP":         price > vwap,
        "RSI 45–75":          45 <= rsi <= 75,
        "Volume spike":       vol >= avg_vol * 1.2,
        "Not overextended":   price < orb_high * 1.08,
        "MACD bullish":       macd_info.get("bullish", False),
        "SuperTrend bullish": st_info.get("bullish", False),
        "BB squeeze/breakout":bb_info.get("squeeze", False) or bb_info.get("breakout_upper", False),
    }

    met     = [k for k, v in conditions.items() if v]
    not_met = [k for k, v in conditions.items() if not v]
    score   = len(met)

    target = round(price * (1 + TARGET_PCT), 3)
    stop   = round(price * (1 - stop_pct), 3)

    if score >= REQUIRED_CONDITIONS:
        return {
            "ticker":         ticker,
            "signal":         "BUY",
            "entry_price":    round(price, 3),
            "target":         target,
            "stop":           stop,
            "stop_pct":       round(stop_pct * 100, 2),
            "vwap":           round(vwap, 3),
            "rsi":            round(rsi, 1),
            "macd_bullish":   macd_info.get("bullish"),
            "st_bullish":     st_info.get("bullish"),
            "bb_squeeze":     bb_info.get("squeeze"),
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
    entry  = position["entry_price"]
    target = position["target"]
    stop   = position["stop"]
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
    if ticker.endswith(".AX"):
        now = datetime.now(AEST)
        return now.weekday() < 5 and (now.hour > 10 or (now.hour == 10 and now.minute >= 30)) and now.hour < 16
    else:
        now = datetime.now(NYSE)
        return now.weekday() < 5 and (now.hour > 10 or (now.hour == 10)) and now.hour < 15
