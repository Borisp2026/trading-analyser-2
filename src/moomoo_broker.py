"""Moomoo Broker Wrapper — Paper and Live modes
Paper mode: works without futu-api (uses agent_trades.json)
Live mode:  requires futu-api + OpenD running locally
            pip install futu-api
"""
import os, json, time
from datetime import datetime, timedelta

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

    NOTE: fill-confirmation / retry / reconcile logic below has not been
    exercised against a live OpenD connection. Test it thoroughly (paper
    account first) before this ever runs with TRADING_MODE=LIVE.
    """
    FILL_POLL_TIMEOUT_S = 30
    FILL_POLL_INTERVAL_S = 1.5

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
        return self._place_and_confirm(code, ticker, price, quantity, self.futu.TrdSide.BUY)

    def sell(self, ticker, quantity, price):
        code = f"AU.{ticker.replace('.AX','')}"
        return self._place_and_confirm(code, ticker, price, quantity, self.futu.TrdSide.SELL)

    def _place_and_confirm(self, code, ticker, price, quantity, trd_side):
        side_label = "BUY" if trd_side == self.futu.TrdSide.BUY else "SELL"

        # Idempotency: if a matching order was already submitted recently,
        # don't blindly resubmit — check the broker's own record first.
        existing = self._find_recent_order(code, trd_side, quantity)
        if existing is not None:
            print(f"[LIVE] Skipping duplicate {side_label} {ticker} — order {existing['order_id']} already on record ({existing['order_status']})")
            return self._order_result_from_row(existing)

        try:
            ret, data = self.trade_ctx.place_order(
                price=price, qty=quantity, code=code,
                trd_side=trd_side,
                order_type=self.futu.OrderType.NORMAL,
                trd_env=self.futu.TrdEnv.REAL
            )
        except Exception as e:
            # The call itself failed (e.g. network timeout) — we don't know
            # if the order reached the broker. Check before retrying instead
            # of resubmitting blind, which could double the position.
            print(f"[LIVE] {side_label} order call errored ({e}) — checking broker state before retry")
            existing = self._find_recent_order(code, trd_side, quantity)
            if existing is not None:
                return self._order_result_from_row(existing)
            return {"ok": False, "error": f"order call failed and no matching order found on broker: {e}"}

        if ret != 0:
            return {"ok": False, "error": data}

        order_id = data["order_id"].iloc[0]
        print(f"[LIVE] {side_label} order placed: {quantity} x {ticker} @ ${price:.3f} (order_id={order_id}) — waiting for fill...")
        filled = self._wait_for_fill(order_id)
        if filled is None:
            print(f"[LIVE] WARNING: order {order_id} fill status unresolved after {self.FILL_POLL_TIMEOUT_S}s — check the Moomoo app manually before treating this as filled or unfilled")
            return {"ok": None, "order_id": order_id, "status": "UNRESOLVED"}
        return self._order_result_from_row(filled)

    def _wait_for_fill(self, order_id, timeout_s=None):
        """Poll order_list_query until the order reaches a terminal state
        (FILLED_ALL, CANCELLED_ALL, FAILED) or timeout_s elapses.
        Returns the order row (dict) or None if unresolved — callers must
        treat None as unknown state, not as failure."""
        timeout_s = timeout_s or self.FILL_POLL_TIMEOUT_S
        terminal = {self.futu.OrderStatus.FILLED_ALL, self.futu.OrderStatus.CANCELLED_ALL,
                    self.futu.OrderStatus.FAILED}
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                ret, data = self.trade_ctx.order_list_query(order_id=order_id)
                if ret == 0 and len(data) > 0:
                    row = data.iloc[0].to_dict()
                    if row.get("order_status") in terminal:
                        return row
            except Exception as e:
                print(f"[LIVE] order_list_query error while polling {order_id}: {e}")
            time.sleep(self.FILL_POLL_INTERVAL_S)
        return None

    def _find_recent_order(self, code, trd_side, qty, window_minutes=5):
        """Look for a matching order already on the broker's books, to avoid
        resubmitting after an ambiguous local failure."""
        try:
            ret, data = self.trade_ctx.order_list_query(code=code)
            if ret != 0 or len(data) == 0:
                return None
            cutoff = datetime.now() - timedelta(minutes=window_minutes)
            for _, row in data.iterrows():
                if row.get("trd_side") != trd_side or float(row.get("qty", 0)) != float(qty):
                    continue
                try:
                    created = datetime.strptime(str(row.get("create_time", "")), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if created >= cutoff:
                    return row.to_dict()
        except Exception as e:
            print(f"[LIVE] order_list_query error while checking for duplicates: {e}")
        return None

    def _order_result_from_row(self, row):
        status = row.get("order_status")
        ok = status == self.futu.OrderStatus.FILLED_ALL
        return {
            "ok": ok, "order_id": row.get("order_id"), "status": str(status),
            "dealt_qty": row.get("dealt_qty"), "dealt_avg_price": row.get("dealt_avg_price"),
        }

    def reconcile(self, local_positions: dict) -> dict:
        """Compare the bot's local position book (agent_trades.json's
        open_positions, keyed by ticker) against the broker's actual account
        state. Returns a diff report — does not auto-resolve conflicts,
        since deciding which side is 'truth' needs a human look."""
        broker_rows = self.get_positions()
        broker_by_ticker = {}
        for p in broker_rows:
            code = str(p.get("code", ""))
            ticker = code.split(".")[-1] + ".AX" if "." in code else code
            broker_by_ticker[ticker] = p

        mismatches = []
        for ticker, local_pos in local_positions.items():
            broker_pos = broker_by_ticker.get(ticker)
            local_qty = local_pos.get("qty") if isinstance(local_pos, dict) else None
            if local_qty is None and isinstance(local_pos, dict):
                local_qty = local_pos.get("quantity")
            if broker_pos is None:
                mismatches.append({"ticker": ticker, "issue": "LOCAL_ONLY",
                                    "detail": "bot's local book has this open, broker shows no position"})
                continue
            broker_qty = float(broker_pos.get("qty", 0))
            if local_qty is not None and float(local_qty) != broker_qty:
                mismatches.append({"ticker": ticker, "issue": "QTY_MISMATCH",
                                    "local_qty": local_qty, "broker_qty": broker_qty})

        for ticker in broker_by_ticker:
            if ticker not in local_positions:
                mismatches.append({"ticker": ticker, "issue": "BROKER_ONLY",
                                    "detail": "broker shows an open position the bot's local book doesn't know about"})

        return {"clean": len(mismatches) == 0, "mismatches": mismatches,
                "checked_at": datetime.now().isoformat()}

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
