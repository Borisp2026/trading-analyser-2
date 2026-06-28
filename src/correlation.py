"""
US Market Correlation Module — Trading Analyser 2.0
Compares each stock against S&P 500 (^GSPC), NASDAQ (^IXIC), Dow (^DJI).
Returns correlation coefficients, beta, and trend alignment.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

BENCHMARKS = {
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow": "^DJI",
}

_cache = {}

def get_benchmark_data(period="3mo"):
    """Download benchmark returns (cached per session)."""
    key = f"bench_{period}"
    if key in _cache:
        return _cache[key]
    bench = {}
    for name, sym in BENCHMARKS.items():
        try:
            df = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if not df.empty:
                bench[name] = df["Close"].pct_change().dropna()
        except Exception:
            pass
    _cache[key] = bench
    return bench

def get_benchmark_trend():
    """Get short-term (5D) and medium-term (20D) trend for each benchmark."""
    trends = {}
    for name, sym in BENCHMARKS.items():
        try:
            df = yf.Ticker(sym).history(period="3mo", auto_adjust=True)
            if df.empty:
                continue
            close = df["Close"]
            price = float(close.iloc[-1])
            d5 = round(((price - float(close.iloc[-6])) / float(close.iloc[-6])) * 100, 2)
            d20 = round(((price - float(close.iloc[-21])) / float(close.iloc[-21])) * 100, 2)
            trend = "BULLISH" if d5 > 0 and d20 > 0 else "BEARISH" if d5 < 0 and d20 < 0 else "MIXED"
            trends[name] = {
                "price": round(price, 2),
                "5d_pct": d5,
                "20d_pct": d20,
                "trend": trend,
            }
        except Exception:
            pass
    return trends

def analyse_correlation(ticker_returns: pd.Series, period="3mo") -> dict:
    """
    Calculate correlation and beta vs each benchmark.
    ticker_returns: daily % returns for the stock.
    """
    bench = get_benchmark_data(period)
    results = {}
    for name, bench_returns in bench.items():
        try:
            combined = pd.concat([ticker_returns, bench_returns], axis=1).dropna()
            combined.columns = ["stock", "bench"]
            if len(combined) < 20:
                continue
            corr = round(float(combined["stock"].corr(combined["bench"])), 3)
            cov = float(combined.cov().iloc[0, 1])
            bench_var = float(combined["bench"].var())
            beta = round(cov / bench_var, 3) if bench_var != 0 else None
            results[name] = {"correlation": corr, "beta": beta}
        except Exception:
            pass

    if not results:
        return {"status": "no_data"}

    # Overall assessment
    avg_corr = round(sum(r["correlation"] for r in results.values()) / len(results), 3)
    trends = get_benchmark_trend()

    # Predict stock direction based on correlation + US trend
    us_trend = "BULLISH" if sum(1 for t in trends.values() if t.get("trend") == "BULLISH") >= 2 else \
               "BEARISH" if sum(1 for t in trends.values() if t.get("trend") == "BEARISH") >= 2 else "MIXED"

    if avg_corr > 0.5 and us_trend == "BULLISH":
        outlook = "POSITIVE — high US correlation + US trending up"
    elif avg_corr > 0.5 and us_trend == "BEARISH":
        outlook = "CAUTION — high US correlation + US trending down"
    elif avg_corr < 0:
        outlook = "INVERSE — moves opposite to US market"
    else:
        outlook = "LOW CORRELATION — moves independently of US"

    return {
        "status": "ok",
        "benchmarks": results,
        "avg_correlation": avg_corr,
        "us_trend": us_trend,
        "us_benchmark_trends": trends,
        "outlook": outlook,
    }

def run_correlation(df: pd.DataFrame) -> dict:
    """Entry point: pass stock OHLCV dataframe, get correlation analysis."""
    if df is None or len(df) < 30:
        return {"status": "insufficient_data"}
    returns = df["Close"].pct_change().dropna()
    return analyse_correlation(returns)
