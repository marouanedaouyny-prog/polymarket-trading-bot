"""
Order execution module for managing trades and inventory.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4


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

    def _live_trading_enabled(self) -> bool:
        """Return True only when live mode is explicitly enabled."""
        return (
            self.mode == "live"
            and os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        )

    def place_order(self, order_details: dict) -> bool:
        """
        Place an order with proper risk controls.
        In paper mode, this records a simulated order and does not hit any exchange.
        """
        order = dict(order_details)
        order_id = order.get("order_id", f"ord_{uuid4().hex[:12]}")
        order["order_id"] = order_id
        order["created_at"] = datetime.utcnow().isoformat() + "Z"
        order["mode"] = self.mode

        if self._live_trading_enabled():
            # Live adapter is not wired in this repo yet. Keep behavior safe.
            order["status"] = "live_not_implemented"
            print(
                f"[ORDER_MANAGER] Live mode enabled but no live adapter configured. "
                f"Order {order_id} was not submitted."
            )
            return False

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
        Apply immediate simulated fill into position and realized PnL accounting.
        Position qty convention:
        - positive: long
        - negative: short
        """
        market_id = str(order.get("market_id", "UNKNOWN"))
        side = str(order.get("side", "")).lower()
        size = float(order.get("size", 0.0))
        price = float(order.get("price", 0.0))
        if size <= 0 or price <= 0:
            return

        pos = self.positions.get(market_id, {"qty": 0.0, "avg_price": 0.0})
        qty = float(pos["qty"])
        avg = float(pos["avg_price"])

        if side == "buy":
            if qty < 0:
                close_qty = min(size, abs(qty))
                pnl = (avg - price) * close_qty  # short close
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
                pnl = (price - avg) * close_qty  # long close
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
