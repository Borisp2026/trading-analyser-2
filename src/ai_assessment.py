"""AI Assessment — hourly check-in on open paper-trading positions via the
Claude API (Anthropic Messages API).

Advisory only: writes a plain-language read to data/ai_assessment.json,
shown on the dashboard next to the existing Sell button. This never places,
closes, or modifies a trade on its own -- it's a second opinion for a human
to read, the same way the suggested stop/target already sit next to the
Sell button without acting on their own.

Requires ANTHROPIC_API_KEY as a repo secret. If it isn't set, this writes a
disabled-state file and exits cleanly rather than failing the workflow.
"""
import json, os, sys
from datetime import datetime
import pytz
import requests

sys.path.insert(0, os.path.dirname(__file__))
from portfolio import load_portfolio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_ASSESSMENT_FILE = os.path.join(BASE, "data", "ai_assessment.json")
MACRO_FILE = os.path.join(BASE, "data", "macro_gate.json")
AEST = pytz.timezone("Australia/Sydney")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"  # cheap and fast, appropriate for a short periodic read
MAX_TOKENS = 700


def load_macro() -> dict:
    try:
        with open(MACRO_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def get_open_positions() -> list:
    portfolio = load_portfolio()
    return [t for t in portfolio.get("paper_trades", []) if t.get("status") == "open"]


def fetch_live_price(ticker: str):
    """Best-effort live price -- a stale/missing price for one ticker shouldn't
    block the assessment for the rest of the portfolio."""
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period="1d", interval="5m", auto_adjust=True)
        if df is None or len(df) == 0:
            return None
        return round(float(df["Close"].iloc[-1]), 4)
    except Exception:
        return None


def build_prompt(positions: list, macro: dict) -> str:
    lines = []
    for p in positions:
        cur = p.get("current")
        pnl_pct = round((cur - p["buy_price"]) / p["buy_price"] * 100, 2) if cur else None
        lines.append(
            f"- {p['ticker']} ({p['strategy']}): bought ${p['buy_price']}, current "
            f"{'$' + str(cur) if cur is not None else 'unavailable'}, "
            f"stop ${p.get('stop_price') or 'none set'}, target ${p.get('target_price') or 'none set'}, "
            f"unrealized {pnl_pct if pnl_pct is not None else '?'}%, opened {p.get('buy_date','?')}"
        )
    positions_text = "\n".join(lines) if lines else "No open positions right now."
    macro_text = f"Macro deployment gate: {macro.get('zone', 'unknown')} (composite {macro.get('composite', '?')}/100)"
    tickers = [p["ticker"] for p in positions]

    return f"""You are reviewing open PAPER-TRADING positions (simulated, no real money) for a personal ASX/NASDAQ research tool. This is advisory only -- the trader reads this and decides manually; nothing you say executes a trade.

{macro_text}

Open positions:
{positions_text}

Reply with ONLY a JSON object, no other text, in exactly this shape:
{{"per_position": {{"TICKER": "one-line read: is the thesis holding up, getting close to its stop, or worth watching more closely?", ...}}, "portfolio_note": "one short note on concentration, correlated risk, or anything notable about the mix"}}

The per_position object must have exactly one entry per ticker listed above ({', '.join(tickers) if tickers else 'none'}), keyed by that exact ticker string. Keep every line concise and factual -- no hype, no disclaimers about this being simulated (the trader already knows), just a clear-eyed read of what's changed since entry."""


def call_claude(prompt: str) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def run_ai_assessment() -> dict:
    now_iso = datetime.now(AEST).isoformat()

    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY not set -- skipping. Add it as a GitHub repo secret to enable this.")
        out = {"generated_at": now_iso, "enabled": False,
               "note": "ANTHROPIC_API_KEY not configured as a repo secret"}
        with open(AI_ASSESSMENT_FILE, "w") as f:
            json.dump(out, f, indent=2)
        return out

    open_trades = get_open_positions()
    positions = [{
        "ticker": t["ticker"],
        "strategy": (t.get("meta") or {}).get("strategy", "manual"),
        "buy_price": t["buy_price"],
        "current": fetch_live_price(t["ticker"]),
        "stop_price": t.get("stop_price"),
        "target_price": t.get("target_price"),
        "buy_date": t.get("buy_date"),
    } for t in open_trades]

    macro = load_macro()
    prompt = build_prompt(positions, macro)

    assessment_text, error = None, None
    per_position, portfolio_note = {}, None
    try:
        assessment_text = call_claude(prompt)
        # Claude is asked to reply with only JSON, but reads it defensively --
        # a model reply outside the exact shape shouldn't break the whole
        # feature, just fall back to showing assessment_text as plain prose
        # (the format this used before per-position reads existed).
        try:
            parsed = json.loads(assessment_text)
            per_position = parsed.get("per_position") or {}
            portfolio_note = parsed.get("portfolio_note")
        except (json.JSONDecodeError, AttributeError):
            print("AI assessment: response wasn't valid JSON, showing as plain text")
    except Exception as e:
        error = str(e)

    out = {
        "generated_at": now_iso, "enabled": True, "model": MODEL,
        "positions_checked": len(positions),
        "positions": positions,
        # per_position: {ticker: one-line read}, used to annotate the Open Positions
        # table row for that ticker directly. portfolio_note + assessment (raw) stay
        # for the full-text panel -- assessment is kept even when JSON parsing
        # succeeds so nothing that reads the old shape breaks.
        "per_position": per_position, "portfolio_note": portfolio_note,
        "assessment": assessment_text, "error": error,
    }
    with open(AI_ASSESSMENT_FILE, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"AI assessment written: {len(positions)} position(s) checked" + (f" (error: {error})" if error else ""))
    return out


if __name__ == "__main__":
    run_ai_assessment()
