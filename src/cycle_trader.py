"""Cycle Trading — nightly orchestrator for the DJRTrading Daily/Intermediate Cycle strategy.

Mirrors the day_trader.py / agent_trader.py split already used for the ORB strategy:
cycle_analysis.py = pure detection/classification, this module = screens the nightly
watchlist results, manages paper-trade lifecycle (open/close), and persists output for
the dashboard's Cycle Trading tab.
"""
import json, os, sys
from datetime import datetime
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from portfolio import load_portfolio, add_paper_trade, close_paper_trade

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLE_SIGNALS_FILE = os.path.join(BASE, "data", "cycle_signals.json")
REPORTS_DIR = os.path.join(BASE, "reports")

STRATEGY_TAG = "cycle_trading"
MAX_OPEN_POSITIONS = 5
MAX_POSITION_SIZE = 2000.0        # hard cap per position regardless of risk sizing below
RISK_PER_TRADE_PCT = 1.0          # % of RISK_CAPITAL_BASE risked if the position is stopped out
RISK_CAPITAL_BASE = 10000.0       # notional capital this strategy is sized and drawdown-tracked against
MIN_STOP_DISTANCE_PCT = 1.5       # floor so a very tight/noisy stop can't size an oversized position
CYCLE_MAX_DRAWDOWN_PCT = 20.0     # halt new entries once the strategy's own P&L drawdown exceeds this
MAX_POSITIONS_PER_SECTOR = 2      # concentration cap


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


def compute_position_size(price: float, stop_price) -> float:
    """Risk-normalized sizing: size the position so a stop-out loses about
    RISK_PER_TRADE_PCT of RISK_CAPITAL_BASE, capped at MAX_POSITION_SIZE. A flat
    dollar amount regardless of stop distance (the old behavior) means a trade
    with a tight stop and one with a wide stop carry very different dollar risk
    for the same allocation -- this keeps dollar risk roughly constant instead.
    Falls back to MAX_POSITION_SIZE if there's no usable stop to size against."""
    if not stop_price or stop_price >= price or price <= 0:
        return MAX_POSITION_SIZE
    stop_distance_pct = max((price - stop_price) / price * 100, MIN_STOP_DISTANCE_PCT)
    dollar_risk = RISK_CAPITAL_BASE * (RISK_PER_TRADE_PCT / 100)
    position_cost = dollar_risk / (stop_distance_pct / 100)
    return round(min(position_cost, MAX_POSITION_SIZE), 2)


def get_real_holding_tickers() -> set:
    """Tickers already held for real, per data/portfolio.json's holdings -- checked
    before auto-opening a Cycle Trading paper position so the system doesn't
    unknowingly recommend piling onto something already held with real money."""
    portfolio = load_portfolio()
    return {h.get("ticker", "").upper() for h in portfolio.get("holdings", []) if h.get("ticker")}


def compute_cycle_drawdown(all_by_ticker: dict) -> dict:
    """Cycle Trading's own realized+unrealized P&L as a drawdown against
    RISK_CAPITAL_BASE -- independent of the shared paper_cash figure, which other
    strategies or manual trades can also move. Mirrors agent_trader.py's
    MAX_DRAWDOWN_PCT circuit breaker, which Cycle Trading didn't have before."""
    portfolio = load_portfolio()
    trades = [t for t in portfolio.get("paper_trades", []) if t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    realized_pnl = sum(t.get("pnl", 0) for t in trades if t.get("status") == "closed")
    unrealized_pnl = 0.0
    for t in trades:
        if t.get("status") != "open":
            continue
        r = all_by_ticker.get(t["ticker"])
        current_price = r.get("tech", {}).get("price") if r else None
        if current_price:
            # tech['price'] is a numpy.float64 (technical.py rounds a pandas value without
            # casting) -- harmless on its own since it subclasses float, but arithmetic that
            # carries it forward keeps everything numpy-typed, and a numpy comparison later
            # (>=) returns numpy.bool_, which -- unlike numpy.float64 -- is NOT a bool
            # subclass and isn't JSON-serializable. Cast here so nothing downstream inherits it.
            unrealized_pnl += (float(current_price) - t["buy_price"]) * t["shares"]
    total_pnl = realized_pnl + unrealized_pnl
    drawdown_pct = max(0.0, round(-total_pnl / RISK_CAPITAL_BASE * 100, 2))
    return {
        "realized_pnl": round(realized_pnl, 2), "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2), "drawdown_pct": drawdown_pct,
        "halted": bool(drawdown_pct >= CYCLE_MAX_DRAWDOWN_PCT),
    }


def screen_candidates(all_results: list, real_holdings: set = None) -> dict:
    """Walks the already-computed result['cycle'] for every watchlist ticker (no extra
    yfinance calls). Produces ranked candidates plus failed-cycle and high-risk alerts."""
    real_holdings = real_holdings or set()
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
        sector = r.get("sector", "Unknown")
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
            stop_price = compute_stop_price(ez, live_daily, cyc.get("live_intermediate_cycle", {}))
            target_price = (cyc.get("predicted_move") or {}).get("target_price")
            overlay = dict(cyc.get("chart_overlay") or {})
            overlay.update({"entry_price": price, "stop_price": stop_price, "target_price": target_price})
            candidates.append({
                "ticker": ticker, "name": name, "price": price, "sector": sector,
                "cycle_score": cyc.get("cycle_score", 50), "cycle_signal": cyc.get("cycle_signal"),
                "entry_zone": ez.get("zone"), "risk": ez.get("risk"),
                "dc_num_in_ic": live_daily.get("cycle_num"),
                "predicted_move": cyc.get("predicted_move", {}),
                "stop_price": stop_price,
                "position_size": compute_position_size(price, stop_price),
                "already_held_real": ticker.upper() in real_holdings,
                "reasons": (ez.get("reasons", []) + cyc.get("reasons", []))[:5],
                "chart_overlay": overlay,
            })

    candidates.sort(key=lambda c: c["cycle_score"], reverse=True)
    for i, c in enumerate(candidates):
        c["rank"] = i + 1
    return {"candidates": candidates, "failed_cycle_alerts": failed_alerts, "high_risk_alerts": high_risk_alerts}


def check_exit_conditions(fresh_cycle: dict, current_price: float = None, stop_price: float = None) -> dict:
    """Phase/time-based exit rules, plus a hard price stop as a backstop underneath
    them -- the phase logic (failed cycle, trendline break, high-risk zone) can be
    slow to fire, so a stop breach shouldn't have to wait on it. No fixed price
    TARGET triggers an exit -- that's shown for reference only; the hard STOP is
    the one price level that actually does."""
    if stop_price is not None and current_price is not None and current_price <= stop_price:
        return {"exit": True, "reason": "HARD_STOP"}
    if fresh_cycle.get("cycle_failing_now", {}).get("failing") or fresh_cycle.get("current_cycle", {}).get("failed"):
        return {"exit": True, "reason": "FAILED_CYCLE"}
    if (fresh_cycle.get("daily_trendline", {}).get("broken")
            or fresh_cycle.get("live_daily_trendline", {}).get("broken")
            or fresh_cycle.get("intermediate_trendline", {}).get("broken")):
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
        ex = check_exit_conditions(fresh_cycle, current_price=current_price, stop_price=t.get("stop_price"))
        if ex["exit"]:
            if close_paper_trade(t["ticker"], current_price, reason=ex["reason"], strategy=STRATEGY_TAG):
                closed.append({"ticker": t["ticker"], "reason": ex["reason"], "exit_price": current_price})
    return closed


def check_intraday_hard_stops() -> list:
    """Lightweight stop-loss check for open Cycle Trading positions, meant to run
    every 5 min by piggybacking on agent_scan.yml's existing cadence (called from
    agent_trader.py) so a stop breach is caught same-day rather than waiting for
    the next nightly cycle re-analysis. Only checks the hard stop_price -- the
    phase-based conditions still need the full nightly re-analysis and are handled
    separately in check_and_close_open_trades."""
    portfolio = load_portfolio()
    open_cycle_trades = [t for t in portfolio.get("paper_trades", [])
                          if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    closed = []
    for t in open_cycle_trades:
        stop_price = t.get("stop_price")
        if not stop_price:
            continue
        try:
            df = yf.Ticker(t["ticker"]).history(period="1d", interval="1m", auto_adjust=True)
            if df is None or len(df) == 0:
                continue
            current_price = float(df["Close"].iloc[-1])
        except Exception:
            continue
        if current_price <= stop_price:
            if close_paper_trade(t["ticker"], current_price, reason="HARD_STOP_INTRADAY", strategy=STRATEGY_TAG):
                closed.append({"ticker": t["ticker"], "exit_price": current_price, "stop_price": stop_price})
    return closed


def open_new_trades(candidates: list) -> list:
    """Opens up to MAX_OPEN_POSITIONS new risk-sized positions for the top-ranked
    unentered candidates, respecting paper_cash availability, a per-sector
    concentration cap, and skipping tickers already held for real."""
    portfolio = load_portfolio()
    open_cycle_trades = [t for t in portfolio.get("paper_trades", [])
                          if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    already_open = {t["ticker"] for t in open_cycle_trades}
    open_slots = MAX_OPEN_POSITIONS - len(open_cycle_trades)
    sector_counts = {}
    for t in open_cycle_trades:
        s = t.get("meta", {}).get("sector", "Unknown")
        sector_counts[s] = sector_counts.get(s, 0) + 1
    opened = []

    for c in candidates:
        if open_slots <= 0:
            break
        if c["ticker"] in already_open:
            continue
        if c.get("already_held_real"):
            continue
        if not c.get("price"):
            continue
        sector = c.get("sector", "Unknown")
        if sector_counts.get(sector, 0) >= MAX_POSITIONS_PER_SECTOR:
            continue
        position_cost = compute_position_size(c["price"], c.get("stop_price"))
        portfolio = load_portfolio()  # re-check cash each iteration
        if portfolio.get("paper_cash", 0) < position_cost:
            break
        shares = round(position_cost / c["price"], 4)
        if shares <= 0:
            continue
        ok = add_paper_trade(
            ticker=c["ticker"], shares=shares, buy_price=c["price"],
            signal="CYCLE_BUY", reason="; ".join(c["reasons"][:2]) if c.get("reasons") else "Cycle Trading candidate",
            stop_price=c.get("stop_price"),
            target_price=(c.get("predicted_move") or {}).get("target_price"),
            meta={"strategy": STRATEGY_TAG, "entry_zone": c["entry_zone"], "sector": sector,
                  "entered_dc_num": c.get("dc_num_in_ic"), "entered_score": c["cycle_score"]},
        )
        if ok:
            opened.append({"ticker": c["ticker"], "entry_price": c["price"], "shares": shares,
                            "position_cost": position_cost, "sector": sector,
                            "stop_price": c.get("stop_price"),
                            "target_price": (c.get("predicted_move") or {}).get("target_price")})
            already_open.add(c["ticker"])
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
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
    drawdown = compute_cycle_drawdown(all_by_ticker)
    screened = screen_candidates(all_results, real_holdings=get_real_holding_tickers())

    if drawdown["halted"]:
        print(f"  Cycle Trading DRAWDOWN HALT: {drawdown['drawdown_pct']}% below baseline "
              f"(limit {CYCLE_MAX_DRAWDOWN_PCT}%) — no new entries this run")
        opened = []
    else:
        opened = open_new_trades(screened["candidates"])

    portfolio = load_portfolio()
    open_trades = [t for t in portfolio.get("paper_trades", [])
                   if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    closed_trades = [t for t in portfolio.get("paper_trades", [])
                      if t.get("status") == "closed" and t.get("meta", {}).get("strategy") == STRATEGY_TAG][-10:]

    for t in open_trades:
        r = all_by_ticker.get(t["ticker"])
        t["_current_price"] = r.get("tech", {}).get("price") if r else None
        overlay = dict((r.get("cycle", {}).get("chart_overlay") or {}) if r else {})
        overlay.update({"entry_price": t.get("buy_price"), "stop_price": t.get("stop_price"),
                         "target_price": t.get("target_price")})
        t["chart_overlay"] = overlay

    opened_tickers = {o["ticker"] for o in opened}
    open_ticker_set = {t["ticker"] for t in open_trades}
    for c in screened["candidates"]:
        if c["ticker"] in opened_tickers:
            c["paper_trade_status"] = "OPENED_THIS_RUN"
        elif c["ticker"] in open_ticker_set:
            c["paper_trade_status"] = "ALREADY_OPEN"
        elif c.get("already_held_real"):
            c["paper_trade_status"] = "SKIPPED_ALREADY_HELD_REAL"
        else:
            c["paper_trade_status"] = "NOT_OPENED"

    signals = {
        "generated_at": datetime.now().isoformat()[:19],
        "watchlist_count": len(all_results),
        "candidates": screened["candidates"],
        "failed_cycle_alerts": screened["failed_cycle_alerts"],
        "high_risk_alerts": screened["high_risk_alerts"],
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "drawdown": drawdown,
        "actions_this_run": {"closed": closed, "opened": opened},
    }
    with open(CYCLE_SIGNALS_FILE, "w") as f:
        json.dump(signals, f, indent=2, default=str)

    write_report_json(all_results, datetime.now().strftime("%Y-%m-%d"))
    return signals
