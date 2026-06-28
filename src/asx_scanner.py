"""
ASX Deep Scanner — Trading Analyser 2.0
Scans all tickers in data/asx_universe.json where price <= max_price.
Runs as a separate weekly GitHub Actions job (not nightly — too slow for that).
Results stored in data/asx_scan_results.json for dashboard display.
"""
import json, os, sys, time
from datetime import datetime
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from technical import analyse_technicals
from cycle_analysis import analyse_cycles
from buy_sell_reasoning import generate_reasoning

UNIVERSE_FILE = os.path.join(BASE, "data", "asx_universe.json")
WATCHLIST_FILE = os.path.join(BASE, "data", "watchlist.json")
RESULTS_FILE = os.path.join(BASE, "data", "asx_scan_results.json")


def load_universe() -> list:
    with open(UNIVERSE_FILE) as f:
        return json.load(f).get("tickers", [])


def load_settings() -> dict:
    with open(WATCHLIST_FILE) as f:
        return json.load(f).get("settings", {})


def batch_get_prices(tickers: list) -> dict:
    """Fast batch download of current prices to pre-filter by max_price."""
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


def scan_ticker(ticker: str) -> dict | None:
    """Full technical + cycle + reasoning scan for one ticker."""
    try:
        df = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
        if df is None or len(df) < 30:
            return None

        tech = analyse_technicals(df, ticker)
        if not tech or tech.get("price", 0) == 0:
            return None

        try:
            cycle = analyse_cycles(df, ticker)
        except Exception:
            cycle = {"status": "error"}

        reasoning = generate_reasoning(tech, cycle, ticker)

        return {
            "ticker": ticker,
            "name": yf.Ticker(ticker).info.get("longName", ticker)[:40],
            "tech": tech,
            "cycle": cycle,
            "reasoning": reasoning,
            "scanned_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"Error scanning {ticker}: {e}")
        return None


def run_deep_scan(max_price: float = 30.0, min_score: float = 0) -> list:
    """
    Main entry point — scans all tickers in universe under max_price.
    Returns sorted list of results (best score first).
    """
    tickers = load_universe()
    settings = load_settings()
    max_price = settings.get("max_price_asx", max_price)

    print(f"ASX Deep Scan: {len(tickers)} tickers, max price ${max_price:.2f}")

    # Step 1: Fast price filter
    print("Step 1: Batch price download...")
    prices = batch_get_prices(tickers)
    eligible = [t for t, p in prices.items() if p is not None and p <= max_price]
    print(f"Step 1 done: {len(eligible)} tickers under ${max_price:.2f}")

    # Step 2: Full scan
    results = []
    for i, ticker in enumerate(eligible):
        print(f"Scanning {ticker} ({i+1}/{len(eligible)})...", end=" ")
        result = scan_ticker(ticker)
        if result:
            score = result["reasoning"].get("blended_score", 0)
            if score >= min_score:
                results.append(result)
                print(f"Score: {score:.0f}")
            else:
                print(f"Score: {score:.0f} (filtered)")
        else:
            print("skip")
        time.sleep(0.1)

    # Sort by blended score descending
    results.sort(key=lambda r: r["reasoning"].get("blended_score", 0), reverse=True)

    # Save results
    output = {
        "scanned_at": datetime.now().isoformat(),
        "total_scanned": len(eligible),
        "max_price": max_price,
        "results_count": len(results),
        "results": results,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, default=str, indent=2)

    print(f"\nDeep scan complete: {len(results)} stocks scored.")
    return results


if __name__ == "__main__":
    run_deep_scan()
