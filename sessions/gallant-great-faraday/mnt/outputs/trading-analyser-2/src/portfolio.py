"""
Portfolio Tracker module for Trading Analyser 2.0
Tracks real holdings, paper trades, P&L, dividends.
"""

import json
import os
from datetime import datetime, date
import yfinance as yf

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "../data/portfolio.json")


def load_portfolio() -> dict:
    with open(PORTFOLIO_FILE) as f:
        return json.load(f)


def save_portfolio(data: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def add_holding(ticker: str, shares: float, buy_price: float, buy_date: str, exchange: str = "ASX"):
    """Add a real holding to portfolio."""
    portfolio = load_portfolio()
    holding = {
        "ticker": ticker.upper(),
        "shares": shares,
        "buy_price": buy_price,
        "buy_date": buy_date,
        "exchange": exchange,
        "type": "real"
    }
    portfolio["holdings"].append(holding)
    save_portfolio(portfolio)
    print(f"Added {shares} x {ticker} @ ${buy_price}")


def add_paper_trade(ticker: str, shares: float, buy_price: float, signal: str, reason: str):
    """Add a paper trade (simulated)."""
    portfolio = load_portfolio()
    trade = {
        "ticker": ticker.upper(),
        "shares": shares,
        "buy_price": buy_price,
        "buy_date": str(date.today()),
        "signal": signal,
        "reason": reason,
        "status": "open",
        "type": "paper"
    }
    cost = shares * buy_price
    if portfolio["paper_cash"] < cost:
        print(f"Insufficient paper cash: ${portfolio['paper_cash']:.2f} < ${cost:.2f}")
        return
    portfolio["paper_trades"].append(trade)
    portfolio["paper_cash"] -= cost
    save_portfolio(portfolio)
    print(f"Paper trade: {shares} x {ticker} @ ${buy_price} | Cash left: ${portfolio['paper_cash']:.2f}")


def close_paper_trade(ticker: str, sell_price: float, reason: str = ""):
    """Close an open paper trade."""
    portfolio = load_portfolio()
    for trade in portfolio["paper_trades"]:
        if trade["ticker"] == ticker.upper() and trade["status"] == "open":
            proceeds = trade["shares"] * sell_price
            cost = trade["shares"] * trade["buy_price"]
            pnl = proceeds - cost
            pnl_pct = round((pnl / cost) * 100, 2)
            trade["status"] = "closed"
            trade["sell_price"] = sell_price
            trade["sell_date"] = str(date.today())
            trade["pnl"] = round(pnl, 2)
            trade["pnl_pct"] = pnl_pct
            trade["close_reason"] = reason
            portfolio["paper_cash"] += proceeds
            print(f"Closed {ticker}: P&L = ${pnl:.2f} ({pnl_pct}%)")
            break
    save_portfolio(portfolio)


def get_current_price(ticker: str) -> float:
    try:
        data = yf.Ticker(ticker).history(period="2d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return 0.0


def evaluate_portfolio(results: list = None) -> dict:
    """
    Evaluate current portfolio value.
    results = list of stock analysis results (for latest prices).
    Returns summary dict.
    """
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    paper_trades = portfolio.get("paper_trades", [])

    # Real holdings
    real_summary = []
    total_cost = 0
    total_value = 0

    for h in holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        buy_price = h["buy_price"]
        cost = shares * buy_price

        # Try to get current price from results first
        current_price = 0
        if results:
            match = next((r for r in results if r.get("ticker") == ticker), None)
            if match:
                current_price = match.get("tech", {}).get("price", 0)
        if not current_price:
            current_price = get_current_price(ticker)

        value = shares * current_price
        pnl = value - cost
        pnl_pct = round((pnl / cost) * 100, 2) if cost > 0 else 0

        # Dividend info
        try:
            info = yf.Ticker(ticker).info
            div_yield = info.get("dividendYield", 0) or 0
            annual_div = round(current_price * div_yield * shares, 2)
        except Exception:
            div_yield = 0
            annual_div = 0

        real_summary.append({
            "ticker": ticker,
            "shares": shares,
            "buy_price": buy_price,
            "current_price": round(current_price, 4),
            "cost": round(cost, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": pnl_pct,
            "div_yield_pct": round(div_yield * 100, 2),
            "annual_div_income": annual_div,
        })

        total_cost += cost
        total_value += value

    total_pnl = total_value - total_cost
    total_pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0

    # Paper trades
    open_paper = [t for t in paper_trades if t.get("status") == "open"]
    closed_paper = [t for t in paper_trades if t.get("status") == "closed"]

    paper_pnl_total = sum(t.get("pnl", 0) for t in closed_paper)
    paper_win_rate = 0
    if closed_paper:
        wins = sum(1 for t in closed_paper if t.get("pnl", 0) > 0)
        paper_win_rate = round((wins / len(closed_paper)) * 100, 1)

    # Open paper positions value
    paper_open_value = 0
    for t in open_paper:
        cp = get_current_price(t["ticker"])
        paper_open_value += t["shares"] * cp

    return {
        "as_of": str(datetime.now())[:16],
        "real": {
            "holdings": real_summary,
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
            "total_annual_dividends": round(sum(h["annual_div_income"] for h in real_summary), 2),
        },
        "paper": {
            "cash_balance": round(portfolio.get("paper_cash", 0), 2),
            "open_positions": len(open_paper),
            "open_positions_value": round(paper_open_value, 2),
            "closed_trades": len(closed_paper),
            "realised_pnl": round(paper_pnl_total, 2),
            "win_rate_pct": paper_win_rate,
            "open_trades": open_paper,
            "closed_trades_detail": closed_paper[-10:],  # last 10
        }
    }
