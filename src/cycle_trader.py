"""Cycle Trading — nightly orchestrator for the DJRTrading Daily/Intermediate Cycle strategy.

Mirrors the day_trader.py / agent_trader.py split already used for the ORB strategy:
cycle_analysis.py = pure detection/classification, this module = screens the nightly
watchlist results, manages paper-trade lifecycle (open/close), and persists output for
the dashboard's Cycle Trading tab.
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from portfolio import load_portfolio, add_paper_trade, close_paper_trade

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLE_SIGNALS_FILE = os.path.join(BASE, "data", "cycle_signals.json")
REPORTS_DIR = os.path.join(BASE, "reports")

STRATEGY_TAG = "cycle_trading"
POSITION_SIZE = 2000.0
MAX_OPEN_POSITIONS = 3


def compute_stop_price(entry_zone: dict, live_daily: dict, live_intermediate: dict):
    """Stop below the relevant HCL or ICL/DCL0, per the DJRTrading stop-placement rule."""
    zone = entry_zone.get("zone")
    if zone in ("DC1_HCL", "DC2_HCL") and live_daily.get("hcl_price"):
        return round(live_daily["hcl_price"] * 0.98, 4)
    if zone in ("AT_ICL_DCL0", "DC1_RECOVERY", "BEARISH_IC_DC1_ONLY") and live_intermediate.get("dcl0_price"):
        return round(live_intermediate["dcl0_price"] * 0.98, 4)
    if zone == "CONFIRMED_ABOVE_IC_RESISTANCE":
        anchor = max(live_daily.get("hcl_price") or 0, live_intermediate.get("dcl0_price") or 0)
        return round(anchor * 0.98, 4) if anchor else None
    return None


def screen_candidates(all_results: list) -> dict:
    """Walks the already-computed result['cycle'] for every watchlist ticker (no extra
    yfinance calls). Produces ranked candidates plus failed-cycle and high-risk alerts."""
    candidates, failed_alerts, high_risk_alerts = [], [], []
    for r in all_results:
        if r.get("error"):
            continue
        cyc = r.get("cycle", {})
        if cyc.get("status") != "ok":
            continue
        ticker = r["ticker"]
        name = r.get("name", ticker)
        price = r.get("tech", {}).get("price", 0)
        ez = cyc.get("entry_zone", {})
        cfn = cyc.get("cycle_failing_now", {})
        live_daily = cyc.get("live_daily_cycle", {})

        if cyc.get("current_cycle", {}).get("failed") or cfn.get("failing"):
            failed_alerts.append({
                "ticker": ticker, "name": name, "price": price,
                "type": "live_cycle_failing" if cfn.get("failing") else "completed_cycle_failed",
                "dcl0_price": live_daily.get("dcl0_price"),
                "detail": ("Live cycle" if cfn.get("failing") else "Most recent completed cycle")
                          + " printed a lower low than its own DCL0"
                          + (f" ({cfn.get('pct_below_dcl0')}% below)" if cfn.get("failing") else ""),
            })

        if ez.get("zone") == "HIGH_RISK_DC3_4":
            high_risk_alerts.append({
                "ticker": ticker, "name": name, "price": price,
                "dc_num_in_ic": live_daily.get("cycle_num"),
                "detail": (ez.get("reasons") or [""])[0],
            })

        eligible = (ez.get("eligible_for_entry") and not cfn.get("failing")
                    and not cyc.get("daily_trendline", {}).get("broken"))
        if eligible and price:
            candidates.append({
                "ticker": ticker, "name": name, "price": price,
                "cycle_score": cyc.get("cycle_score", 50), "cycle_signal": cyc.get("cycle_signal"),
                "entry_zone": ez.get("zone"), "risk": ez.get("risk"),
                "dc_num_in_ic": live_daily.get("cycle_num"),
                "predicted_move": cyc.get("predicted_move", {}),
                "stop_price": compute_stop_price(ez, live_daily, cyc.get("live_intermediate_cycle", {})),
                "reasons": (ez.get("reasons", []) + cyc.get("reasons", []))[:5],
            })

    candidates.sort(key=lambda c: c["cycle_score"], reverse=True)
    for i, c in enumerate(candidates):
        c["rank"] = i + 1
    return {"candidates": candidates, "failed_cycle_alerts": failed_alerts, "high_risk_alerts": high_risk_alerts}


def check_exit_conditions(fresh_cycle: dict) -> dict:
    """Phase/time-based exit rules: Failed Cycle, trendline break, or rolled into the
    high-risk Daily-Cycle-3/4 zone. No fixed price target — that's shown for reference
    only (predicted_move) and doesn't trigger the exit by itself."""
    if fresh_cycle.get("cycle_failing_now", {}).get("failing") or fresh_cycle.get("current_cycle", {}).get("failed"):
        return {"exit": True, "reason": "FAILED_CYCLE"}
    if fresh_cycle.get("daily_trendline", {}).get("broken") or fresh_cycle.get("intermediate_trendline", {}).get("broken"):
        return {"exit": True, "reason": "TRENDLINE_BREAK"}
    if fresh_cycle.get("entry_zone", {}).get("zone") == "HIGH_RISK_DC3_4":
        return {"exit": True, "reason": "HIGH_RISK_ZONE_DC3_4"}
    return {"exit": False, "reason": None}


def check_and_close_open_trades(all_results_by_ticker: dict) -> list:
    """Re-evaluates every open Cycle-Trading paper trade against tonight's fresh cycle
    data and closes it if an exit condition fires. If a ticker isn't in tonight's
    watchlist run, its position is left open untouched (can't evaluate it)."""
    portfolio = load_portfolio()
    open_cycle_trades = [t for t in portfolio.get("paper_trades", [])
                          if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    closed = []
    for t in open_cycle_trades:
        r = all_results_by_ticker.get(t["ticker"])
        if not r:
            continue
        fresh_cycle = r.get("cycle", {})
        if fresh_cycle.get("status") != "ok":
            continue
        current_price = r.get("tech", {}).get("price") or t["buy_price"]
        ex = check_exit_conditions(fresh_cycle)
        if ex["exit"]:
            if close_paper_trade(t["ticker"], current_price, reason=ex["reason"], strategy=STRATEGY_TAG):
                closed.append({"ticker": t["ticker"], "reason": ex["reason"], "exit_price": current_price})
    return closed


def open_new_trades(candidates: list) -> list:
    """Opens up to MAX_OPEN_POSITIONS new $POSITION_SIZE positions for the top-ranked
    unentered candidates, respecting paper_cash availability."""
    portfolio = load_portfolio()
    open_cycle_trades = [t for t in portfolio.get("paper_trades", [])
                          if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    already_open = {t["ticker"] for t in open_cycle_trades}
    open_slots = MAX_OPEN_POSITIONS - len(open_cycle_trades)
    opened = []

    for c in candidates:
        if open_slots <= 0:
            break
        if c["ticker"] in already_open:
            continue
        portfolio = load_portfolio()  # re-check cash each iteration
        if portfolio.get("paper_cash", 0) < POSITION_SIZE:
            break
        if not c.get("price"):
            continue
        shares = round(POSITION_SIZE / c["price"], 4)
        ok = add_paper_trade(
            ticker=c["ticker"], shares=shares, buy_price=c["price"],
            signal="CYCLE_BUY", reason="; ".join(c["reasons"][:2]) if c.get("reasons") else "Cycle Trading candidate",
            stop_price=c.get("stop_price"),
            target_price=(c.get("predicted_move") or {}).get("target_price"),
            meta={"strategy": STRATEGY_TAG, "entry_zone": c["entry_zone"],
                  "entered_dc_num": c.get("dc_num_in_ic"), "entered_score": c["cycle_score"]},
        )
        if ok:
            opened.append({"ticker": c["ticker"], "entry_price": c["price"], "shares": shares,
                            "stop_price": c.get("stop_price"),
                            "target_price": (c.get("predicted_move") or {}).get("target_price")})
            already_open.add(c["ticker"])
            open_slots -= 1

    return opened


def write_report_json(all_results: list, today_str: str):
    """Incidental fix: writes reports/report_{date}.json (never written before), which
    makes agent_trader.py::scan_tickers()'s existing dead-code report-merge path start
    working. chart_data is stripped to avoid unbounded git-history growth."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    trimmed = [{k: v for k, v in r.items() if k != "chart_data"} for r in all_results]
    path = os.path.join(REPORTS_DIR, f"report_{today_str}.json")
    with open(path, "w") as f:
        json.dump({"results": trimmed}, f, indent=2, default=str)


def run_cycle_trading(all_results: list) -> dict:
    """Single entry point called from analyser.py's nightly run."""
    all_by_ticker = {r["ticker"]: r for r in all_results if not r.get("error")}

    closed = check_and_close_open_trades(all_by_ticker)
    screened = screen_candidates(all_results)
    opened = open_new_trades(screened["candidates"])

    portfolio = load_portfolio()
    open_trades = [t for t in portfolio.get("paper_trades", [])
                   if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    closed_trades = [t for t in portfolio.get("paper_trades", [])
                      if t.get("status") == "closed" and t.get("meta", {}).get("strategy") == STRATEGY_TAG][-10:]

    for t in open_trades:
        r = all_by_ticker.get(t["ticker"])
        t["_current_price"] = r.get("tech", {}).get("price") if r else None

    signals = {
        "generated_at": datetime.now().isoformat()[:19],
        "watchlist_count": len(all_results),
        "candidates": screened["candidates"],
        "failed_cycle_alerts": screened["failed_cycle_alerts"],
        "high_risk_alerts": screened["high_risk_alerts"],
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "actions_this_run": {"closed": closed, "opened": opened},
    }
    with open(CYCLE_SIGNALS_FILE, "w") as f:
        json.dump(signals, f, indent=2, default=str)

    write_report_json(all_results, datetime.now().strftime("%Y-%m-%d"))
    return signals
