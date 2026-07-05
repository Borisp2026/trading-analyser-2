"""Macro Deployment Gate — Trading Analyser 2.0
6 macro signals, each scored 0-100, blended into a composite deployment score.
Answers: "Should I be deploying capital right now, and how aggressively?"
"""
import json, os
from datetime import datetime
import yfinance as yf
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO_FILE = os.path.join(BASE, "data", "macro_gate.json")

SECTOR_ETFS = ['XLK','XLF','XLV','XLE','XLI','XLY','XLP','XLB','XLU','XLRE','XLC']


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# ── Signal 1: VIX Level ───────────────────────────────────────────────────────
def signal_vix_level(vix_hist):
    current = float(vix_hist['Close'].iloc[-1])
    # Percentile rank: how often was VIX *above* today's level (low VIX = calm = high score)
    pct_above = (vix_hist['Close'] > current).sum() / len(vix_hist) * 100
    score = pct_above  # if VIX lower than 80% of history → score = 80
    if current < 15: score = _clamp(score + 5)
    if current > 30: score = _clamp(score - 10)
    label = "CALM" if current < 18 else "ELEVATED" if current < 28 else "FEAR"
    return {"name": "VIX Level", "value": round(current, 2),
            "value_label": f"VIX {current:.1f}",
            "score": round(_clamp(score), 1),
            "detail": f"VIX {current:.1f} — lower than {pct_above:.0f}% of the past year",
            "interpretation": label}


# ── Signal 2: VIX Term Structure ──────────────────────────────────────────────
def signal_vix_term_structure(vix_hist, vix3m_hist):
    vix_now = float(vix_hist['Close'].iloc[-1])
    try:
        vix3m_now = float(vix3m_hist['Close'].iloc[-1])
        ratio = vix_now / vix3m_now
    except Exception:
        ratio = 1.0
        vix3m_now = vix_now
    # 0.85 → 100, 1.15 → 0
    score = _clamp((1.15 - ratio) / 0.30 * 100)
    structure = "CONTANGO" if ratio < 1.0 else "BACKWARDATION"
    label = "CALM" if ratio < 0.95 else "NEUTRAL" if ratio < 1.05 else "STRESS"
    return {"name": "VIX Term Structure", "value": round(ratio, 3),
            "value_label": f"Ratio {ratio:.3f}",
            "score": round(score, 1),
            "detail": f"VIX/VIX3M = {ratio:.3f} ({structure}) — below 1.0 = calm",
            "interpretation": label}


# ── Signal 3: Market Breadth ──────────────────────────────────────────────────
def signal_market_breadth():
    above, total = 0, 0
    for etf in SECTOR_ETFS:
        try:
            df = yf.Ticker(etf).history(period="1y", auto_adjust=True)
            if len(df) >= 200:
                price = float(df['Close'].iloc[-1])
                ma200 = float(df['Close'].rolling(200).mean().iloc[-1])
                if not np.isnan(ma200):
                    total += 1
                    if price > ma200: above += 1
        except Exception:
            pass
    pct = (above / total * 100) if total > 0 else 50.0
    # 80% → 100, 30% → 0
    score = _clamp((pct - 30) / 50 * 100)
    label = "BROAD" if pct >= 65 else "NARROW" if pct >= 45 else "WEAK"
    return {"name": "Market Breadth", "value": round(pct, 1),
            "value_label": f"{above}/{total} sectors above 200MA",
            "score": round(score, 1),
            "detail": f"{above} of {total} SPDR sector ETFs above their 200-day SMA ({pct:.0f}%)",
            "interpretation": label}


# ── Signal 4: Credit Spreads ──────────────────────────────────────────────────
def signal_credit_spreads():
    try:
        hyg = yf.Ticker("HYG").history(period="1y", auto_adjust=True)['Close']
        tlt = yf.Ticker("TLT").history(period="1y", auto_adjust=True)['Close']
        df = pd.DataFrame({'hyg': hyg, 'tlt': tlt}).dropna()
        ratio = df['hyg'] / df['tlt']
        z = float((ratio.iloc[-1] - ratio.mean()) / ratio.std())
        # Negative z = high HYG/TLT = tight spreads = bullish
        # z=-2 → 100, z=+2 → 0
        score = _clamp((2 - z) / 4 * 100)
        label = "TIGHT" if z < -0.5 else "NORMAL" if z < 0.5 else "WIDE"
        return {"name": "Credit Spreads", "value": round(z, 2),
                "value_label": f"Z-score {z:+.2f}",
                "score": round(score, 1),
                "detail": f"HYG/TLT ratio z-score {z:+.2f} vs 1-year avg (negative = tight = bullish)",
                "interpretation": label}
    except Exception as e:
        return {"name": "Credit Spreads", "value": 0, "value_label": "N/A",
                "score": 50.0, "detail": f"Error: {e}", "interpretation": "UNKNOWN"}


# ── Signal 5: Put/Call Sentiment ──────────────────────────────────────────────
def signal_put_call(vix_hist):
    try:
        if len(vix_hist) >= 21:
            roc = (float(vix_hist['Close'].iloc[-1]) - float(vix_hist['Close'].iloc[-21])) \
                  / float(vix_hist['Close'].iloc[-21]) * 100
        else:
            roc = 0.0
        # ROC -30% → 100, ROC +50% → 0
        score = _clamp((50 - roc) / 80 * 100)
        label = "GREEDY" if roc < -10 else "NEUTRAL" if roc < 15 else "FEARFUL"
        return {"name": "Put/Call Sentiment", "value": round(roc, 2),
                "value_label": f"VIX ROC {roc:+.1f}%",
                "score": round(score, 1),
                "detail": f"VIX 20-day rate of change {roc:+.1f}% (rapidly rising = fear = low score)",
                "interpretation": label}
    except Exception as e:
        return {"name": "Put/Call Sentiment", "value": 0, "value_label": "N/A",
                "score": 50.0, "detail": f"Error: {e}", "interpretation": "UNKNOWN"}


# ── Signal 6: SPX Trend ───────────────────────────────────────────────────────
def signal_spx_trend():
    try:
        spx = yf.Ticker("^GSPC").history(period="1y", auto_adjust=True)['Close']
        price = float(spx.iloc[-1])
        ma50  = float(spx.rolling(50).mean().iloc[-1])
        ma200 = float(spx.rolling(200).mean().iloc[-1])
        score = 50
        score += 25 if price > ma200 else -25
        score += 15 if price > ma50  else -15
        score += 10 if ma50  > ma200 else -10   # golden vs death cross
        pct_from_200 = (price - ma200) / ma200 * 100
        trend = ("UPTREND"   if price > ma50 > ma200 else
                 "DOWNTREND" if price < ma50 < ma200 else "MIXED")
        return {"name": "SPX Trend", "value": round(pct_from_200, 2),
                "value_label": f"SPX {pct_from_200:+.1f}% vs 200MA",
                "score": round(_clamp(score), 1),
                "detail": f"S&P 500 ${price:,.0f} — MA50 {'above' if ma50>ma200 else 'below'} MA200 ({'Golden' if ma50>ma200 else 'Death'} cross)",
                "interpretation": trend}
    except Exception as e:
        return {"name": "SPX Trend", "value": 0, "value_label": "N/A",
                "score": 50.0, "detail": f"Error: {e}", "interpretation": "UNKNOWN"}


# ── Main runner ───────────────────────────────────────────────────────────────
def run_macro_gate():
    print("\n--- Macro Deployment Gate ---")
    vix_hist  = yf.Ticker("^VIX").history(period="1y", auto_adjust=True)
    try:
        vix3m_hist = yf.Ticker("^VIX3M").history(period="5d", auto_adjust=True)
        if len(vix3m_hist) == 0: raise ValueError("empty")
    except Exception:
        vix3m_hist = vix_hist

    signals = [
        signal_vix_level(vix_hist),
        signal_vix_term_structure(vix_hist, vix3m_hist),
        signal_market_breadth(),
        signal_credit_spreads(),
        signal_put_call(vix_hist),
        signal_spx_trend(),
    ]

    composite = round(sum(s["score"] for s in signals) / len(signals), 1)

    if composite >= 70:
        zone, zone_color = "DEPLOY",    "#44bb44"
        zone_desc = "Conditions favourable — deploy capital aggressively"
    elif composite >= 50:
        zone, zone_color = "SELECTIVE", "#ff9900"
        zone_desc = "Mixed conditions — selective deployment, reduce size"
    elif composite >= 30:
        zone, zone_color = "CAUTION",   "#ff6600"
        zone_desc = "Elevated risk — minimal deployment, hold cash"
    else:
        zone, zone_color = "RISK OFF",  "#cc0000"
        zone_desc = "Defensive — avoid new longs, preserve capital"

    for s in signals:
        print(f"  {s['name']:26} | {s['score']:5.1f}/100 | {s['value_label']:25} | {s['interpretation']}")
    print(f"  {'COMPOSITE':26} | {composite:5.1f}/100 | Zone: {zone}")

    result = {"signals": signals, "composite": composite,
              "zone": zone, "zone_desc": zone_desc, "zone_color": zone_color,
              "scanned_at": datetime.now().isoformat()}
    with open(MACRO_FILE, "w") as f:
        json.dump(result, f, indent=2)
    return result
