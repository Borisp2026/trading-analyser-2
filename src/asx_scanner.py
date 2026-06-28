"""ASX Deep Scanner — Trading Analyser 2.0"""
import json, os, sys, time
from datetime import datetime
import yfinance as yf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from technical import analyse_technicals
from cycle_analysis import analyse_cycles
from buy_sell_reasoning import generate_reasoning

UNIVERSE_FILE = os.path.join(BASE, "data", "asx_universe.json")
WATCHLIST_FILE = os.path.join(BASE, "data", "watchlist.json")
RESULTS_FILE = os.path.join(BASE, "data", "asx_scan_results.json")

def load_universe():
    with open(UNIVERSE_FILE) as f:
        return json.load(f).get("tickers", [])

def load_settings():
    with open(WATCHLIST_FILE) as f:
        return json.load(f).get("settings", {})

def batch_get_prices(tickers):
    prices = {}
    chunk_size = 50
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        try:
            data = yf.download(chunk, period="2d", auto_adjust=True,
                               group_by="ticker", progress=False, threads=True)
            for t in chunk:
                try:
                    if len(chunk) == 1:
                        price = float(data["Close"].iloc[-1])
                    else:
                        price = float(data[t]["Close"].iloc[-1])
                    prices[t] = price
                except Exception:
                    prices[t] = None
        except Exception as e:
            print(f"Batch price error: {e}")
        time.sleep(0.3)
    return prices

def scan_ticker(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        tech = analyse_technicals(df)
        if not tech or tech.get("price", 0) == 0:
            return None
        mas = tech.get("moving_averages", {})
        try:
            cycle = analyse_cycles(df, mas)
        except Exception:
            cycle = {"status": "error"}
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            info = {}
        name = info.get("longName") or info.get("shortName") or ticker


git add src/asx_scanner.py
git commit -m "fix: asx_scanner function argument order"
git push






