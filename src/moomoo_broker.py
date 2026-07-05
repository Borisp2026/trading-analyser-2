"""Moomoo Broker Wrapper — Paper and Live modes
Paper mode: works without futu-api (uses agent_trades.json)
Live mode:  requires futu-api + OpenD running locally
            pip install futu-api
"""
import os, json
from datetime import datetime

MODE = os.environ.get("TRADING_MODE", "PAPER")  # PAPER or LIVE


class PaperBroker:
    """Simulates order execution. No real money. No API needed."""
    def __init__(self, capital=1000.0):
        self.capital = capital
        self.positions = {}
        self.order_log = []

    def buy(self, ticker, price, quantity):
        cost = price * quantity
        if cost > self.capital:
            return {"ok": False, "error": f"Insufficient capital (${self.capital:.2f} < ${cost:.2f})"}
        self.capital -= cost
        self.positions[ticker] = {"qty": quantity, "entry": price, "cost": cost}
        order = {"time": datetime.now().isoformat(), "action": "BUY",
                 "ticker": ticker, "price": price, "qty": quantity, "cost": cost}
        self.order_log.append(order)
        print(f"[PAPER] BUY {quantity} x {ticker} @ ${price:.3f} = ${cost:.2f}")
        return {"ok": True, "order": order}

    def sell(self, ticker, price):
        pos = self.positions.get(ticker)
        if not pos:
            return {"ok": False, "error": f"{ticker} not in positions"}
        proceeds = price * pos["qty"]
        pnl = proceeds - pos["cost"]
        self.capital += proceeds
        del self.positions[ticker]
        order = {"time": datetime.now().isoformat(), "action": "SELL",
                 "ticker": ticker, "price": price, "qty": pos["qty"],
                 "proceeds": proceeds, "pnl": round(pnl, 2)}
        self.order_log.append(order)
        print(f"[PAPER] SELL {pos['qty']} x {ticker} @ ${price:.3f} | P&L ${pnl:+.2f}")
        return {"ok": True, "order": order}

    def get_positions(self): return self.positions
    def get_capital(self):   return round(self.capital, 2)


class LiveBroker:
    """
    Live broker via Moomoo OpenAPI.
    Requires: pip install futu-api
    Requires: OpenD gateway running on localhost:11111
    Requires: Moomoo account + API permissions enabled in app settings.

    Setup steps:
    1. Download OpenD from https://www.moomoo.com/download/OpenAPI
    2. Run OpenD, log in with your Moomoo credentials
    3. Enable API trading in Moomoo app: Me > Settings > API Settings
    4. Set TRADING_MODE=LIVE in environment
    """
    def __init__(self, host='127.0.0.1', port=11111):
        try:
            import futu
            self.futu = futu
            self.quote_ctx = futu.OpenQuoteContext(host=host, port=port)
            self.trade_ctx = futu.OpenSecTradeContext(
                filter_trdmarket=futu.TrdMarket.AU,  # AU for ASX, US for NASDAQ
                host=host, port=port
            )
            print("[LIVE] Connected to OpenD")
        except ImportError:
            raise RuntimeError("futu-api not installed. Run: pip install futu-api")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to OpenD: {e}\nIs OpenD running on {host}:{port}?")

    def buy(self, ticker, price, quantity):
        # Convert ticker format: EOS.AX → HK.EOS (Futu uses different codes for AU)
        # For ASX: use SZ.TICKER or AU.TICKER format
        code = f"AU.{ticker.replace('.AX','')}"
        ret, data = self.trade_ctx.place_order(
            price=price, qty=quantity, code=code,
            trd_side=self.futu.TrdSide.BUY,
            order_type=self.futu.OrderType.NORMAL,
            trd_env=self.futu.TrdEnv.REAL
        )
        if ret == 0:
            print(f"[LIVE] BUY order placed: {quantity} x {ticker} @ ${price:.3f}")
            return {"ok": True, "order_id": data["order_id"].iloc[0]}
        return {"ok": False, "error": data}

    def sell(self, ticker, quantity, price):
        code = f"AU.{ticker.replace('.AX','')}"
        ret, data = self.trade_ctx.place_order(
            price=price, qty=quantity, code=code,
            trd_side=self.futu.TrdSide.SELL,
            order_type=self.futu.OrderType.NORMAL,
            trd_env=self.futu.TrdEnv.REAL
        )
        if ret == 0:
            return {"ok": True, "order_id": data["order_id"].iloc[0]}
        return {"ok": False, "error": data}

    def get_positions(self):
        ret, data = self.trade_ctx.position_list_query()
        if ret == 0:
            return data.to_dict('records')
        return []

    def get_capital(self):
        ret, data = self.trade_ctx.accinfo_query()
        if ret == 0:
            return float(data["cash"].iloc[0])
        return 0.0

    def close(self):
        self.quote_ctx.close()
        self.trade_ctx.close()


def get_broker(capital=1000.0):
    """Factory — returns Paper or Live broker based on TRADING_MODE env var."""
    if MODE == "LIVE":
        print("[BROKER] Live mode — connecting to OpenD...")
        return LiveBroker()
    print("[BROKER] Paper mode — simulated trades only")
    return PaperBroker(capital=capital)
