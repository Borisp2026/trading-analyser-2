"""Agent Trader — Autonomous Day Trading Test Run
Runs every 5 min via GitHub Actions during market hours.
Tracks 30 simulated trades before paper/live go-live.
Strategy: ORB + VWAP breakout, 5% target, 2% stop.
"""
import json, os, sys, time
from datetime import datetime, date
import yfinance as yf
import pandas as pd
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from day_trader import check_entry, check_exit, is_trading_window

BASE          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_FILE    = os.path.join(BASE, "data", "agent_trades.json")
WATCHLIST_FILE= os.path.join(BASE, "data", "watchlist.json")
MACRO_FILE    = os.path.join(BASE, "data", "macro_gate.json")
AEST          = pytz.timezone('Australia/Sydney')

TARGET_TRADES = 30
START_CAPITAL = 5000.0
MAX_POSITIONS = 2
POS_SIZE      = 2500.0  # fixed $2500 per trade


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(AGENT_FILE):
        with open(AGENT_FILE) as f:
            return json.load(f)
    return {
        "trades": [], "open_positions": {},
        "capital": START_CAPITAL, "starting_capital": START_CAPITAL,
        "scan_log": [], "status": "RUNNING",
        "target_trades": TARGET_TRADES,
        "started_at": datetime.now().isoformat(),
        "stats": {}
    }

def save_data(d):
    with open(AGENT_FILE, 'w') as f:
        json.dump(d, f, indent=2, default=str)

def macro_score():
    try:
        with open(MACRO_FILE) as f:
            return float(json.load(f).get("composite", 50))
    except Exception:
        return 50.0

def scan_tickers():
    """Watchlist tickers + top nightly report tickers, capped at 50."""
    import glob
    seen, result = set(), []
    try:
        with open(WATCHLIST_FILE) as f:
            wl = json.load(f)
        for t in wl.get("asx", []) + wl.get("etf", []):
            if t not in seen:
                seen.add(t); result.append(t)
    except Exception:
        pass
    wl_count = len(result)
    try:
        files = sorted(glob.glob(os.path.join(BASE, "reports", "*.json")))
        if files:
            rep = json.load(open(files[-1]))
            ranked = sorted(rep.get("results", []),
                key=lambda x: x.get("reasoning", {}).get("blended_score", 0), reverse=True)
            for r in ranked:
                t = r.get("ticker", "")
                if t and t not in seen and len(result) < 50:
                    seen.add(t); result.append(t)
    except Exception as e:
        print(f"  Report tickers error: {e}")
    print(f"  Scan list: {len(result)} tickers ({wl_count} watchlist + {len(result)-wl_count} report)")
    return result[:50]


def update_eod_tracking(d, tickers):
    """Track days each ticker appears, build EOD assessment, auto-add after 5 days."""
    today = datetime.now(AEST).strftime("%Y-%m-%d")
    td = d.setdefault("ticker_days", {})
    for t in tickers:
        days = td.setdefault(t, [])
        if today not in days:
            days.append(today)
    try:
        with open(WATCHLIST_FILE) as f:
            wl = json.load(f)
    except Exception:
        wl = {"asx": [], "etf": [], "nasdaq": [], "settings": {}}
    wl_set = set(wl.get("asx", []) + wl.get("etf", []) + wl.get("nasdaq", []))
    assessment, auto_added = [], []
    for t in tickers:
        days_list = td.get(t, [])
        t_logs = [e for e in d.get("scan_log", []) if e.get("ticker") == t and e.get("date") == today]
        assessment.append({
            "ticker":       t,
            "days_in_list": len(days_list),
            "last_5_days":  days_list[-5:],
            "scans_today":  len(t_logs),
            "buys_today":   sum(1 for e in t_logs if e.get("signal") == "BUY"),
            "in_watchlist": t in wl_set,
            "add_pending":  len(days_list) >= 5 and t not in wl_set,
        })
        if len(days_list) >= 5 and t not in wl_set:
            key = "asx" if t.endswith(".AX") else "nasdaq"
            wl.setdefault(key, []).append(t)
            wl_set.add(t)
            auto_added.append(t)
            print(f"  AUTO-WATCHLIST: {t} ({len(days_list)} days)")
    d["eod_assessment"] = sorted(assessment, key=lambda x: x["days_in_list"], reverse=True)
    if auto_added:
        try:
            with open(WATCHLIST_FILE, "w") as f:
                json.dump(wl, f, indent=2)
            print(f"  Watchlist updated with: {auto_added}")
        except Exception as e:
            print(f"  Watchlist save error: {e}")

def fetch_1min(ticker):
    df = yf.Ticker(ticker).history(period="1d", interval="1m", auto_adjust=True)
    if df is not None and len(df) > 0:
        df.index = pd.to_datetime(df.index)
    return df

def calc_stats(d):
    closed = [t for t in d["trades"] if t["status"] == "CLOSED"]
    wins   = [t for t in closed if (t.get("pnl_pct") or 0) > 0]
    pnls   = [t.get("pnl_pct", 0) for t in closed]
    return {
        "total_trades":    len(d["trades"]),
        "closed_trades":   len(closed),
        "open_trades":     len(d["open_positions"]),
        "wins":            len(wins),
        "losses":          len(closed) - len(wins),
        "win_rate":        round(len(wins)/len(closed)*100, 1) if closed else 0,
        "avg_pnl_pct":     round(sum(pnls)/len(pnls), 2) if pnls else 0,
        "total_pnl_pct":   round(sum(pnls), 2),
        "current_capital": round(d.get("capital", START_CAPITAL), 2),
        "capital_growth":  round((d.get("capital", START_CAPITAL) - START_CAPITAL) / START_CAPITAL * 100, 2),
    }


# ── Main scan ─────────────────────────────────────────────────────────────────
def run_agent_scan():
    now_str = datetime.now(AEST).strftime('%H:%M:%S AEST')
    print(f"\n{'='*50}")
    print(f"Agent Scan — {now_str}")
    print(f"{'='*50}")

    d = load_data()

    # Completed?
    if len(d["trades"]) >= TARGET_TRADES and not d["open_positions"]:
        d["status"] = "COMPLETED"
        d["stats"]  = calc_stats(d)
        d["completed_at"] = datetime.now().isoformat()
        save_data(d)
        print(f"✓ Test COMPLETE: {d['stats']['win_rate']}% win rate | Avg {d['stats']['avg_pnl_pct']:+.1f}%")
        return

    ms     = macro_score()
    tickers = scan_tickers()
    capital = d.get("capital", START_CAPITAL)
    print(f"Macro: {ms:.0f} | Capital: ${capital:.2f} | Open: {len(d['open_positions'])} | Trades: {len(d['trades'])}/{TARGET_TRADES}")

    # ── 1. Check exits ────────────────────────────────────────────────────────
    for ticker, pos in list(d["open_positions"].items()):
        try:
            df = fetch_1min(ticker)
            if df is None or len(df) == 0: continue
            price = float(df['Close'].iloc[-1])
            ex = check_exit(pos, price)
            if ex["exit"]:
                pnl_pct    = ex["pnl_pct"]
                pos_size   = pos.get("position_size", capital / MAX_POSITIONS)
                exit_fee   = round(pos_size * 0.001, 2)
                pnl_dollar = round(pos_size * pnl_pct / 100 - exit_fee, 2)
                capital   += pos_size + pnl_dollar
                # Update trade record
                for t in d["trades"]:
                    if t["id"] == pos["trade_id"]:
                        t.update({
                            "exit_price":  ex["exit_price"],
                            "exit_time":   datetime.now().isoformat(),
                            "exit_reason": ex["reason"],
                            "pnl_pct":     pnl_pct,
                            "pnl_dollar":  pnl_dollar,
                            "outcome":     "WIN" if pnl_pct > 0 else "LOSS",
                            "status":      "CLOSED",
                        })
                del d["open_positions"][ticker]
                print(f"  EXIT {ticker} | {ex['reason']} | {pnl_pct:+.1f}% | ${pnl_dollar:+.2f}")
        except Exception as e:
            print(f"  Exit error {ticker}: {e}")

    d["capital"] = round(capital, 2)

    # ── 2. Scan for entries ───────────────────────────────────────────────────
    open_count  = len(d["open_positions"])
    trades_done = len(d["trades"])

    for ticker in tickers:
        if open_count >= MAX_POSITIONS: break
        if trades_done >= TARGET_TRADES: break
        if ticker in d["open_positions"]: continue
        if not is_trading_window(ticker): continue

        try:
            df     = fetch_1min(ticker)
            sig    = check_entry(ticker, df, ms)
            log_e  = {
                "time":   datetime.now(AEST).strftime('%H:%M'),
                "date":   datetime.now(AEST).strftime('%Y-%m-%d'),
                "ticker": ticker,
                "signal": sig.get("signal", "ERR"),
                "price":  sig.get("entry_price") or sig.get("price", 0),
                "notes":  (sig.get("reasons", [])[:1] or [""])[0][:60],
            }
            d["scan_log"] = d["scan_log"][-300:]
            d["scan_log"].append(log_e)

            if sig and sig["signal"] == "BUY":
                trade_id  = trades_done + 1
                pos_size  = min(POS_SIZE, round(capital * 0.5, 2))
                trade = {
                    "id":             trade_id,
                    "ticker":         ticker,
                    "entry_price":    sig["entry_price"],
                    "entry_time":     datetime.now().isoformat(),
                    "target":         sig["target"],
                    "stop":           sig["stop"],
                    "vwap":           sig.get("vwap"),
                    "rsi":            sig.get("rsi"),
                    "orb_high":       sig.get("orb_high"),
                    "conditions_met": sig.get("conditions_met"),
                    "reasons":        sig.get("reasons", []),
                    "position_size":  pos_size,
                    "macro_score":    ms,
                    "status":         "OPEN",
                    "exit_price":     None,
                    "exit_time":      None,
                    "exit_reason":    None,
                    "pnl_pct":        None,
                    "pnl_dollar":     None,
                    "outcome":        "PENDING",
                }
                d["trades"].append(trade)
                d["open_positions"][ticker] = {
                    "trade_id":     trade_id,
                    "entry_price":  sig["entry_price"],
                    "target":       sig["target"],
                    "stop":         sig["stop"],
                    "position_size":pos_size,
                }
                fee = round(pos_size * 0.001, 2)  # entry fee
                capital      -= pos_size + fee
                d["capital"]  = round(capital, 2)
                open_count   += 1
                trades_done  += 1
                print(f"  BUY  {ticker} @ ${sig['entry_price']} | T:${sig['target']} S:${sig['stop']} | {sig['conditions_met']}/5 conditions")
            else:
                reasons = (sig.get("reasons", []) if sig else [])
                skip_r  = [r for r in reasons if r.startswith("✗")]
                print(f"  SKIP {ticker}: {skip_r[0] if skip_r else 'no signal'}")

            time.sleep(0.3)
        except Exception as e:
            print(f"  Entry error {ticker}: {e}")

    d["stats"]     = calc_stats(d)
    d["last_scan"] = datetime.now().isoformat()
    update_eod_tracking(d, tickers)
    save_data(d)

    s = d["stats"]
    print(f"\nSummary: {s['closed_trades']}/{TARGET_TRADES} done | Win {s['win_rate']}% | Avg {s['avg_pnl_pct']:+.1f}% | Capital ${s['current_capital']:.2f}")


if __name__ == "__main__":
    run_agent_scan()
