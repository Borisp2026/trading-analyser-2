"""
Shared Technical Indicators Library
MACD, SuperTrend, Bollinger Bands, ATR, RS vs XJO, 52-Week High Proximity
"""
import pandas as pd
import numpy as np


def calc_macd(series, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram, is_bullish)"""
    ema_fast   = series.ewm(span=fast,   adjust=False).mean()
    ema_slow   = series.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    is_bullish = bool(macd_line.iloc[-1] > signal_line.iloc[-1])
    crossed_up = bool(macd_line.iloc[-1] > signal_line.iloc[-1] and
                      macd_line.iloc[-2] <= signal_line.iloc[-2])
    return {
        "macd":       round(float(macd_line.iloc[-1]), 4),
        "signal":     round(float(signal_line.iloc[-1]), 4),
        "histogram":  round(float(histogram.iloc[-1]), 4),
        "bullish":    is_bullish,
        "crossed_up": crossed_up,
    }


def calc_supertrend(df, period=7, multiplier=3.0):
    """ATR-based SuperTrend. Returns (is_bullish, supertrend_value)."""
    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]

    prev_close = close.shift(1)
    tr = pd.concat([high - low,
                    (high - prev_close).abs(),
                    (low  - prev_close).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(span=period, adjust=False).mean()

    hl2   = (high + low) / 2
    upper = hl2 + multiplier * atr_s
    lower = hl2 - multiplier * atr_s

    st    = [float("nan")] * len(df)
    bull  = [True]         * len(df)

    for i in range(1, len(df)):
        prev_st   = st[i-1]
        prev_bull = bull[i-1]
        c = float(close.iloc[i])
        u = float(upper.iloc[i])
        l = float(lower.iloc[i])
        pu= float(upper.iloc[i-1]) if not pd.isna(upper.iloc[i-1]) else u
        pl= float(lower.iloc[i-1]) if not pd.isna(lower.iloc[i-1]) else l

        final_lower = l if l > pl or float(close.iloc[i-1]) < pl else pl
        final_upper = u if u < pu or float(close.iloc[i-1]) > pu else pu

        if pd.isna(prev_st) or prev_bull:
            st[i]   = final_lower if c >= final_lower else final_upper
            bull[i] = c >= final_lower
        else:
            st[i]   = final_upper if c <= final_upper else final_lower
            bull[i] = c > final_upper

    return {
        "bullish":    bull[-1],
        "value":      round(st[-1], 3) if not pd.isna(st[-1]) else None,
    }


def calc_bollinger(series, period=20, std_mult=2.0):
    """Bollinger Bands + squeeze detection."""
    mid   = series.rolling(period).mean()
    std   = series.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    bw    = (upper - lower) / mid   # bandwidth

    price    = float(series.iloc[-1])
    bw_now   = float(bw.iloc[-1])
    bw_50    = float(bw.rolling(50).quantile(0.2).iloc[-1]) if len(series) >= 70 else bw_now

    squeeze        = bw_now < bw_50               # bands are unusually tight
    breakout_upper = price > float(upper.iloc[-1])
    breakout_lower = price < float(lower.iloc[-1])

    return {
        "upper":          round(float(upper.iloc[-1]), 3),
        "middle":         round(float(mid.iloc[-1]),   3),
        "lower":          round(float(lower.iloc[-1]), 3),
        "bandwidth":      round(bw_now, 4),
        "squeeze":        squeeze,
        "breakout_upper": breakout_upper,
        "breakout_lower": breakout_lower,
        "pct_b":          round((price - float(lower.iloc[-1])) /
                                max(float(upper.iloc[-1]) - float(lower.iloc[-1]), 0.0001), 3),
    }


def calc_atr(df, period=14):
    """Average True Range — raw value and % of price."""
    close    = df["Close"]
    high     = df["High"]
    low      = df["Low"]
    prev_c   = close.shift(1)
    tr       = pd.concat([high - low,
                           (high - prev_c).abs(),
                           (low  - prev_c).abs()], axis=1).max(axis=1)
    atr_val  = float(tr.rolling(period).mean().iloc[-1])
    price    = float(close.iloc[-1])
    return {
        "atr":     round(atr_val, 4),
        "atr_pct": round(atr_val / price * 100, 3) if price else 0,
    }


def calc_rs_vs_xjo(ticker_close, xjo_close, period=63):
    """
    Relative Strength vs XJO over `period` trading days.
    RS > 1 = outperforming ASX 200.
    """
    n = min(period, len(ticker_close) - 1, len(xjo_close) - 1)
    if n < 5:
        return {"rs": 1.0, "outperforming": False, "ticker_ret": 0, "xjo_ret": 0}
    t_ret  = float(ticker_close.iloc[-1]) / float(ticker_close.iloc[-n]) - 1
    x_ret  = float(xjo_close.iloc[-1])   / float(xjo_close.iloc[-n])   - 1
    rs     = round(1 + (t_ret - x_ret), 3)
    return {
        "rs":           rs,
        "outperforming": rs > 1.0,
        "ticker_ret":   round(t_ret * 100, 2),
        "xjo_ret":      round(x_ret * 100, 2),
    }


def calc_52w_high(df):
    """
    52-week high proximity score (0-100).
    100 = AT the 52w high; 0 = at the 52w low.
    Also flags if within 5% of high (strong momentum zone).
    """
    n     = min(252, len(df))
    price = float(df["Close"].iloc[-1])
    hi    = float(df["High"].tail(n).max())
    lo    = float(df["Low"].tail(n).min())
    rng   = hi - lo if hi != lo else 1
    score = round((price - lo) / rng * 100, 1)
    pct_from_high = round((price - hi) / hi * 100, 2)
    return {
        "score":          score,
        "pct_from_high":  pct_from_high,
        "high_52w":       round(hi, 3),
        "low_52w":        round(lo, 3),
        "near_high":      pct_from_high >= -5,   # within 5% of 52w high
    }
