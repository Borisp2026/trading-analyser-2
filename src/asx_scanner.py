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
    for i in range(0, len(tickers), 50):
        chunk = tickers[i:i+50]
        try:
            data = yf.download(chunk, period="2d", auto_adjust=True,
                               group_by="ticker", progress=False, threads=True)
            for t in chunk:
                try:
                    price = float(data["Close"].iloc[-1]) if len(chunk)==1 else float(data[t]["Close"].iloc[-1])
                    prices[t] = price
                except Exception:
                    prices[t] = None
        except Exception as e:
            print(f"Batch error: {e}")
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
        name = (info.get("longName") or info.get("shortName") or ticker)[:40]
        reasoning = generate_reasoning(ticker, tech, cycle, info)
        return {"ticker": ticker, "name": name, "tech": tech, "cycle": cycle,
                "reasoning": reasoning, "scanned_at": datetime.now().isoformat()}
    except Exception as e:
        print(f"Error {ticker}: {e}")
        return None

def run_deep_scan(max_price=30.0, min_score=0):
    tickers = load_universe()
    settings = load_settings()
    max_price = settings.get("max_price_asx", max_price)
    print(f"ASX Deep Scan: {len(tickers)} tickers, max ${max_price:.2f}")
    prices = batch_get_prices(tickers)
    eligible = [t for t, p in prices.items() if p is not None and p <= max_price]
    print(f"{len(eligible)} tickers under ${max_price:.2f}")
    results = []
    for i, ticker in enumerate(eligible):
        print(f"Scanning {ticker} ({i+1}/{len(eligible)})...", end=" ", flush=True)
        result = scan_ticker(ticker)
        if result:
            score = result["reasoning"].get("blended_score", 0)
            results.append(result)
            print(f"Score: {score:.0f}")
        else:
            print("skip")
        time.sleep(0.1)
    results.sort(key=lambda r: r["reasoning"].get("blended_score", 0), reverse=True)
    output = {"scanned_at": datetime.now().isoformat(), "total_scanned": len(eligible),
              "max_price": max_price, "results_count": len(results), "results": results}
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, default=str, indent=2)
    print(f"\nDone: {len(results)} stocks scored.")
    return results

if __name__ == "__main__":
    run_deep_scan()
