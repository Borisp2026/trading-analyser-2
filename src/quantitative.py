"""Quantitative Analysis — Trading Analyser 2.0
Earnings, 12-1 Momentum, RSI Strategy, MA Crossover,
Walk Forward Validation, Monte Carlo, Sensitivity Analysis.
"""
import json, os, time
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUANT_FILE = os.path.join(BASE, "data", "quant_results.json")


def _rsi(series, period=14):
    d = series.diff()
    g = d.clip(lower=0).rolling(period).mean()
    l = (-d.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + g / l)


# ── Earnings ──────────────────────────────────────────────────────────────────
def get_earnings(yft, ticker):
    try:
        cal = yft.calendar
        next_date = "Unknown"
        if cal is not None:
            if isinstance(cal, dict):
                nd = cal.get("Earnings Date")
                next_date = str(nd[0]) if hasattr(nd, '__iter__') and not isinstance(nd, str) else str(nd) if nd else "Unknown"
            elif hasattr(cal, "index") and "Earnings Date" in cal.index:
                next_date = str(cal.loc["Earnings Date"].iloc[0])
        hist = []
        try:
            qe = yft.quarterly_earnings
            if qe is not None and len(qe) > 0:
                for dt, row in list(qe.iterrows())[:4]:
                    hist.append({
                        "date": str(dt),
                        "actual": float(row.get("Actual", 0) or 0),
                        "estimate": float(row.get("Estimate", 0) or 0),
                    })
        except Exception:
            pass
        return {"ticker": ticker, "next_earnings": next_date, "history": hist}
    except Exception as e:
        return {"ticker": ticker, "next_earnings": "N/A", "history": [], "error": str(e)}


# ── 12-1 Month Momentum ───────────────────────────────────────────────────────
def get_momentum(ticker, df):
    try:
        if len(df) < 252:
            return {"ticker": ticker, "error": "Need 1y+ of data"}
        now  = float(df["Close"].iloc[-1])
        m1   = float(df["Close"].iloc[-21])
        m12  = float(df["Close"].iloc[-252])
        r12  = (now / m12 - 1) * 100
        r1   = (now / m1  - 1) * 100
        mom  = r12 - r1
        return {"ticker": ticker, "ret_12m": round(r12,2), "ret_1m": round(r1,2), "momentum": round(mom,2)}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── RSI Crossover Strategy ────────────────────────────────────────────────────
def get_rsi_strategy(ticker, df):
    try:
        rsi = _rsi(df["Close"])
        signals, prev = [], None
        for i in range(len(df)):
            curr = rsi.iloc[i]
            if pd.isna(curr) or prev is None: prev = curr; continue
            if prev < 30 <= curr:
                signals.append({"date": str(df.index[i].date()), "type": "BUY",  "price": round(float(df["Close"].iloc[i]),3)})
            elif prev < 70 <= curr:
                signals.append({"date": str(df.index[i].date()), "type": "SELL", "price": round(float(df["Close"].iloc[i]),3)})
            prev = curr
        wins = total = 0
        for j, s in enumerate(signals):
            if s["type"] != "BUY": continue
            idx = df.index.get_indexer([pd.Timestamp(s["date"])], method="nearest")[0]
            if idx + 20 < len(df):
                ret = (float(df["Close"].iloc[idx+20]) - s["price"]) / s["price"] * 100
                total += 1
                if ret > 0: wins += 1
        curr_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        return {"ticker": ticker, "current_rsi": round(curr_rsi,1),
                "signals": signals[-5:], "total_signals": total,
                "win_rate": round(wins/total*100,1) if total else None, "wins": wins}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Moving Average Strategy ───────────────────────────────────────────────────
def get_ma_strategy(ticker, df):
    try:
        ma50  = df["Close"].rolling(50).mean()
        ma200 = df["Close"].rolling(200).mean()
        cross_type = cross_date = cross_price = days_since = None
        for i in range(len(df)-1, max(len(df)-200, 201), -1):
            cd = ma50.iloc[i] - ma200.iloc[i]
            pd_ = ma50.iloc[i-1] - ma200.iloc[i-1]
            if pd.isna(cd) or pd.isna(pd_): continue
            if pd_ <= 0 < cd:
                cross_type = "GOLDEN"; cross_date = str(df.index[i].date())
                cross_price = round(float(df["Close"].iloc[i]),3); days_since = len(df)-1-i; break
            elif pd_ >= 0 > cd:
                cross_type = "DEATH";  cross_date = str(df.index[i].date())
                cross_price = round(float(df["Close"].iloc[i]),3); days_since = len(df)-1-i; break
        gold_rets = []
        for i in range(200, len(df)-61):
            pd_ = ma50.iloc[i-1] - ma200.iloc[i-1]
            cd  = ma50.iloc[i]   - ma200.iloc[i]
            if pd.isna(pd_) or pd.isna(cd): continue
            if pd_ <= 0 < cd:
                gold_rets.append((float(df["Close"].iloc[i+60]) - float(df["Close"].iloc[i])) / float(df["Close"].iloc[i]) * 100)
        price = float(df["Close"].iloc[-1])
        m50   = float(ma50.iloc[-1])  if not pd.isna(ma50.iloc[-1])  else None
        m200  = float(ma200.iloc[-1]) if not pd.isna(ma200.iloc[-1]) else None
        return {"ticker": ticker, "price": round(price,3), "ma50": round(m50,3) if m50 else None,
                "ma200": round(m200,3) if m200 else None,
                "trend": "UPTREND" if (m50 and m200 and m50>m200) else "DOWNTREND",
                "cross_type": cross_type or "NONE", "cross_date": cross_date,
                "cross_price": cross_price, "days_since_cross": days_since,
                "avg_golden_return_60d": round(float(np.mean(gold_rets)),2) if gold_rets else None,
                "n_golden_crosses": len(gold_rets)}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Walk Forward Validation ───────────────────────────────────────────────────
def run_walk_forward(ticker, df, train_days=126, test_days=21, n_windows=5):
    try:
        closes = df["Close"]
        results = []
        for w in range(n_windows):
            te = len(closes) - w * test_days
            ts = te - test_days
            tr = ts - train_days
            if tr < 0: break
            train = closes.iloc[tr:ts]
            test  = closes.iloc[ts:te]
            best_thresh, best_ret = 30, -999
            for th in [25, 28, 30, 32, 35]:
                rsi = _rsi(train, th)
                buys = [float(train.iloc[i]) for i in range(1,len(train))
                        if not pd.isna(rsi.iloc[i-1]) and not pd.isna(rsi.iloc[i]) and rsi.iloc[i-1]<th<=rsi.iloc[i]]
                if buys:
                    r = np.mean([
                        (float(train.iloc[min(k+10,len(train)-1)])-p)/p*100
                        for k,p in enumerate(buys[:5]) if k+10<len(train)
                    ])
                    if r > best_ret: best_ret=r; best_thresh=th
            rsi_t = _rsi(test, best_thresh)
            wins = total = 0
            for i in range(1, len(test)):
                if pd.isna(rsi_t.iloc[i-1]) or pd.isna(rsi_t.iloc[i]): continue
                if rsi_t.iloc[i-1] < best_thresh <= rsi_t.iloc[i]:
                    if i+5 < len(test):
                        r = (float(test.iloc[i+5])-float(test.iloc[i]))/float(test.iloc[i])*100
                        total+=1; wins += (r>0)
            results.append({"window": n_windows-w, "period": f"{df.index[ts].date()} to {df.index[min(te-1,len(df)-1)].date()}",
                            "optimal_rsi_thresh": best_thresh, "test_wins": wins, "test_total": total,
                            "win_rate": round(wins/total*100,1) if total else None})
        results.reverse()
        avg = round(float(np.mean([r["win_rate"] for r in results if r["win_rate"] is not None])),1) if results else None
        return {"ticker": ticker, "windows": results, "avg_win_rate": avg}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Monte Carlo Simulation ────────────────────────────────────────────────────
def run_monte_carlo(ticker, df, n_sims=300, horizon=63):
    try:
        closes = df["Close"].dropna()
        rets = closes.pct_change().dropna()
        mu, sigma = float(rets.mean()), float(rets.std())
        last = float(closes.iloc[-1])
        np.random.seed(42)
        ends = []
        for _ in range(n_sims):
            r = np.random.normal(mu, sigma, horizon)
            path = last
            for ri in r: path *= (1+ri)
            ends.append(path)
        return {"ticker": ticker, "current_price": round(last,3), "horizon_days": horizon, "n_sims": n_sims,
                "p10": round(float(np.percentile(ends,10)),3), "p25": round(float(np.percentile(ends,25)),3),
                "p50": round(float(np.percentile(ends,50)),3), "p75": round(float(np.percentile(ends,75)),3),
                "p90": round(float(np.percentile(ends,90)),3),
                "prob_up": round(sum(1 for p in ends if p>last)/n_sims*100,1),
                "mu_daily": round(mu*100,4), "sigma_daily": round(sigma*100,4)}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Sensitivity Analysis ──────────────────────────────────────────────────────
def run_sensitivity(ticker, df):
    try:
        closes = df["Close"]
        grid = []
        for rp in [7, 10, 14, 21]:
            rsi = _rsi(closes, rp)
            cr = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            for ms, ml in [(20,100),(20,200),(50,100),(50,200)]:
                if len(closes) < ml: continue
                mas = closes.rolling(ms).mean().iloc[-1]
                mal = closes.rolling(ml).mean().iloc[-1]
                cp  = float(closes.iloc[-1])
                score = 50
                if cr < 30: score += 15
                elif cr < 40: score += 8
                elif cr > 70: score -= 15
                elif cr > 60: score -= 8
                if not pd.isna(mas) and not pd.isna(mal):
                    score += 10 if mas > mal else -10
                score += 5 if (not pd.isna(mas) and cp > float(mas)) else -5
                grid.append({"rsi_period": rp, "ma_short": ms, "ma_long": ml,
                             "score": round(score), "rsi_val": round(cr,1)})
        scores = [g["score"] for g in grid]
        return {"ticker": ticker, "grid": grid,
                "score_min": min(scores), "score_max": max(scores),
                "score_range": max(scores)-min(scores), "score_mean": round(float(np.mean(scores)),1)}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Main runner ───────────────────────────────────────────────────────────────
def run_quantitative(tickers):
    print(f"\n--- Quantitative Analysis ({len(tickers)} stocks) ---")
    all_quant = {}
    for ticker in tickers:
        print(f"  Quant: {ticker}...", end=" ", flush=True)
        try:
            yft = yf.Ticker(ticker)
            df  = yft.history(period="2y", auto_adjust=True)
            if df is None or len(df) < 60:
                print("SKIP: no data"); continue
            all_quant[ticker] = {
                "ticker":       ticker,
                "earnings":     get_earnings(yft, ticker),
                "momentum":     get_momentum(ticker, df),
                "rsi_strategy": get_rsi_strategy(ticker, df),
                "ma_strategy":  get_ma_strategy(ticker, df),
                "monte_carlo":  run_monte_carlo(ticker, df),
                "walk_forward": run_walk_forward(ticker, df),
                "sensitivity":  run_sensitivity(ticker, df),
            }
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)

    # Rank momentum across universe
    mom_list = [(t, d["momentum"].get("momentum", 0))
                for t, d in all_quant.items() if "error" not in d.get("momentum", {})]
    mom_list.sort(key=lambda x: x[1])
    n = len(mom_list)
    for i, (t, _) in enumerate(mom_list):
        pct = round(i / max(n-1,1) * 100, 1)
        all_quant[t]["momentum"]["percentile"] = pct
        all_quant[t]["momentum"]["signal"] = "BUY" if pct>=80 else "WATCH" if pct>=50 else "NEUTRAL"

    out = {"results": all_quant, "scanned_at": datetime.now().isoformat(), "tickers": tickers}
    with open(QUANT_FILE, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Quantitative done: {len(all_quant)} stocks\n")
    return all_quant
