"""Intraday Analysis — Trading Analyser 2.0
15-min bars, VWAP, gap analysis, intraday signals.
"""
import json, os, time
from datetime import datetime, date
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTRADAY_FILE = os.path.join(BASE, "data", "intraday_results.json")


def _vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


def analyse_intraday(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="15m", auto_adjust=True)
        if df is None or len(df) < 4:
            return {"ticker": ticker, "error": "No data"}
        df.index = pd.to_datetime(df.index)
        today = df.index.date[-1]
        today_df = df[df.index.date == today]
        prev_df  = df[df.index.date < today]
        if len(today_df) < 2 or len(prev_df) == 0:
            return {"ticker": ticker, "error": "Insufficient bars"}

        yesterday_close = float(prev_df["Close"].iloc[-1])
        today_open  = float(today_df["Open"].iloc[0])
        today_high  = float(today_df["High"].max())
        today_low   = float(today_df["Low"].min())
        today_close = float(today_df["Close"].iloc[-1])
        today_vol   = int(today_df["Volume"].sum())

        gap_pct  = round((today_open - yesterday_close) / yesterday_close * 100, 2)
        gap_type = "GAP UP" if gap_pct > 0.5 else "GAP DOWN" if gap_pct < -0.5 else "FLAT"

        vwap_series = _vwap(today_df)
        vwap = round(float(vwap_series.iloc[-1]), 3)
        vs_vwap = "ABOVE" if today_close > vwap else "BELOW"

        closes = today_df["Close"]
        if len(closes) >= 14:
            d = closes.diff()
            gain = d.clip(lower=0).rolling(14).mean()
            loss = (-d.clip(upper=0)).rolling(14).mean()
            rs = gain / loss
            rsi = round(float(100 - 100 / (1 + rs.iloc[-1])), 1)
        else:
            rsi = 50.0

        mom_pct = round((today_close - today_open) / today_open * 100, 2)

        # Score
        score = 50
        reasons = []
        if vs_vwap == "ABOVE":
            score += 10; reasons.append(f"Price above VWAP ${vwap:.3f}")
        else:
            score -= 10; reasons.append(f"Price below VWAP ${vwap:.3f}")
        if gap_type == "GAP UP":
            score += 10; reasons.append(f"Gap up {gap_pct:+.1f}% from prev close")
        elif gap_type == "GAP DOWN":
            score -= 10; reasons.append(f"Gap down {gap_pct:+.1f}% from prev close")
        if rsi < 35:
            score += 10; reasons.append(f"RSI {rsi} oversold intraday")
        elif rsi > 65:
            score -= 5;  reasons.append(f"RSI {rsi} overbought intraday")
        if mom_pct > 1:
            score += 10; reasons.append(f"Strong momentum +{mom_pct:.1f}% today")
        elif mom_pct < -1:
            score -= 10; reasons.append(f"Weak momentum {mom_pct:.1f}% today")

        signal = ("DAY BUY" if score >= 65 else
                  "WATCH"   if score >= 55 else
                  "AVOID"   if score <= 35 else "NEUTRAL")

        # Chart data
        vwap_vals = _vwap(today_df).tolist()
        candles, vwap_line = [], []
        for i, (idx, row) in enumerate(today_df.iterrows()):
            ts = int(idx.timestamp())
            candles.append({"time": ts, "open": round(float(row["Open"]),3),
                            "high": round(float(row["High"]),3),
                            "low":  round(float(row["Low"]),3),
                            "close":round(float(row["Close"]),3)})
            vwap_line.append({"time": ts, "value": round(vwap_vals[i], 3)})

        return {
            "ticker": ticker, "date": str(today),
            "open": round(today_open,3), "high": round(today_high,3),
            "low": round(today_low,3),  "close": round(today_close,3),
            "volume": today_vol, "yesterday_close": round(yesterday_close,3),
            "gap_pct": gap_pct, "gap_type": gap_type,
            "vwap": vwap, "vs_vwap": vs_vwap,
            "rsi_15m": rsi, "momentum_pct": mom_pct,
            "signal": signal, "score": score, "reasons": reasons,
            "candles": candles, "vwap_line": vwap_line, "error": None
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_intraday(tickers):
    print(f"\n--- Intraday Scan ({len(tickers)} stocks) ---")
    results = []
    for ticker in tickers:
        r = analyse_intraday(ticker)
        if r and not r.get("error"):
            results.append(r)
            print(f"  {ticker:10} | {r['signal']:8} | Gap: {r['gap_pct']:+.1f}% | {r['vs_vwap']} VWAP | RSI: {r['rsi_15m']}")
        else:
            print(f"  {ticker:10} | SKIP: {(r or {}).get('error','?')}")
        time.sleep(0.2)

    out = {"results": results, "scanned_at": datetime.now().isoformat(),
           "total_scanned": len(tickers), "results_count": len(results)}
    with open(INTRADAY_FILE, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Intraday done: {len(results)}/{len(tickers)}\n")
    return results
