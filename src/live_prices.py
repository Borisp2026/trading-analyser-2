"""
Live Prices snapshot for Trading Analyser 2.0
Runs every 30 minutes via GitHub Actions (piggybacking on intraday.yml, during
ASX + NASDAQ hours). Writes data/live_prices.json: a plain same-origin file the
dashboard's browser JS reads directly with a normal fetch().

Why this exists: the dashboard's "current price" features (Portfolio refresh,
Trade Ideas scan, Current-price columns, manual ticker lookup) used to fetch
Yahoo Finance straight from the browser via a public CORS proxy (corsproxy.io),
since Yahoo's API sends no CORS headers for third-party sites. That proxy
started requiring a paid API key and now rejects every request with HTTP 401 --
a systemic outage, not a bug in our code. Fetching here instead, server-to-
server via yfinance, has no CORS restriction at all (CORS is a browser-only
concept), so this file becomes a proxy-free fallback the dashboard can always
read, refreshed on the same 30-min cadence as the rest of the intraday data.
"""

import json
import os
import sys
from datetime import datetime
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from portfolio import load_portfolio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE, "data", "watchlist.json")
LIVE_PRICES_FILE = os.path.join(BASE, "data", "live_prices.json")


def load_watchlist() -> dict:
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


def get_tracked_tickers() -> list:
    """Every ticker the dashboard might ask a live price for: the full
    watchlist, real holdings, and any open paper trade (across all
    strategies) -- so a position like ASIA.AX that isn't on the watchlist
    still gets covered."""
    tickers = set()

    try:
        wl = load_watchlist()
        tickers.update(wl.get("asx", []))
        tickers.update(wl.get("nasdaq", []))
        tickers.update(wl.get("etf", []))
    except Exception as e:
        print(f"  Could not load watchlist: {e}")

    try:
        portfolio = load_portfolio()
        for h in portfolio.get("holdings", []):
            tickers.add(h["ticker"])
        for t in portfolio.get("paper_trades", []):
            if t.get("status") == "open":
                tickers.add(t["ticker"])
    except Exception as e:
        print(f"  Could not load portfolio: {e}")

    return sorted(tickers)


def fetch_price(ticker: str):
    """Same NaN-guard as portfolio.py's get_current_price(): a same-day row
    can arrive with NaN Close before Yahoo finalizes it, so drop NaNs before
    taking the last value rather than trusting .iloc[-1] blindly."""
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if not data.empty:
            valid = data["Close"].dropna()
            if len(valid):
                return float(valid.iloc[-1])
    except Exception as e:
        print(f"  {ticker}: {e}")
    return None


def run_live_prices():
    tickers = get_tracked_tickers()
    prices = {}
    for ticker in tickers:
        price = fetch_price(ticker)
        if price is not None:
            prices[ticker] = round(price, 4)

    out = {
        "generated_at": str(datetime.now())[:16],
        "prices": prices,
    }
    with open(LIVE_PRICES_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"live_prices.json written: {len(prices)}/{len(tickers)} tickers")


if __name__ == "__main__":
    run_live_prices()
