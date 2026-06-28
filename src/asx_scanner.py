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

def scan_ticker(ticker, max_price=30.0):
    try:
        df = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        tech = analyse_technicals(df)
        if not tech or tech.get("price", 0) == 0:
            return None
        # Price filter here — skip expensive stocks
        if tech.get("price", 999) > max_price:
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

def run_deep_scan(max_price=30.0):
    tickers = load_universe()
    settings = load_settings()
    max_price = settings.get("max_price_asx", max_price)
    print(f"ASX Deep Scan: {len(tickers)} tickers, max price ${max_price:.2f}")
    results = []
    skipped = 0
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker}...", end=" ", flush=True)
        result = scan_ticker(ticker, max_price)
        if result:
            score = result["reasoning"].get("blended_score", 0)
            results.append(result)
            print(f"Score: {score:.0f}")
        else:
            skipped += 1
            print("skip")
        time.sleep(0.3)
    results.sort(key=lambda r: r["reasoning"].get("blended_score", 0), reverse=True)
    output = {"scanned_at": datetime.now().isoformat(), "total_scanned": len(tickers)-skipped,
              "max_price": max_price, "results_count": len(results), "results": results}
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, default=str, indent=2)
    print(f"\nDone: {len(results)} stocks scored, {skipped} skipped.")
    return results

if __name__ == "__main__":
    run_deep_scan()
