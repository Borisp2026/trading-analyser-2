"""
Zen Trading — pure detection/classification.

"Zen Trading" isn't one single, publicly documented system the way the
DJRTrading Hurst Cycle methodology was (screenshots, explicit rules). Research
across every public source found (Chad McMillan's "Zen Trading Method" book,
the Zen Trading Strategies platform, general "maximum upside, minimum stress"
trading-plan writeups) converges on the same toolkit, so this is a coherent,
documented synthesis of that shared philosophy, not a literal reproduction of
any one paywalled system:

  - Heiken-Ashi candles for a calmer, noise-filtered trend read (the core
    Chad McMillan technique)
  - trend-following breakout entries -- only with an already-established
    trend, on a break of recent resistance ("First Breakout"/"Riding the
    Trend")
  - a hard minimum reward:risk filter -- "maximum upside, minimum stress" in
    practice means patience/selectivity over frequency, not every breakout
  - a volatility-scaled trailing stop, with the exit trigger being trend
    reversal (calm discipline) rather than prediction or emotion

Mirrors cycle_analysis.py's contract: analyse_zen(df) returns one dict per
ticker with a stable `status` key and stable key set across every branch, so
downstream code never needs branchy existence checks.
"""
import pandas as pd

BREAKOUT_LOOKBACK = 20      # bars of prior high/low to break out of
MIN_TREND_BARS = 4          # consecutive same-direction HA candles before a
                             # trend counts as "calm"/confirmed rather than noise
MIN_REWARD_RISK = 2.0       # "maximum upside, minimum stress" -- the patience/
                             # selectivity filter; below this it's a HOLD, not a chase
ATR_STOP_MULT = 2.0         # trailing stop = entry - ATR*mult


def calc_heiken_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Standard Heiken-Ashi transform: HA close = avg(OHLC); HA open = avg of
    the prior bar's HA open/close (seeded from the first real open/close).
    Smooths noise so the underlying trend reads calmer than raw candles."""
    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [float((df["Open"].iloc[0] + df["Close"].iloc[0]) / 2)]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + float(ha_close.iloc[i - 1])) / 2)
    ha_open = pd.Series(ha_open, index=df.index)
    ha_high = pd.concat([df["High"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["Low"], ha_open, ha_close], axis=1).min(axis=1)
    return pd.DataFrame({
        "open": ha_open, "close": ha_close, "high": ha_high, "low": ha_low,
        "bullish": ha_close > ha_open,
    })


def detect_ha_trend(ha: pd.DataFrame, min_consecutive: int = MIN_TREND_BARS) -> dict:
    """Current trend direction + how many consecutive same-colour HA candles
    it's run. Fewer than min_consecutive reads as CHOPPY (not yet a real
    trend), regardless of which colour the last candle happened to be."""
    bullish = ha["bullish"]
    last = bool(bullish.iloc[-1])
    run = 1
    for i in range(len(bullish) - 2, -1, -1):
        if bool(bullish.iloc[i]) == last:
            run += 1
        else:
            break
    direction = ("BULLISH" if last else "BEARISH") if run >= min_consecutive else "CHOPPY"
    return {"direction": direction, "consecutive_bars": run, "last_bullish": last}


def detect_breakout(df: pd.DataFrame, lookback: int = BREAKOUT_LOOKBACK) -> dict:
    """Trend-following breakout: today's close vs the prior `lookback`-bar
    high/low (today excluded), per Chad McMillan's "First Breakout"/"Riding
    the Trend" approach."""
    if len(df) < lookback + 1:
        return {"bullish_breakout": False, "bearish_breakout": False, "resistance": None, "support": None}
    window = df.iloc[-(lookback + 1):-1]
    resistance = float(window["High"].max())
    support = float(window["Low"].min())
    close = float(df["Close"].iloc[-1])
    return {
        "bullish_breakout": close > resistance, "bearish_breakout": close < support,
        "resistance": round(resistance, 4), "support": round(support, 4),
    }


def compute_zen_stop(df: pd.DataFrame, entry_price: float, atr_mult: float = ATR_STOP_MULT):
    """Volatility-scaled trailing stop (long only -- like every other strategy
    tab in this app, Zen Trading is a BUY strategy). Falls back to a flat 5%
    if ATR can't be computed (too little data)."""
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    if pd.isna(atr) or atr <= 0:
        return round(entry_price * 0.95, 4)
    return round(entry_price - float(atr) * atr_mult, 4)


def _empty(status: str, error: str = None) -> dict:
    d = {
        "status": status, "zen_signal": "HOLD", "zen_score": 50,
        "eligible_for_entry": False, "trend": {}, "breakout": {},
        "price": None, "stop_price": None, "target_price": None,
        "reward_risk": None, "reasons": [],
    }
    if error:
        d["error"] = error
    return d


def analyse_zen(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 30:
        return _empty("insufficient_data")
    try:
        ha = calc_heiken_ashi(df)
        trend = detect_ha_trend(ha)
        breakout = detect_breakout(df)
        price = float(df["Close"].iloc[-1])

        is_setup = trend["direction"] == "BULLISH" and breakout["bullish_breakout"]
        stop_price = compute_zen_stop(df, price) if is_setup else None

        # Target: prior swing range (the breakout leg) projected from the breakout
        # level, floored by MIN_REWARD_RISK*risk -- same "amplitude of the last
        # leg" idea Cycle Trading's predicted_move uses, applied to Zen's range.
        target_price, reward_risk = None, None
        if is_setup and stop_price and breakout.get("resistance") is not None:
            risk = price - stop_price
            support = breakout.get("support") or breakout["resistance"] * 0.95
            leg = breakout["resistance"] - support
            if risk > 0:
                target_price = round(price + max(leg, risk * MIN_REWARD_RISK), 4)
                reward_risk = round((target_price - price) / risk, 2)

        eligible = bool(is_setup and reward_risk is not None and reward_risk >= MIN_REWARD_RISK)

        if trend["direction"] == "BEARISH":
            zen_signal = "AVOID"
        elif trend["direction"] == "CHOPPY":
            zen_signal = "HOLD"
        elif eligible:
            zen_signal = "BUY"
        else:
            zen_signal = "HOLD"  # bullish/breakout but reward:risk too thin -- patience, not a chase

        score = 50
        score += 15 if trend["direction"] == "BULLISH" else -20 if trend["direction"] == "BEARISH" else 0
        score += min(trend["consecutive_bars"], 10)
        score += 15 if breakout["bullish_breakout"] else 0
        if reward_risk:
            score += min(int((reward_risk - MIN_REWARD_RISK) * 5), 15)
        score = max(0, min(100, score))

        reasons = [f"Heiken-Ashi trend {trend['direction']} for {trend['consecutive_bars']} bars"]
        if breakout["bullish_breakout"]:
            reasons.append(f"Breakout above {BREAKOUT_LOOKBACK}-bar high (${breakout['resistance']})")
        if reward_risk is not None:
            reasons.append(f"Reward:risk {reward_risk}:1 ({'meets' if eligible else 'below'} {MIN_REWARD_RISK}:1 minimum)")

        return {
            "status": "ok",
            "zen_signal": zen_signal, "zen_score": round(score, 1),
            "eligible_for_entry": eligible,
            "trend": trend, "breakout": breakout,
            "price": round(price, 4), "stop_price": stop_price, "target_price": target_price,
            "reward_risk": reward_risk,
            "reasons": reasons,
        }
    except Exception as e:
        return _empty("error", error=str(e))
