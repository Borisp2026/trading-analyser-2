"""
Technical indicators module for Trading Analyser 2.0
Covers: RSI, MACD, Bollinger Bands, Volume analysis, Moving Averages, ATR, Stochastic
"""

import pandas as pd
import numpy as np


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_bollinger(close: pd.Series, period=20, std_dev=2):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return upper, sma, lower, pct_b


def calc_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def calc_stochastic(high, low, close, k_period=14, d_period=3):
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return k, d


def calc_volume_signal(volume: pd.Series, period=20) -> dict:
    avg_vol = volume.rolling(period).mean()
    latest_vol = volume.iloc[-1]
    avg = avg_vol.iloc[-1]
    ratio = latest_vol / avg if avg > 0 else 1.0
    if ratio >= 3.0:
        signal = "EXTREME_SPIKE"
    elif ratio >= 2.0:
        signal = "HIGH_VOLUME"
    elif ratio >= 1.5:
        signal = "ABOVE_AVERAGE"
    elif ratio < 0.5:
        signal = "LOW_VOLUME"
    else:
        signal = "NORMAL"
    return {"ratio": round(ratio, 2), "signal": signal, "avg_volume": int(avg)}


def calc_moving_averages(close: pd.Series) -> dict:
    return {
        "sma_10": round(close.rolling(10).mean().iloc[-1], 4),
        "sma_20": round(close.rolling(20).mean().iloc[-1], 4),
        "sma_50": round(close.rolling(50).mean().iloc[-1], 4),
        "sma_200": round(close.rolling(200).mean().iloc[-1], 4),
        "ema_9": round(close.ewm(span=9, adjust=False).mean().iloc[-1], 4),
        "ema_21": round(close.ewm(span=21, adjust=False).mean().iloc[-1], 4),
    }


def analyse_technicals(df: pd.DataFrame) -> dict:
    """
    Full technical analysis on OHLCV dataframe.
    Returns a structured dict with all indicators + a composite score (0-100).
    """
    if df is None or len(df) < 30:
        return {"error": "Insufficient data"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # RSI
    rsi = calc_rsi(close)
    rsi_val = round(rsi.iloc[-1], 2)
    rsi_prev = round(rsi.iloc[-2], 2)

    # MACD
    macd_line, signal_line, histogram = calc_macd(close)
    macd_val = round(macd_line.iloc[-1], 4)
    macd_sig = round(signal_line.iloc[-1], 4)
    macd_hist = round(histogram.iloc[-1], 4)
    macd_cross = (macd_line.iloc[-2] < signal_line.iloc[-2]) and (macd_line.iloc[-1] > signal_line.iloc[-1])
    macd_death = (macd_line.iloc[-2] > signal_line.iloc[-2]) and (macd_line.iloc[-1] < signal_line.iloc[-1])

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower, pct_b = calc_bollinger(close)
    pct_b_val = round(pct_b.iloc[-1], 3) if not pd.isna(pct_b.iloc[-1]) else 0.5
    price = round(close.iloc[-1], 4)

    # ATR (for stop-loss suggestions)
    atr = calc_atr(high, low, close)
    atr_val = round(atr.iloc[-1], 4)

    # Stochastic
    stoch_k, stoch_d = calc_stochastic(high, low, close)
    stoch_k_val = round(stoch_k.iloc[-1], 2) if not pd.isna(stoch_k.iloc[-1]) else 50
    stoch_d_val = round(stoch_d.iloc[-1], 2) if not pd.isna(stoch_d.iloc[-1]) else 50

    # Volume
    vol_signal = calc_volume_signal(volume)

    # Moving averages
    mas = calc_moving_averages(close)

    # Trend direction
    above_50sma = price > mas["sma_50"] if not pd.isna(mas["sma_50"]) else None
    above_200sma = price > mas["sma_200"] if not pd.isna(mas["sma_200"]) else None
    golden_cross = (mas["sma_50"] > mas["sma_200"]) if (not pd.isna(mas["sma_50"]) and not pd.isna(mas["sma_200"])) else None

    # Price change
    price_1d = round(((price - close.iloc[-2]) / close.iloc[-2]) * 100, 2)
    price_5d = round(((price - close.iloc[-6]) / close.iloc[-6]) * 100, 2) if len(close) > 5 else 0
    price_20d = round(((price - close.iloc[-21]) / close.iloc[-21]) * 100, 2) if len(close) > 20 else 0

    # 52-week range
    high_52w = round(high.rolling(252).max().iloc[-1], 4)
    low_52w = round(low.rolling(252).min().iloc[-1], 4)
    pct_from_52w_high = round(((price - high_52w) / high_52w) * 100, 2)

    # --- Composite Score (0-100) ---
    score = 50  # neutral start

    # RSI signals
    if rsi_val < 30:
        score += 15  # oversold = buy opportunity
    elif rsi_val < 40:
        score += 8
    elif rsi_val > 70:
        score -= 15  # overbought
    elif rsi_val > 60:
        score -= 5

    # RSI momentum (rising vs falling)
    if rsi_val > rsi_prev:
        score += 3
    else:
        score -= 3

    # MACD
    if macd_cross:
        score += 12  # bullish crossover
    elif macd_death:
        score -= 12
    elif macd_val > macd_sig:
        score += 5
    else:
        score -= 5

    # Bollinger
    if pct_b_val < 0.1:
        score += 10  # near lower band = potential bounce
    elif pct_b_val > 0.9:
        score -= 10  # near upper = potential pullback

    # Volume
    if vol_signal["signal"] in ("HIGH_VOLUME", "EXTREME_SPIKE") and price_1d > 0:
        score += 8  # volume-confirmed move up
    elif vol_signal["signal"] in ("HIGH_VOLUME", "EXTREME_SPIKE") and price_1d < 0:
        score -= 8

    # Trend
    if above_50sma:
        score += 5
    elif above_50sma is False:
        score -= 5
    if golden_cross:
        score += 5
    elif golden_cross is False:
        score -= 5

    # Stochastic
    if stoch_k_val < 20:
        score += 5
    elif stoch_k_val > 80:
        score -= 5

    score = max(0, min(100, score))

    # Signal label
    if score >= 70:
        signal = "STRONG_BUY"
        color = "green"
    elif score >= 55:
        signal = "BUY"
        color = "lightgreen"
    elif score >= 45:
        signal = "HOLD"
        color = "orange"
    elif score >= 30:
        signal = "WEAK"
        color = "salmon"
    else:
        signal = "AVOID"
        color = "red"

    # Stop loss suggestion (1.5x ATR below current price)
    stop_loss = round(price - (1.5 * atr_val), 4) if atr_val else None
    take_profit = round(price + (3 * atr_val), 4) if atr_val else None  # 2:1 risk/reward

    return {
        "price": price,
        "price_1d_pct": price_1d,
        "price_5d_pct": price_5d,
        "price_20d_pct": price_20d,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": pct_from_52w_high,
        "rsi": rsi_val,
        "rsi_prev": rsi_prev,
        "macd": macd_val,
        "macd_signal": macd_sig,
        "macd_hist": macd_hist,
        "macd_bullish_cross": macd_cross,
        "macd_death_cross": macd_death,
        "bb_upper": round(bb_upper.iloc[-1], 4),
        "bb_mid": round(bb_mid.iloc[-1], 4),
        "bb_lower": round(bb_lower.iloc[-1], 4),
        "pct_b": pct_b_val,
        "atr": atr_val,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stoch_k": stoch_k_val,
        "stoch_d": stoch_d_val,
        "volume": int(volume.iloc[-1]),
        "volume_signal": vol_signal,
        "moving_averages": mas,
        "above_50sma": above_50sma,
        "above_200sma": above_200sma,
        "golden_cross": golden_cross,
        "tech_score": score,
        "signal": signal,
        "color": color,
    }
