"""Zen Trading — nightly orchestrator.

Mirrors cycle_trader.py's split: zen_analysis.py = pure detection, this module
= screens the nightly watchlist results, manages paper-trade lifecycle
(open/close), and persists output for the dashboard's Zen Trading tab. Same
risk-sizing, drawdown halt, macro halt, sector cap, and cooldown machinery as
Cycle Trading -- proven patterns, reused rather than reinvented -- applied to
Zen's own trend/breakout/reward:risk signals instead of Hurst-cycle phases.
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from portfolio import load_portfolio, add_paper_trade, close_paper_trade

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZEN_SIGNALS_FILE = os.path.join(BASE, "data", "zen_signals.json")
MACRO_FILE = os.path.join(BASE, "data", "macro_gate.json")

STRATEGY_TAG = "zen_trading"
MAX_OPEN_POSITIONS = 5
MAX_POSITION_SIZE = 2000.0        # hard cap per position regardless of risk sizing below
RISK_PER_TRADE_PCT = 1.0          # % of RISK_CAPITAL_BASE risked if the position is stopped out
RISK_CAPITAL_BASE = 10000.0       # notional capital this strategy is sized and drawdown-tracked against
MIN_STOP_DISTANCE_PCT = 1.5       # floor so a very tight/noisy stop can't size an oversized position
ZEN_MAX_DRAWDOWN_PCT = 20.0       # halt new entries once the strategy's own P&L drawdown exceeds this
MAX_POSITIONS_PER_SECTOR = 2      # concentration cap
COOLDOWN_DAYS = 3                 # days to skip re-entering a ticker after a trend-reversal whipsaw
RISK_OFF_ZONE = "RISK OFF"


def macro_zone() -> str:
    try:
        with open(MACRO_FILE) as f:
            return json.load(f).get("zone", "SELECTIVE")
    except Exception:
        return "SELECTIVE"


def compute_position_size(price: float, stop_price) -> float:
    """Risk-normalized sizing: size the position so a stop-out loses about
    RISK_PER_TRADE_PCT of RISK_CAPITAL_BASE, capped at MAX_POSITION_SIZE."""
    if not stop_price or stop_price >= price or price <= 0:
        return MAX_POSITION_SIZE
    stop_distance_pct = max((price - stop_price) / price * 100, MIN_STOP_DISTANCE_PCT)
    dollar_risk = RISK_CAPITAL_BASE * (RISK_PER_TRADE_PCT / 100)
    position_cost = dollar_risk / (stop_distance_pct / 100)
    return round(min(position_cost, MAX_POSITION_SIZE), 2)


def get_real_holding_tickers() -> set:
    portfolio = load_portfolio()
    return {h.get("ticker", "").upper() for h in portfolio.get("holdings", []) if h.get("ticker")}


def compute_zen_drawdown(all_by_ticker: dict) -> dict:
    """Zen Trading's own realized+unrealized P&L as a drawdown against
    RISK_CAPITAL_BASE -- independent of the shared paper_cash figure."""
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
            # tech['price'] can be a numpy.float64 -- cast so nothing downstream
            # inherits a numpy type (a numpy bool from a later >= comparison
            # isn't JSON-serializable, unlike a plain Python bool).
            unrealized_pnl += (float(current_price) - t["buy_price"]) * t["shares"]
    total_pnl = realized_pnl + unrealized_pnl
    drawdown_pct = max(0.0, round(-total_pnl / RISK_CAPITAL_BASE * 100, 2))
    return {
        "realized_pnl": round(realized_pnl, 2), "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2), "drawdown_pct": drawdown_pct,
        "halted": bool(drawdown_pct >= ZEN_MAX_DRAWDOWN_PCT),
    }


def _tickers_in_cooldown() -> dict:
    """ticker -> days remaining, for tickers whose most recent Zen Trading close
    was a trend-reversal whipsaw within COOLDOWN_DAYS."""
    portfolio = load_portfolio()
    today = datetime.now().date()
    cooldowns = {}
    for t in portfolio.get("paper_trades", []):
        if t.get("meta", {}).get("strategy") != STRATEGY_TAG: continue
        if t.get("status") != "closed": continue
        if t.get("close_reason") != "TREND_REVERSAL": continue
        try:
            sell_date = datetime.strptime(t["sell_date"], "%Y-%m-%d").date()
        except Exception:
            continue
        days_since = (today - sell_date).days
        if days_since < COOLDOWN_DAYS:
            ticker = t["ticker"]
            cooldowns[ticker] = max(cooldowns.get(ticker, 0), COOLDOWN_DAYS - days_since)
    return cooldowns


def screen_candidates(all_results: list, real_holdings: set = None) -> dict:
    """Walks the already-computed result['zen'] for every watchlist ticker (no
    extra yfinance calls). Produces ranked candidates plus AVOID alerts for
    tickers with an established bearish trend (a real-time warning, distinct
    from just not appearing as a candidate)."""
    real_holdings = real_holdings or set()
    cooldowns = _tickers_in_cooldown()
    candidates, avoid_alerts = [], []
    for r in all_results:
        if r.get("error"):
            continue
        zen = r.get("zen", {})
        if zen.get("status") != "ok":
            continue
        ticker = r["ticker"]
        name = r.get("name", ticker)
        price = zen.get("price") or r.get("tech", {}).get("price", 0)
        sector = r.get("sector", "Unknown")

        if zen.get("zen_signal") == "AVOID":
            avoid_alerts.append({
                "ticker": ticker, "name": name, "price": price,
                "detail": f"Heiken-Ashi trend BEARISH for {zen.get('trend', {}).get('consecutive_bars', '?')} bars",
            })

        if zen.get("zen_signal") == "BUY" and zen.get("eligible_for_entry") and price:
            candidates.append({
                "ticker": ticker, "name": name, "price": price, "sector": sector,
                "zen_score": zen.get("zen_score", 50),
                "trend": zen.get("trend", {}), "breakout": zen.get("breakout", {}),
                "stop_price": zen.get("stop_price"), "target_price": zen.get("target_price"),
                "reward_risk": zen.get("reward_risk"),
                "position_size": compute_position_size(price, zen.get("stop_price")),
                "already_held_real": ticker.upper() in real_holdings,
                "cooldown_days_remaining": cooldowns.get(ticker.upper(), 0),
                "reasons": zen.get("reasons", [])[:5],
            })

    candidates.sort(key=lambda c: c["zen_score"], reverse=True)
    for i, c in enumerate(candidates):
        c["rank"] = i + 1
    return {"candidates": candidates, "avoid_alerts": avoid_alerts}


def check_exit_conditions(fresh_zen: dict, current_price: float = None, stop_price: float = None) -> dict:
    """Hard price stop as a backstop underneath the phase logic (trend
    reversal), since the phase read can lag a fast move by a day."""
    if stop_price is not None and current_price is not None and current_price <= stop_price:
        return {"exit": True, "reason": "HARD_STOP"}
    if fresh_zen.get("trend", {}).get("direction") in ("BEARISH", "CHOPPY"):
        return {"exit": True, "reason": "TREND_REVERSAL"}
    return {"exit": False, "reason": None}


def check_and_close_open_trades(all_results_by_ticker: dict) -> list:
    """Re-evaluates every open Zen Trading paper trade against tonight's fresh
    zen data and closes it if an exit condition fires. A ticker missing from
    tonight's watchlist run is left open untouched (can't evaluate it)."""
    portfolio = load_portfolio()
    open_zen_trades = [t for t in portfolio.get("paper_trades", [])
                        if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    closed = []
    for t in open_zen_trades:
        r = all_results_by_ticker.get(t["ticker"])
        if not r:
            continue
        fresh_zen = r.get("zen", {})
        if fresh_zen.get("status") != "ok":
            continue
        current_price = r.get("tech", {}).get("price") or t["buy_price"]
        ex = check_exit_conditions(fresh_zen, current_price=current_price, stop_price=t.get("stop_price"))
        if ex["exit"]:
            if close_paper_trade(t["ticker"], current_price, reason=ex["reason"], strategy=STRATEGY_TAG):
                closed.append({"ticker": t["ticker"], "reason": ex["reason"], "exit_price": current_price})
    return closed


def open_new_trades(candidates: list) -> list:
    """Opens up to MAX_OPEN_POSITIONS new risk-sized positions for the
    top-ranked unentered candidates, respecting paper_cash, a per-sector
    concentration cap, and skipping tickers already held for real."""
    portfolio = load_portfolio()
    open_zen_trades = [t for t in portfolio.get("paper_trades", [])
                        if t.get("status") == "open" and t.get("meta", {}).get("strategy") == STRATEGY_TAG]
    already_open = {t["ticker"] for t in open_zen_trades}
    open_slots = MAX_OPEN_POSITIONS - len(open_zen_trades)
    sector_counts = {}
    for t in open_zen_trades:
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
        if c.get("cooldown_days_remaining"):
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
            signal="ZEN_BUY", reason="; ".join(c["reasons"][:2]) if c.get("reasons") else "Zen Trading candidate",
            stop_price=c.get("stop_price"), target_price=c.get("target_price"),
            meta={"strategy": STRATEGY_TAG, "sector": sector, "entered_score": c["zen_score"],
                  "entered_reward_risk": c.get("reward_risk")},
        )
        if ok:
            opened.append({"ticker": c["ticker"], "entry_price": c["price"], "shares": shares,
                            "position_cost": position_cost, "sector": sector,
                            "stop_price": c.get("stop_price"), "target_price": c.get("target_price")})
            already_open.add(c["ticker"])
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            open_slots -= 1

    return opened


def run_zen_trading(all_results: list) -> dict:
    """Single entry point called from analyser.py's nightly run."""
    all_by_ticker = {r["ticker"]: r for r in all_results if not r.get("error")}

    closed = check_and_close_open_trades(all_by_ticker)
    drawdown = compute_zen_drawdown(all_by_ticker)
    screened = screen_candidates(all_results, real_holdings=get_real_holding_tickers())

    mz = macro_zone()
    macro_halt = mz == RISK_OFF_ZONE
    if macro_halt:
        print(f"  Zen Trading MACRO HALT: zone is {mz} — no new entries this run")

    if drawdown["halted"]:
        print(f"  Zen Trading DRAWDOWN HALT: {drawdown['drawdown_pct']}% below baseline "
              f"(limit {ZEN_MAX_DRAWDOWN_PCT}%) — no new entries this run")
        opened = []
    elif macro_halt:
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

    opened_tickers = {o["ticker"] for o in opened}
    open_ticker_set = {t["ticker"] for t in open_trades}
    for c in screened["candidates"]:
        if c["ticker"] in opened_tickers:
            c["paper_trade_status"] = "OPENED_THIS_RUN"
        elif c["ticker"] in open_ticker_set:
            c["paper_trade_status"] = "ALREADY_OPEN"
        elif c.get("already_held_real"):
            c["paper_trade_status"] = "SKIPPED_ALREADY_HELD_REAL"
        elif c.get("cooldown_days_remaining"):
            c["paper_trade_status"] = "SKIPPED_COOLDOWN"
        else:
            c["paper_trade_status"] = "NOT_OPENED"

    signals = {
        "generated_at": datetime.now().isoformat()[:19],
        "watchlist_count": len(all_results),
        "candidates": screened["candidates"],
        "avoid_alerts": screened["avoid_alerts"],
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "drawdown": drawdown,
        "macro_zone": mz, "macro_halted": macro_halt,
        "actions_this_run": {"closed": closed, "opened": opened},
    }
    with open(ZEN_SIGNALS_FILE, "w") as f:
        json.dump(signals, f, indent=2, default=str)

    return signals
