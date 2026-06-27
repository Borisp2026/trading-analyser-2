"""
Cycle Analysis module for Trading Analyser 2.0
Implements DJRTrading Hurst-style Daily/Intermediate Cycle methodology.

Concepts:
  DCL  = Daily Cycle Low (cycle start/end)
  HCH  = Half Cycle High (high in first half)
  HCL  = Half Cycle Low (pullback after HCH, used to draw trendline)
  DCH  = Daily Cycle High (overall cycle peak)
  Right-translated = DCH after midpoint (bullish)
  Left-translated  = DCH before midpoint (bearish, risk of failed cycle)
"""

import numpy as np
import pandas as pd


def find_swing_points(series: pd.Series, window: int = 5):
    """Find local highs and lows using a rolling window."""
    highs = []
    lows = []
    idx = series.index.tolist()
    vals = series.values
    n = len(vals)
    for i in range(window, n - window):
        segment_high = vals[i - window: i + window + 1]
        segment_low = vals[i - window: i + window + 1]
        if vals[i] == max(segment_high):
            highs.append(idx[i])
        if vals[i] == min(segment_low):
            lows.append(idx[i])
    return highs, lows


def auto_detect_cycle_length(close: pd.Series) -> int:
    """Auto-detect dominant cycle length via autocorrelation (20-60 bar range)."""
    if len(close) < 80:
        return 35  # default
    try:
        returns = close.pct_change().dropna()
        autocorrs = [abs(returns.autocorr(lag=lag)) for lag in range(20, 61)]
        best_lag = 20 + int(np.argmax(autocorrs))
        return max(20, min(60, best_lag))
    except Exception:
        return 35


def detect_daily_cycles(close: pd.Series, high: pd.Series, low: pd.Series):
    """
    Detect all completed daily cycles. Returns list of cycle dicts.
    Each cycle: dcl0, hch, hcl, dch, dcl1, translation, failed
    """
    if len(close) < 60:
        return None, {"status": "insufficient_data"}

    cycle_len = auto_detect_cycle_length(close)
    window = max(3, cycle_len // 8)

    _, low_idx = find_swing_points(low, window=window)
    high_idx, _ = find_swing_points(high, window=window)

    if len(low_idx) < 2:
        return cycle_len, {"status": "no_cycles_detected"}

    # Filter major lows: require prominence (drop at least 2% from surrounding highs)
    close_arr = close.values
    close_dates = close.index.tolist()

    def get_pos(date):
        try:
            return close_dates.index(date)
        except ValueError:
            return None

    major_lows = []
    min_gap = cycle_len // 2
    for i, ldate in enumerate(low_idx):
        pos = get_pos(ldate)
        if pos is None:
            continue
        # Must be at least min_gap bars from last major low
        if major_lows:
            last_pos = get_pos(major_lows[-1])
            if last_pos is not None and (pos - last_pos) < min_gap:
                # Keep the lower one
                if close_arr[pos] < close_arr[last_pos]:
                    major_lows[-1] = ldate
                continue
        major_lows.append(ldate)

    if len(major_lows) < 2:
        return cycle_len, {"status": "insufficient_major_lows"}

    cycles = []
    high_set = set(high_idx)

    for i in range(len(major_lows) - 1):
        dcl0_date = major_lows[i]
        dcl1_date = major_lows[i + 1]
        dcl0_pos = get_pos(dcl0_date)
        dcl1_pos = get_pos(dcl1_date)
        if dcl0_pos is None or dcl1_pos is None:
            continue

        actual_len = dcl1_pos - dcl0_pos
        midpoint_pos = dcl0_pos + actual_len // 2
        midpoint_date = close_dates[midpoint_pos]

        # Find DCH = highest point between DCL0 and DCL1
        segment_high = high[dcl0_date:dcl1_date]
        if segment_high.empty:
            continue
        dch_date = segment_high.idxmax()
        dch_pos = get_pos(dch_date)
        dch_price = round(float(high[dch_date]), 4)

        # Translation
        right_translated = dch_pos > midpoint_pos
        translation = "RIGHT" if right_translated else "LEFT"

        # HCH = first swing high before midpoint
        highs_before_mid = [h for h in high_idx if dcl0_date < h <= midpoint_date and h != dch_date]
        hch_date = highs_before_mid[0] if highs_before_mid else dch_date
        hch_price = round(float(high[hch_date]), 4)

        # HCL = lowest swing low between HCH and DCH
        hcl_date = None
        hcl_price = None
        if hch_date != dch_date:
            lows_between = [l for l in low_idx if hch_date < l < dch_date]
            if lows_between:
                hcl_date = min(lows_between, key=lambda d: float(low[d]))
                hcl_price = round(float(low[hcl_date]), 4)
            else:
                # Fallback: minimum in that range
                seg = low[hch_date:dch_date]
                if not seg.empty:
                    hcl_date = seg.idxmin()
                    hcl_price = round(float(seg.min()), 4)

        # Failed cycle check: DCL1 < DCL0 (lower low = failed)
        dcl0_price = round(float(low[dcl0_date]), 4)
        dcl1_price = round(float(low[dcl1_date]), 4)
        failed = dcl1_price < dcl0_price

        # Cycle number within a presumed 4-cycle intermediate
        cycle_num = (i % 4) + 1

        cycles.append({
            "cycle_num": cycle_num,
            "dcl0_date": str(dcl0_date)[:10],
            "dcl0_price": dcl0_price,
            "hch_date": str(hch_date)[:10],
            "hch_price": hch_price,
            "hcl_date": str(hcl_date)[:10] if hcl_date else None,
            "hcl_price": hcl_price,
            "dch_date": str(dch_date)[:10],
            "dch_price": dch_price,
            "dcl1_date": str(dcl1_date)[:10],
            "dcl1_price": dcl1_price,
            "translation": translation,
            "failed": failed,
            "length": actual_len,
        })

    return cycle_len, cycles


def check_trendline_break(close: pd.Series, cycle: dict) -> bool:
    """Returns True if price has closed below the HCL trendline (bearish signal)."""
    if not cycle or not cycle.get("hcl_price"):
        return False
    try:
        hcl_price = cycle["hcl_price"]
        current_price = float(close.iloc[-1])
        return current_price < hcl_price
    except Exception:
        return False


def check_confirmation_signal(close: pd.Series, cycle: dict, mas: dict) -> bool:
    """
    Returns True if 90% confirmation signal is present:
    Price closes above HCH resistance AND above 10-day SMA — confirms new cycle upleg.
    """
    if not cycle or not cycle.get("hch_price"):
        return False
    try:
        hch_price = cycle["hch_price"]
        current_price = float(close.iloc[-1])
        sma10 = mas.get("sma_10", 0)
        return current_price > hch_price and current_price > sma10
    except Exception:
        return False


def analyse_cycles(df: pd.DataFrame, mas: dict) -> dict:
    """Main entry point. Returns cycle analysis dict."""
    if df is None or len(df) < 60:
        return {"status": "insufficient_data", "cycle_score": 50, "cycle_signal": "NEUTRAL"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    cycle_len, cycles = detect_daily_cycles(close, high, low)

    if isinstance(cycles, dict):
        # Error dict returned
        return {
            "status": cycles.get("status", "unknown"),
            "cycle_len": cycle_len,
            "cycle_score": 50,
            "cycle_signal": "NEUTRAL",
        }

    if not cycles:
        return {"status": "no_cycles", "cycle_len": cycle_len, "cycle_score": 50, "cycle_signal": "NEUTRAL"}

    current = cycles[-1]
    trendline_break = check_trendline_break(close, current)
    confirmation = check_confirmation_signal(close, current, mas)

    # Estimate where we are in the current incomplete cycle
    last_dcl1_date = current["dcl1_date"]
    try:
        bars_since_dcl = len(close[last_dcl1_date:]) - 1
    except Exception:
        bars_since_dcl = 0

    pct_through = round((bars_since_dcl / cycle_len) * 100, 1) if cycle_len else 0
    high_risk_zone = pct_through > 70  # past 70% = likely approaching DCH / late cycle

    # Cycle score
    score = 50
    if current["translation"] == "RIGHT":
        score += 15
    else:
        score -= 10

    if current["failed"]:
        score -= 20

    if trendline_break:
        score -= 20
    elif confirmation:
        score += 15

    if high_risk_zone:
        score -= 10

    # Check intermediate cycle position (are we in cycle 3-4 = high risk?)
    if current["cycle_num"] in (3, 4):
        score -= 8

    score = max(0, min(100, score))

    if score >= 65:
        cycle_signal = "CYCLE_BUY"
    elif score >= 50:
        cycle_signal = "CYCLE_HOLD"
    elif score >= 35:
        cycle_signal = "CYCLE_CAUTION"
    else:
        cycle_signal = "CYCLE_AVOID"

    # Build reason text
    reasons = []
    reasons.append(f"{current['translation']}-translated cycle (cycle #{current['cycle_num']} of 4)")
    if current["failed"]:
        reasons.append("⚠️ FAILED CYCLE — lower low than start, bearish")
    if trendline_break:
        reasons.append("⚠️ Trendline BREAK — closed below HCL support")
    if confirmation:
        reasons.append("✅ 90% confirmation signal — above HCH resistance and 10D SMA")
    if high_risk_zone:
        reasons.append(f"⏰ {pct_through}% through cycle — late-cycle, higher risk zone")
    if current["cycle_num"] in (3, 4):
        reasons.append("🔴 Intermediate Cycle 3-4: highest risk zone, reduce exposure")

    # Entry/exit guidance
    if cycle_signal == "CYCLE_BUY":
        entry_note = "Enter near DCL or on confirmation signal above HCH + 10D SMA"
        exit_note = f"Exit/tighten stops if trendline breaks below HCL (~${current.get('hcl_price', 'N/A')})"
    elif cycle_signal in ("CYCLE_CAUTION", "CYCLE_AVOID"):
        entry_note = "Wait for next DCL before entering new positions"
        exit_note = "Reduce or exit existing longs"
    else:
        entry_note = "Monitor for confirmation signal"
        exit_note = "Hold with stop below most recent HCL"

    return {
        "status": "ok",
        "cycle_len": cycle_len,
        "cycle_score": score,
        "cycle_signal": cycle_signal,
        "current_cycle": current,
        "bars_since_dcl": bars_since_dcl,
        "pct_through_cycle": pct_through,
        "high_risk_zone": high_risk_zone,
        "trendline_break": trendline_break,
        "confirmation_signal": confirmation,
        "reasons": reasons,
        "entry_note": entry_note,
        "exit_note": exit_note,
        "all_cycles": cycles,
    }
