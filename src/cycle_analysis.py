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

  ICL/ICH = Intermediate Cycle Low/High (the same concepts one scale up,
            typically ~4 Daily Cycles per Intermediate Cycle)
"""

import numpy as np
import pandas as pd


# ── Shared date/position helpers ────────────────────────────────────────────
def _norm_dates(index) -> list:
    """Normalize a DatetimeIndex/list of Timestamps to 'YYYY-MM-DD' strings."""
    return [str(d)[:10] for d in index]


def _pos(date_key, dates_list):
    """Position of a date (Timestamp or 'YYYY-MM-DD' str) in a pre-normalized dates_list."""
    if date_key is None:
        return None
    try:
        return dates_list.index(str(date_key)[:10])
    except ValueError:
        return None


def _swing_window_for(cycle_len: int) -> int:
    return max(3, cycle_len // 8)


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


def detect_daily_cycles(close: pd.Series, high: pd.Series, low: pd.Series,
                         cycle_len_override: int = None, min_gap_override: int = None):
    """
    Detect all completed cycles at the given scale. Returns list of cycle dicts.
    Each cycle: dcl0, hch, hcl, dch, dcl1, translation, failed, cycle_num (None here —
    filled in later by assign_daily_cycle_numbers once Intermediate Cycles are known).

    cycle_len_override/min_gap_override let this same function be reused, unmodified,
    at a coarser scale to detect Intermediate Cycles (see detect_intermediate_cycles) —
    when both are None, behavior is identical to the original Daily-Cycle-only version.
    """
    if len(close) < 60:
        return None, {"status": "insufficient_data"}

    cycle_len = cycle_len_override if cycle_len_override is not None else auto_detect_cycle_length(close)
    window = _swing_window_for(cycle_len)

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
    min_gap = min_gap_override if min_gap_override is not None else (cycle_len // 2)
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

        cycles.append({
            "cycle_num": None,  # filled in by assign_daily_cycle_numbers()
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


# ── Trendline (real slanted line, not a flat price) ─────────────────────────
def _line_value_at(dates_list, x0_date, y0, x1_date, y1, target_date):
    """Linear extrapolation in bar-index space between two (date, price) anchors."""
    x0, x1, xt = _pos(x0_date, dates_list), _pos(x1_date, dates_list), _pos(target_date, dates_list)
    if x0 is None or x1 is None or xt is None or x1 == x0:
        return None
    slope = (y1 - y0) / (x1 - x0)
    return y0 + slope * (xt - x0)


def check_trendline_break(close: pd.Series, cycle: dict, dates_list: list = None) -> dict:
    """
    Draws the DCL0->HCL trendline (or ICL0->IC-HCL for an Intermediate Cycle dict —
    both share the same key schema) and checks whether the latest close is below its
    projected value. Replaces the old flat-hcl_price comparison.
    """
    dates_list = dates_list or _norm_dates(close.index)
    x0, y0 = cycle.get("dcl0_date"), cycle.get("dcl0_price")
    x1, y1 = cycle.get("hcl_date"), cycle.get("hcl_price")
    if not (x0 and y0 and x1 and y1):
        return {"applicable": False, "broken": False, "trendline_price": None, "slope_pct_per_bar": None}
    latest_date = dates_list[-1]
    line_price = _line_value_at(dates_list, x0, y0, x1, y1, latest_date)
    if line_price is None:
        return {"applicable": False, "broken": False, "trendline_price": None, "slope_pct_per_bar": None}
    current_close = float(close.iloc[-1])
    i0, i1 = _pos(x0, dates_list), _pos(x1, dates_list)
    slope_pct = None
    if i0 is not None and i1 is not None and i1 != i0 and y0:
        slope_pct = round(((y1 - y0) / y0) / abs(i1 - i0) * 100, 3)
    return {"applicable": True, "broken": current_close < line_price,
            "trendline_price": round(line_price, 4), "slope_pct_per_bar": slope_pct}


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


# ── Live (still-forming) cycle detection ────────────────────────────────────
def detect_live_cycle(close: pd.Series, high: pd.Series, low: pd.Series,
                       cycle_len: int, start_date: str, start_price: float,
                       dates_list: list = None) -> dict:
    """
    Detect HCH/HCL/running-high of the OPEN cycle starting at (start_date, start_price)
    — the most recent major low, not yet paired into a completed cycle. Scale-agnostic:
    pass the Daily cycle_len for the live Daily Cycle, or the Intermediate cycle_len
    with the last ICL as start_date/start_price for the live Intermediate Cycle. Returns
    the same key schema as a completed cycle dict (dcl0_date/hch_date/hcl_date/dch_date/
    translation) so check_trendline_break() works on either without special-casing.
    """
    dates_list = dates_list or _norm_dates(close.index)
    start_pos = _pos(start_date, dates_list)
    if start_pos is None:
        return {"live": True, "status": "no_position", "dcl0_date": start_date, "dcl0_price": start_price,
                "hch_date": None, "hch_price": None, "hcl_date": None, "hcl_price": None,
                "dch_date": None, "dch_price": None, "translation": "PENDING", "bars_elapsed": 0}

    window = _swing_window_for(cycle_len)
    seg_high, seg_low = high.iloc[start_pos:], low.iloc[start_pos:]
    bars_elapsed = len(seg_high) - 1
    projected_midpoint_pos = start_pos + cycle_len // 2
    projected_midpoint_date = dates_list[min(projected_midpoint_pos, len(dates_list) - 1)]

    dch_ts = seg_high.idxmax()
    dch_date, dch_price = str(dch_ts)[:10], round(float(seg_high.max()), 4)
    dch_pos = _pos(dch_date, dates_list)

    live_high_idx, live_low_idx = [], []
    if len(seg_high) >= window * 2 + 1:
        live_high_idx, _ = find_swing_points(seg_high, window=window)
        _, live_low_idx = find_swing_points(seg_low, window=window)

    highs_before_mid = [h for h in live_high_idx
                         if start_date < str(h)[:10] <= projected_midpoint_date]
    hch_date = str(highs_before_mid[0])[:10] if highs_before_mid else None
    hch_price = round(float(high.loc[highs_before_mid[0]]), 4) if highs_before_mid else None

    hcl_date = hcl_price = None
    if hch_date:
        lows_after_hch = [l for l in live_low_idx if str(l)[:10] > hch_date]
        if lows_after_hch:
            hcl_ts = min(lows_after_hch, key=lambda d: float(low.loc[d]))
            hcl_date, hcl_price = str(hcl_ts)[:10], round(float(low.loc[hcl_ts]), 4)

    translation = "PENDING"
    if dch_pos is not None:
        if dch_pos > projected_midpoint_pos and bars_elapsed >= cycle_len // 2:
            translation = "RIGHT"
        elif bars_elapsed >= cycle_len:
            translation = "LEFT"

    return {
        "live": True, "scale": "daily" if cycle_len < 80 else "intermediate",
        "dcl0_date": start_date, "dcl0_price": start_price,
        "hch_date": hch_date, "hch_price": hch_price,
        "hcl_date": hcl_date, "hcl_price": hcl_price,
        "dch_date": dch_date, "dch_price": dch_price,
        "translation": translation, "bars_elapsed": bars_elapsed,
        "projected_cycle_len": cycle_len, "projected_midpoint_date": projected_midpoint_date,
    }


def check_cycle_failing_now(low: pd.Series, close: pd.Series, dcl0_date: str, dcl0_price: float,
                             dates_list: list = None) -> dict:
    """
    True if price has already traded below the LIVE cycle's own starting low
    (dcl0_price) at any point since dcl0_date — i.e. the new cycle is failing in
    real time, before it has even completed. This is distinct from the retrospective
    `failed` flag on already-completed cycles.
    """
    dates_list = dates_list or _norm_dates(close.index)
    start_pos = _pos(dcl0_date, dates_list) if dcl0_date else None
    if start_pos is None or not dcl0_price:
        return {"failing": False, "lowest_since_dcl0": None, "pct_below_dcl0": None}
    # Exclude the DCL0 bar itself: dcl0_price is a *rounded* low from that same bar,
    # so re-including it and comparing against the unrounded series here produces
    # false positives from floating-point noise (e.g. 190.01 stored as
    # 190.00999999999999) — the cycle can't be "failing below its own start" on the
    # day it started; failing means a *later* bar traded lower.
    after_start = low.iloc[start_pos + 1:]
    if after_start.empty:
        return {"failing": False, "lowest_since_dcl0": None, "pct_below_dcl0": None}
    lowest = float(after_start.min())
    failing = lowest < dcl0_price
    pct = round((lowest - dcl0_price) / dcl0_price * 100, 2) if failing else 0.0
    return {"failing": failing, "lowest_since_dcl0": round(lowest, 4), "pct_below_dcl0": pct}


# ── Intermediate Cycle (weekly-scale) detection ─────────────────────────────
def detect_intermediate_cycles(close: pd.Series, high: pd.Series, low: pd.Series,
                                daily_cycle_len: int, daily_cycles: list):
    """
    Reuses detect_daily_cycles() at ~4x the Daily Cycle scale — DJRTrading: an
    Intermediate Cycle is "typically 4-5 Daily Cycles". Same pairing/translation/
    failed-cycle math applies unchanged at any scale, so this is a recursive call
    rather than a separate bespoke algorithm.
    """
    ic_cycle_len = daily_cycle_len * 4
    _, ic_raw = detect_daily_cycles(close, high, low,
                                     cycle_len_override=ic_cycle_len,
                                     min_gap_override=int(ic_cycle_len * 0.6))
    if isinstance(ic_raw, dict) or not ic_raw:
        return ic_cycle_len, []

    intermediate_cycles = []
    for ic in ic_raw:
        members = sorted([dc["dcl0_date"] for dc in daily_cycles
                           if ic["dcl0_date"] <= dc["dcl0_date"] < ic["dcl1_date"]])
        intermediate_cycles.append({
            "icl0_date": ic["dcl0_date"], "icl0_price": ic["dcl0_price"],
            "ic_hch_date": ic["hch_date"], "ic_hch_price": ic["hch_price"],
            "ic_hcl_date": ic["hcl_date"], "ic_hcl_price": ic["hcl_price"],
            "ich_date": ic["dch_date"], "ich_price": ic["dch_price"],
            "icl1_date": ic["dcl1_date"], "icl1_price": ic["dcl1_price"],
            "translation": ic["translation"], "failed": ic["failed"], "length": ic["length"],
            "daily_cycle_count": len(members),
            "member_daily_cycles": members,
        })
    return ic_cycle_len, intermediate_cycles


def _live_cycle_num(daily_cycles: list, intermediate_cycles: list) -> int:
    """How many-th Daily Cycle (within the current, still-forming Intermediate Cycle)
    the LIVE/open Daily Cycle is. Counts completed daily cycles that started on/after
    the current live IC's start (the last completed IC's end, or the very first daily
    cycle if no IC has completed yet), plus 1 for the live cycle itself."""
    if intermediate_cycles:
        ic_start = intermediate_cycles[-1]["icl1_date"]
    elif daily_cycles:
        ic_start = daily_cycles[0]["dcl0_date"]
    else:
        return 1
    count = sum(1 for d in daily_cycles if d["dcl0_date"] >= ic_start)
    return count + 1


def assign_daily_cycle_numbers(daily_cycles: list, intermediate_cycles: list) -> list:
    """Replaces the old `(i % 4) + 1` guess with a real DC-within-IC ordinal, by date
    containment against completed Intermediate Cycles. Daily cycles that trail the last
    completed IC (i.e. belong to the still-forming current IC) get numbered by counting
    since that IC's start, the same way the live/open cycle is numbered."""
    out = []
    for dc in daily_cycles:
        dc = dict(dc)
        match = next((ic for ic in intermediate_cycles
                      if ic["icl0_date"] <= dc["dcl0_date"] < ic["icl1_date"]), None)
        if match:
            members = sorted(match["member_daily_cycles"])
            dc["cycle_num"] = (members.index(dc["dcl0_date"]) + 1) if dc["dcl0_date"] in members else None
            dc["intermediate_cycle_start"] = match["icl0_date"]
        else:
            ic_start = intermediate_cycles[-1]["icl1_date"] if intermediate_cycles else daily_cycles[0]["dcl0_date"]
            if dc["dcl0_date"] >= ic_start:
                dc["cycle_num"] = sum(1 for d in daily_cycles if ic_start <= d["dcl0_date"] <= dc["dcl0_date"])
                dc["intermediate_cycle_start"] = ic_start
            else:
                dc["cycle_num"] = None
                dc["intermediate_cycle_start"] = None
        out.append(dc)
    return out


# ── Entry-zone classification (the 5 low-risk types + high-risk DC3/4) ──────
AT_LOW_BAR_THRESHOLD = 5          # bars since dcl0 to count as "right at the low"
AT_LOW_PRICE_TOLERANCE_PCT = 3.0  # price within this % of dcl0_price


def classify_entry_zone(current_price: float, live_daily: dict, live_intermediate: dict,
                         daily_trendline: dict, intermediate_trendline: dict,
                         confirmation_signal: bool, cycle_failing_now: dict) -> dict:
    """
    zone in {AT_ICL_DCL0, CONFIRMED_ABOVE_IC_RESISTANCE, DC1_HCL, DC1_RECOVERY, DC2_HCL,
             BEARISH_IC_DC1_ONLY, HIGH_RISK_DC3_4, BEARISH_IC_NO_ENTRY, MID_CYCLE_NO_SIGNAL,
             FAILING_NOW}
    Checked in the order the DJRTrading screenshots list the 5 low-risk entry types.
    """
    dc_num = live_daily.get("cycle_num")
    bars_since = live_daily.get("bars_elapsed", 0) or 0
    dcl0 = live_daily.get("dcl0_price")
    ic_translation = live_intermediate.get("translation", "PENDING") if live_intermediate else "PENDING"
    ic_bias = "BEARISH" if ic_translation == "LEFT" else "BULLISH_OR_SIDEWAYS"

    if cycle_failing_now.get("failing"):
        return {"zone": "FAILING_NOW", "risk": "HIGH", "eligible_for_entry": False,
                "reasons": ["Live cycle already trading below its own DCL0 — failing in real time"]}

    if ic_bias == "BEARISH":
        if dc_num == 1:
            return {"zone": "BEARISH_IC_DC1_ONLY", "risk": "MEDIUM", "eligible_for_entry": True,
                    "reasons": ["Bearish Intermediate Cycle — only DC1 longs, target 1st/2nd DC High"]}
        return {"zone": "BEARISH_IC_NO_ENTRY", "risk": "HIGH", "eligible_for_entry": False,
                "reasons": ["Bearish Intermediate Cycle past DC1 — no new longs"]}

    if dc_num == 1 and bars_since <= AT_LOW_BAR_THRESHOLD and dcl0 and \
       abs(current_price - dcl0) / dcl0 * 100 <= AT_LOW_PRICE_TOLERANCE_PCT:
        return {"zone": "AT_ICL_DCL0", "risk": "LOW", "eligible_for_entry": True,
                "reasons": ["Near-impossible-to-time low-risk entry: at/near ICL/DCL0"]}

    if confirmation_signal and not daily_trendline.get("broken") and not intermediate_trendline.get("broken"):
        return {"zone": "CONFIRMED_ABOVE_IC_RESISTANCE", "risk": "LOW", "eligible_for_entry": True,
                "reasons": ["90% confirmation: close above HCH resistance + 10D SMA, no trendline break"]}

    if dc_num == 1 and live_daily.get("hcl_price") and current_price >= live_daily["hcl_price"]:
        return {"zone": "DC1_HCL", "risk": "LOW", "eligible_for_entry": True,
                "reasons": ["At/above 1st Daily Cycle HCL, trendline drawable"]}

    if dc_num == 1 and dcl0 and current_price > dcl0:
        return {"zone": "DC1_RECOVERY", "risk": "LOW", "eligible_for_entry": True,
                "reasons": ["1st Daily Cycle of IC, price recovering off DCL"]}

    if dc_num == 2 and live_daily.get("hcl_price") and current_price >= live_daily["hcl_price"]:
        return {"zone": "DC2_HCL", "risk": "LOW", "eligible_for_entry": True,
                "reasons": ["At/above 2nd Daily Cycle HCL"]}

    if dc_num is not None and dc_num >= 3:
        return {"zone": "HIGH_RISK_DC3_4", "risk": "HIGH", "eligible_for_entry": False,
                "reasons": [f"Daily Cycle {dc_num} of Intermediate Cycle — high-risk zone, no new longs"]}

    return {"zone": "MID_CYCLE_NO_SIGNAL", "risk": "MEDIUM", "eligible_for_entry": False,
            "reasons": ["No qualifying low-risk entry pattern present"]}


# ── Predicted move (soft target + phase-based exit timing estimate) ─────────
def predicted_move(close: pd.Series, live_daily: dict, completed_daily_cycles: list,
                    daily_cycle_len: int) -> dict:
    empty = {"target_price": None, "target_basis": None, "prior_cycle_amplitude_pct": None,
             "bars_to_dc3_estimate": None, "est_date_dc3": None}
    if not completed_daily_cycles:
        return empty
    prior = completed_daily_cycles[-1]
    if not prior.get("dcl0_price"):
        return empty

    amp_pct = (prior["dch_price"] - prior["dcl0_price"]) / prior["dcl0_price"]
    dcl0 = live_daily.get("dcl0_price")
    target_price = round(dcl0 * (1 + amp_pct), 4) if dcl0 else None

    dc_num = live_daily.get("cycle_num")
    bars_since = live_daily.get("bars_elapsed", 0) or 0
    bars_to_dc3 = None
    if dc_num in (1, 2):
        bars_left_this_dc = max(0, daily_cycle_len - bars_since)
        bars_to_dc3 = bars_left_this_dc + (2 - dc_num) * daily_cycle_len
    elif dc_num is not None and dc_num >= 3:
        bars_to_dc3 = 0

    est_date_dc3 = None
    if bars_to_dc3 is not None:
        try:
            est_date_dc3 = str((close.index[-1] + pd.tseries.offsets.BDay(bars_to_dc3)).date())
        except Exception:
            est_date_dc3 = None

    return {"target_price": target_price,
            "target_basis": f"Prior Daily Cycle amplitude {amp_pct*100:.1f}% projected from new DCL0",
            "prior_cycle_amplitude_pct": round(amp_pct * 100, 2),
            "bars_to_dc3_estimate": bars_to_dc3, "est_date_dc3": est_date_dc3}


def _empty_cycle_extras() -> dict:
    """Neutral defaults for the new additive keys, spread into every early-return
    branch of analyse_cycles() so downstream code never needs branchy .get() chains."""
    neutral_trendline = {"applicable": False, "broken": False, "trendline_price": None, "slope_pct_per_bar": None}
    return {
        "cycle_len_intermediate": None,
        "intermediate_cycles": [],
        "live_daily_cycle": {},
        "live_intermediate_cycle": {},
        "daily_trendline": dict(neutral_trendline),
        "intermediate_trendline": dict(neutral_trendline),
        "cycle_failing_now": {"failing": False, "lowest_since_dcl0": None, "pct_below_dcl0": None},
        "entry_zone": {"zone": "NO_DATA", "risk": "MEDIUM", "eligible_for_entry": False, "reasons": []},
        "predicted_move": {"target_price": None, "target_basis": None, "prior_cycle_amplitude_pct": None,
                            "bars_to_dc3_estimate": None, "est_date_dc3": None},
    }


def analyse_cycles(df: pd.DataFrame, mas: dict) -> dict:
    """Main entry point. Returns cycle analysis dict."""
    if df is None or len(df) < 60:
        return {"status": "insufficient_data", "cycle_score": 50, "cycle_signal": "NEUTRAL",
                **_empty_cycle_extras()}

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
            **_empty_cycle_extras(),
        }

    if not cycles:
        return {"status": "no_cycles", "cycle_len": cycle_len, "cycle_score": 50, "cycle_signal": "NEUTRAL",
                **_empty_cycle_extras()}

    dates_list = _norm_dates(close.index)

    # Intermediate Cycles must be known before real Daily-Cycle-within-IC numbers can be assigned
    ic_cycle_len, intermediate_cycles = detect_intermediate_cycles(close, high, low, cycle_len, cycles)
    cycles = assign_daily_cycle_numbers(cycles, intermediate_cycles)

    current = cycles[-1]
    trendline_info = check_trendline_break(close, current, dates_list)
    trendline_break = trendline_info["broken"]
    confirmation = check_confirmation_signal(close, current, mas)

    live_daily = detect_live_cycle(close, high, low, cycle_len,
                                    current["dcl1_date"], current["dcl1_price"], dates_list)
    live_daily["cycle_num"] = _live_cycle_num(cycles, intermediate_cycles)

    live_intermediate = {}
    intermediate_trendline = {"applicable": False, "broken": False, "trendline_price": None, "slope_pct_per_bar": None}
    if intermediate_cycles:
        last_ic = intermediate_cycles[-1]
        live_intermediate = detect_live_cycle(close, high, low, ic_cycle_len,
                                               last_ic["icl1_date"], last_ic["icl1_price"], dates_list)
        intermediate_trendline = check_trendline_break(close, live_intermediate, dates_list)

    cycle_failing_now = check_cycle_failing_now(low, close, live_daily.get("dcl0_date"),
                                                 live_daily.get("dcl0_price"), dates_list)

    entry_zone = classify_entry_zone(float(close.iloc[-1]), live_daily, live_intermediate,
                                      trendline_info, intermediate_trendline, confirmation, cycle_failing_now)

    p_move = predicted_move(close, live_daily, cycles, cycle_len)

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

    if current.get("cycle_num") in (3, 4):
        score -= 8

    if cycle_failing_now["failing"]:
        score -= 25
    if entry_zone["risk"] == "HIGH":
        score -= 10
    if intermediate_trendline["broken"]:
        score -= 10

    score = max(0, min(100, score))

    if cycle_failing_now["failing"]:
        cycle_signal = "CYCLE_AVOID"
    elif score >= 65:
        cycle_signal = "CYCLE_BUY"
    elif score >= 50:
        cycle_signal = "CYCLE_HOLD"
    elif score >= 35:
        cycle_signal = "CYCLE_CAUTION"
    else:
        cycle_signal = "CYCLE_AVOID"

    # Build reason text
    cn = current.get("cycle_num")
    reasons = []
    reasons.append(f"{current['translation']}-translated cycle" + (f" (Daily Cycle #{cn} of IC)" if cn else ""))
    if current["failed"]:
        reasons.append("⚠️ FAILED CYCLE — lower low than start, bearish")
    if trendline_break:
        reasons.append("⚠️ Trendline BREAK — closed below HCL support")
    if confirmation:
        reasons.append("✅ 90% confirmation signal — above HCH resistance and 10D SMA")
    if high_risk_zone:
        reasons.append(f"⏰ {pct_through}% through cycle — late-cycle, higher risk zone")
    if cn in (3, 4):
        reasons.append("🔴 Intermediate Cycle 3-4: highest risk zone, reduce exposure")
    if cycle_failing_now["failing"]:
        reasons.append(f"⚠️ FAILING NOW — live cycle already {cycle_failing_now['pct_below_dcl0']}% below its own DCL0")
    if intermediate_trendline["broken"]:
        reasons.append("⚠️ Intermediate Cycle trendline BREAK")
    reasons.extend(entry_zone.get("reasons", []))

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
        # ── additive: Intermediate Cycle + live-cycle + entry-zone extensions ──
        "cycle_len_intermediate": ic_cycle_len,
        "intermediate_cycles": intermediate_cycles,
        "live_daily_cycle": live_daily,
        "live_intermediate_cycle": live_intermediate,
        "daily_trendline": trendline_info,
        "intermediate_trendline": intermediate_trendline,
        "cycle_failing_now": cycle_failing_now,
        "entry_zone": entry_zone,
        "predicted_move": p_move,
    }
