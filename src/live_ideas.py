"""
Live Day-Buy scan for Trade Ideas' "Live Scan" panel — server-side replacement
for the old browser-side scanMarketForIdeas().

That function fetched 15-min intraday bars straight from Yahoo Finance via a
public CORS proxy (Yahoo sends no CORS headers for third-party sites). It
depended entirely on corsproxy.io, which now requires a paid API key and
rejects every request. The only remaining free proxy option (Corsfix) also
isn't free for a live site beyond a trial. So this scan moves server-side,
same as live_prices.py: computed here every ~30 min via yfinance (no CORS
involved server-to-server), written to data/live_ideas.json, and the dashboard
just reads the file instead of live-fetching per click.

Same "Day Buy" definition as before: price above VWAP, RSI in the healthy
45-75 band, positive short-term momentum.
"""

import json
import os
import sys
from datetime import datetime
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from live_prices import load_watchlist

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASX_SCAN_FILE = os.path.join(BASE, "data", "asx_scan_results.json")
LIVE_IDEAS_FILE = os.path.join(BASE, "data", "live_ideas.json")

# Keep the scan universe modest since this now runs unattended every 30 min
# rather than once on a user click -- breadth accumulates over repeated runs.
DEEP_SCAN_TOP_N = 40


def get_scan_tickers() -> list:
    tickers = set()
    try:
        wl = load_watchlist()
        tickers.update(wl.get("asx", []))
        tickers.update(wl.get("nasdaq", []))
        tickers.update(wl.get("etf", []))
    except Exception as e:
        print(f"  Could not load watchlist: {e}")

    try:
        with open(ASX_SCAN_FILE) as f:
            scan = json.load(f)
        ranked = sorted(
            scan.get("results", []),
            key=lambda r: (r.get("reasoning") or {}).get("blended_score") or 0,
            reverse=True,
        )
        tickers.update(r["ticker"] for r in ranked[:DEEP_SCAN_TOP_N] if r.get("ticker"))
    except Exception as e:
        print(f"  Could not load asx_scan_results.json: {e}")

    return sorted(tickers)


def scan_ticker(ticker: str):
    """Returns a Day-Buy signal dict if the ticker qualifies right now, else None."""
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="15m")
        if df.empty or len(df) < 2:
            return None
        df = df.dropna(subset=["Close"])
        if df.empty:
            return None

        closes = df["Close"].tolist()
        highs = df["High"].tolist()
        lows = df["Low"].tolist()
        vols = df["Volume"].fillna(0).tolist()

        price = closes[-1]

        tpv = sum(((h + l + c) / 3) * v for h, l, c, v in zip(highs, lows, closes, vols))
        vol = sum(vols)
        vwap = tpv / vol if vol > 0 else 0
        vs = (price - vwap) / vwap * 100 if vwap > 0 else 0

        rsi = 50.0
        if len(closes) >= 15:
            gains = losses = 0.0
            for k in range(len(closes) - 14, len(closes)):
                d = closes[k] - closes[k - 1]
                if d > 0:
                    gains += d
                else:
                    losses -= d
            avg_gain, avg_loss = gains / 14, losses / 14
            rsi = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)

        mo = price - closes[-6] if len(closes) >= 6 else 0

        atr = 0.0
        if len(closes) >= 2:
            trs = []
            for k in range(1, len(closes)):
                trs.append(max(
                    highs[k] - lows[k],
                    abs(highs[k] - closes[k - 1]),
                    abs(lows[k] - closes[k - 1]),
                ))
            recent = trs[-14:]
            atr = sum(recent) / len(recent) if recent else 0

        is_day_buy = vs > 0 and 45 <= rsi <= 75 and mo > 0
        if not is_day_buy:
            return None

        buy_zone = vwap if (vwap > 0 and vwap < price) else price * 0.99
        sell_zone = price + atr * 2 if atr > 0 else price * 1.04

        return {
            "ticker": ticker,
            "price": round(price, 4),
            "vwap": round(vwap, 4),
            "vs": round(vs, 4),
            "rsi": round(rsi, 1),
            "mo": round(mo, 4),
            "buyZone": round(buy_zone, 4),
            "sellZone": round(sell_zone, 4),
        }
    except Exception as e:
        print(f"  {ticker}: {e}")
        return None


def run_live_ideas():
    tickers = get_scan_tickers()
    ideas = []
    for ticker in tickers:
        idea = scan_ticker(ticker)
        if idea:
            ideas.append(idea)

    out = {
        "generated_at": str(datetime.now())[:16],
        "scanned_count": len(tickers),
        "ideas": ideas,
    }
    with open(LIVE_IDEAS_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"live_ideas.json written: {len(ideas)} Day Buy signal(s) from {len(tickers)} tickers")


if __name__ == "__main__":
    run_live_ideas()
