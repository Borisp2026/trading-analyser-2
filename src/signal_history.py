"""
Signal History / Daily Advice Log — Trading Analyser 2.0
Records each day's recommendation + next day's actual move.
Keeps 30 days of history per stock.
"""
import json, os
from datetime import datetime, date, timedelta
import yfinance as yf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE, "data", "signal_history.json")
MAX_DAYS = 30


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(data: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def record_signals(results: list):
    """
    Called at end of nightly run. Saves today's recommendations.
    Also fills in yesterday's actual move for each stock.
    """
    history = load_history()
    today_str = str(date.today())

    for r in results:
        ticker = r.get("ticker")
        if not ticker:
            continue

        rec = r.get("reasoning", {})
        tech = r.get("tech", {})

        if ticker not in history:
            history[ticker] = []

        # Fill in actual move for yesterday's record (if it exists and is unfilled)
        if history[ticker]:
            last = history[ticker][-1]
            if last.get("date") != today_str and not last.get("actual_next_day_pct"):
                try:
                    price_today = tech.get("price", 0)
                    price_yesterday = tech.get("price_prev")
                    if not price_yesterday:
                        df = yf.Ticker(ticker).history(period="5d", auto_adjust=True)
                        if len(df) >= 2:
                            price_yesterday = float(df["Close"].iloc[-2])
                            price_today = float(df["Close"].iloc[-1])
                    if price_yesterday and price_today:
                        actual = round(((price_today - price_yesterday) / price_yesterday) * 100, 2)
                        last["actual_next_day_pct"] = actual
                        last["actual_direction"] = "UP" if actual > 0 else "DOWN"
                        # Was the signal correct?
                        predicted_up = "BUY" in last.get("recommendation", "")
                        actually_up = actual > 0
                        last["signal_correct"] = predicted_up == actually_up
                        last["outcome"] = "CORRECT" if last["signal_correct"] else "WRONG"
                except Exception:
                    pass

        # Add today's record
        entry = {
            "date": today_str,
            "recommendation": rec.get("recommendation", "?"),
            "blended_score": rec.get("blended_score", 50),
            "price": tech.get("price", 0),
            "entry_price": rec.get("entry_price"),
            "stop_loss": rec.get("stop_loss"),
            "take_profit": rec.get("take_profit"),
            "confidence": rec.get("confidence", "?"),
            "actual_next_day_pct": None,
            "actual_direction": None,
            "signal_correct": None,
            "outcome": "PENDING",
        }

        if history[ticker] and history[ticker][-1].get("date") == today_str:
            history[ticker][-1] = entry  # overwrite today's entry -- one per day
        else:
            history[ticker].append(entry)

        # Keep only last MAX_DAYS entries
        history[ticker] = history[ticker][-MAX_DAYS:]

    save_history(history)
    print(f"Signal history updated for {len(results)} stocks")
    return history


def get_accuracy_summary(history: dict) -> dict:
    """Calculate overall signal accuracy across all stocks."""
    total = 0
    correct = 0
    by_stock = {}

    for ticker, entries in history.items():
        resolved = [e for e in entries if e.get("outcome") not in (None, "PENDING")]
        stock_correct = sum(1 for e in resolved if e.get("signal_correct"))
        if resolved:
            by_stock[ticker] = {
                "total": len(resolved),
                "correct": stock_correct,
                "accuracy": round(stock_correct / len(resolved) * 100, 1),
            }
            total += len(resolved)
            correct += stock_correct

    overall = round(correct / total * 100, 1) if total > 0 else 0
    return {
        "overall_accuracy": overall,
        "total_signals": total,
        "correct_signals": correct,
        "by_stock": by_stock,
    }


def get_stock_history_table(ticker: str, history: dict) -> list:
    """Get last 30 days of history for a stock as a list of dicts."""
    entries = history.get(ticker, [])
    return list(reversed(entries[-30:]))
