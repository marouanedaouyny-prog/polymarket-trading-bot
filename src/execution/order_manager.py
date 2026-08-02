"""
Order execution module for managing trades and inventory.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class OrderManager:
    """Order execution and inventory management."""

    def __init__(self, mode: Optional[str] = None):
        """Initialize order manager."""
        env_mode = os.getenv("TRADING_MODE", "paper")
        self.mode = (mode or env_mode).lower()
        self.inventory = 0.0
        self.open_orders: List[Dict] = []
        self.order_history: List[Dict] = []
        self.positions: Dict[str, Dict[str, float]] = {}
        self.realized_pnl: float = 0.0
        self.consecutive_losing_closes: int = 0
        self.total_closed_trades: int = 0
        self.winning_closed_trades: int = 0

        # [LATENCY] Simulated exchange latency (seconds)
        self.simulated_latency = float(os.getenv("EXCHANGE_LATENCY", "0.5"))

        # [LIVE ADAPTER] Initialize live execution adapter only when live trading is requested.
        self.live_adapter = None
        if self.mode == "live" and os.getenv("POLYMARKET_ALLOW_REAL_ORDERS", "false").lower() == "true":
            try:
                from .clob_adapter import PolymarketCLOBAdapter
                self.live_adapter = PolymarketCLOBAdapter()
            except ImportError:
                self.live_adapter = None

    def _live_trading_enabled(self) -> bool:
        """Return True only when live mode is explicitly enabled and adapter is ready."""
        return (
            self.mode == "live"
            and os.getenv("POLYMARKET_ALLOW_REAL_ORDERS", "false").lower() == "true"
            and self.live_adapter is not None
            and self.live_adapter.is_available
        )

    def place_order(self, order_details: dict) -> bool:
        """
        Place an order with proper risk controls.
        - In live mode: uses CLOB adapter to sign and broadcast.
        - In paper mode: records a simulated order with latency.
        """
        order = dict(order_details)
        order_id = order.get("order_id", f"ord_{uuid4().hex[:12]}")
        order["order_id"] = order_id
        order["created_at"] = datetime.utcnow().isoformat() + "Z"
        order["mode"] = self.mode

        if self.mode == "live":
            if self._live_trading_enabled():
                # [LIVE EXECUTION] Execute real trade
                result = self.live_adapter.place_order(
                    market_id=order.get("market_id"),
                    side=order.get("side"),
                    price=order.get("price"),
                    size=order.get("size")
                )
                if result["status"] == "success":
                    order["status"] = "filled" # Or pending depending on result
                    order["exchange_order_id"] = result["order_id"]
                    self._apply_simulated_fill(order) # Sync local state
                    self.order_history.append(order)
                    print(f"[ORDER_MANAGER] LIVE order {order_id} placed successfully.")
                    return True
                else:
                    order["status"] = "error"
                    order["error_message"] = result["message"]
                    print(f"[ORDER_MANAGER] LIVE order {order_id} failed: {result['message']}")
                    return False
            else:
                order["status"] = "blocked"
                print(f"[ORDER_MANAGER] Live mode requested but adapter not ready or blocked by guard.")
                return False

        # [PAPER MODE] With simulated latency
        if self.simulated_latency > 0:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context — schedule sleep without blocking
                    import concurrent.futures as _cf
                    _cf.ThreadPoolExecutor().submit(time.sleep, self.simulated_latency)
                else:
                    time.sleep(self.simulated_latency)
            except RuntimeError:
                time.sleep(self.simulated_latency)

        order["status"] = "simulated"
        self._apply_simulated_fill(order)
        self.open_orders.append(order)
        self.order_history.append(order)
        print(
            f"[ORDER_MANAGER] Simulated order {order_id}: "
            f"{order.get('side')} {order.get('size')} @ {order.get('price')}"
        )
        return True

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        for order in self.open_orders:
            if order.get("order_id") == order_id:
                order["status"] = "cancelled"
                self.open_orders.remove(order)
                self.order_history.append(
                    {
                        "order_id": order_id,
                        "status": "cancelled",
                        "cancelled_at": datetime.utcnow().isoformat() + "Z",
                        "mode": self.mode,
                    }
                )
                return True
        return False

    def update_inventory(self, fill_amount: float) -> float:
        """Update position inventory based on fills."""
        self.inventory += fill_amount
        return self.inventory

    def _record_close_pnl(self, pnl: float):
        """Track realized PnL and loss streak for closed quantity."""
        self.realized_pnl += pnl
        self.total_closed_trades += 1
        if pnl > 0:
            self.winning_closed_trades += 1
            self.consecutive_losing_closes = 0
        elif pnl < 0:
            self.consecutive_losing_closes += 1

    def _apply_simulated_fill(self, order: Dict):
        """
        Apply simulated fill with optional partial-fill support.

        If `order` contains `fill_pct` (0.0–1.0), only that fraction is filled
        immediately; the remainder stays as `status='partial'` in open_orders.
        """
        market_id = str(order.get("market_id", "UNKNOWN"))
        side = str(order.get("side", "")).lower()
        requested = float(order.get("size", 0.0))
        price = float(order.get("price", 0.0))
        fill_pct = float(order.get("fill_pct", 1.0))   # 1.0 = full fill

        if requested <= 0 or price <= 0:
            return

        size = requested * fill_pct
        unfilled = requested - size
        order["filled_size"] = size
        order["unfilled_size"] = unfilled
        order["fill_pct"] = fill_pct
        if unfilled > 0.0001:
            order["status"] = "partial"

        pos = self.positions.get(market_id, {"qty": 0.0, "avg_price": 0.0})
        qty = float(pos["qty"])
        avg = float(pos["avg_price"])

        if side == "buy":
            if qty < 0:
                close_qty = min(size, abs(qty))
                pnl = (avg - price) * close_qty
                self._record_close_pnl(pnl)
                qty += close_qty
                remaining = size - close_qty
                if remaining > 0:
                    qty = remaining
                    avg = price
                elif qty == 0:
                    avg = 0.0
            else:
                new_qty = qty + size
                avg = ((qty * avg) + (size * price)) / new_qty if new_qty > 0 else 0.0
                qty = new_qty

        elif side == "sell":
            if qty > 0:
                close_qty = min(size, qty)
                pnl = (price - avg) * close_qty
                self._record_close_pnl(pnl)
                qty -= close_qty
                remaining = size - close_qty
                if remaining > 0:
                    qty = -remaining
                    avg = price
                elif qty == 0:
                    avg = 0.0
            else:
                abs_qty = abs(qty)
                new_abs_qty = abs_qty + size
                avg = ((abs_qty * avg) + (size * price)) / new_abs_qty if new_abs_qty > 0 else 0.0
                qty = -new_abs_qty

        self.positions[market_id] = {"qty": qty, "avg_price": avg}
        self.inventory = sum(abs(v["qty"]) for v in self.positions.values())

    def reconcile_positions(self, exchange_positions: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Reconcile local position book against the exchange's authoritative state.

        exchange_positions: {market_id: {"qty": float, "avg_price": float}}

        Returns a dict of discrepancies: {market_id: {"local": ..., "exchange": ..., "delta": ...}}
        """
        discrepancies = {}
        all_markets = set(self.positions) | set(exchange_positions)
        for mid in all_markets:
            local = self.positions.get(mid, {"qty": 0.0, "avg_price": 0.0})
            exchange = exchange_positions.get(mid, {"qty": 0.0, "avg_price": 0.0})
            delta = exchange["qty"] - local["qty"]
            if abs(delta) > 1e-8:
                discrepancies[mid] = {
                    "local_qty": local["qty"],
                    "exchange_qty": exchange["qty"],
                    "delta": delta,
                }
                # Sync local state to exchange truth
                self.positions[mid] = exchange
        if discrepancies:
            logger.warning(f"Position reconciliation found {len(discrepancies)} discrepancies: {discrepancies}")
            self.inventory = sum(abs(v["qty"]) for v in self.positions.values())
        return discrepancies
