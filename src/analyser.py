"""Trading Analyser 2.0 — Main Nightly Scanner"""
import json, os, sys, traceback
from datetime import datetime
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from technical import analyse_technicals
from cycle_analysis import analyse_cycles
from buy_sell_reasoning import generate_reasoning
from portfolio import evaluate_portfolio
from build_dashboard import build_dashboard
from send_report import send_email_report
from build_pdf import build_pdf_report
from correlation import run_correlation
from signal_history import record_signals, load_history, get_accuracy_summary
from chart_builder import build_chart_data
from quantitative import run_quantitative
from intraday import run_intraday

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE, "data", "watchlist.json")
REPORTS_DIR = os.path.join(BASE, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_watchlist():
    with open(WATCHLIST_FILE) as f:
        return json.load(f)

def fetch_stock(ticker):
    print(f"  Analysing {ticker}...")
    try:
        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(period="2y", auto_adjust=True)
        if df.empty or len(df) < 30:
            return {"ticker": ticker, "error": "No data"}
        try:
            info = yf_ticker.info
        except Exception:
            info = {}
        name = info.get("longName") or info.get("shortName") or ticker
        tech = analyse_technicals(df)
        mas = tech.get("moving_averages", {}) if tech else {}
        cycle = analyse_cycles(df, mas)
        reasoning = generate_reasoning(ticker, tech, cycle, info)
        try:
            corr = run_correlation(df)
        except Exception as ce:
            corr = {"status": "error", "error": str(ce)}
        try:
            chart_data = build_chart_data(df, ticker)
        except Exception:
            chart_data = {}
        return {
            "ticker": ticker, "name": name,
            "sector": info.get("sector", "Unknown"),
            "market_cap": info.get("marketCap"),
            "tech": tech, "cycle": cycle, "reasoning": reasoning,
            "correlation": corr, "chart_data": chart_data, "error": None,
        }
    except Exception as e:
        traceback.print_exc()
        return {"ticker": ticker, "error": str(e)}

def filter_by_price(results, max_price):
    return [r for r in results if r.get("tech", {}).get("price", 999) <= max_price]

def run_nightly():
    print(f"\n{'='*60}")
    print(f"Trading Analyser 2.0 — Nightly Scan")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")
    watchlist = load_watchlist()
    settings = watchlist.get("settings", {})
    max_price_asx = settings.get("max_price_asx", 30.0)
    max_price_nasdaq = settings.get("max_price_nasdaq", 30.0)
    all_tickers = watchlist.get("asx", []) + watchlist.get("nasdaq", []) + watchlist.get("etf", [])
    results, errors = [], []
    print(f"Scanning {len(all_tickers)} stocks...\n")
    for ticker in all_tickers:
        result = fetch_stock(ticker)
        if result.get("error"):
            errors.append(result)
            print(f"  SKIP {ticker}: {result['error']}")
        else:
            results.append(result)
            r = result["reasoning"]
            print(f"  OK   {ticker:8} | {r.get('recommendation','?'):12} | Score: {r.get('blended_score','?'):5} | ${result['tech'].get('price',0):.3f}")
    asx_filtered = filter_by_price([r for r in results if r["ticker"].endswith(".AX")], max_price_asx)
    nasdaq_filtered = filter_by_price([r for r in results if not r["ticker"].endswith(".AX")], max_price_nasdaq)
    all_results = sorted(asx_filtered + nasdaq_filtered, key=lambda r: r["reasoning"].get("blended_score", 0), reverse=True)
    print("\nEvaluating portfolio...")
    portfolio_summary = evaluate_portfolio(all_results)
    print("Recording signal history...")
    history = record_signals(all_results)
    accuracy = get_accuracy_summary(history)
    print(f"Signal accuracy: {accuracy.get('overall_accuracy', 0):.1f}% over {accuracy.get('total_signals', 0)} resolved signals")
    top_buys = [r for r in all_results if r["reasoning"].get("recommendation", "").startswith(("STRONG", "BUY"))][:5]
    print(f"Top picks: {[r['ticker'] for r in top_buys]}")
    today_str = datetime.now().strftime("%Y-%m-%d")
    dashboard_file = os.path.join(BASE, "index.html")
    pdf_file = os.path.join(REPORTS_DIR, f"report_{today_str}.pdf")
    print("\nBuilding dashboard...")
    build_dashboard(all_results, portfolio_summary, dashboard_file, signal_history=history, accuracy=accuracy)
    print("Building PDF report...")
    build_pdf_report(all_results, portfolio_summary, pdf_file, signal_history=history, accuracy=accuracy)
    print("Sending email...")
    send_email_report(all_results, portfolio_summary, pdf_file)
    print(f"\n{'='*60}")
    print(f"Complete. {len(all_results)} stocks, {len(errors)} errors.")
    print(f"{'='*60}\n")
    return all_results, portfolio_summary

if __name__ == "__main__":
    run_nightly()
