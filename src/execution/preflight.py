"""
Execution preflight — validates every live order before it reaches the CLOB
adapter. Provides tick/size/price validation, slippage and deadline controls,
and redacted exception handling. Fixes clob_adapter.py gaps: no preflight
simulation, no price/size/tick validation, no slippage/deadline controls,
no comprehensive exception redaction.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


@dataclass
class PreflightResult:
    allowed: bool
    reason: str
    order: Dict[str, Any]
    simulated_fill: Optional[Dict[str, Any]] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(tz=timezone.utc).isoformat()


class PreflightValidator:
    def __init__(
        self,
        max_slippage_bps: int = 50,
        order_deadline_seconds: int = 60,
        min_order_size_usd: float = 1.0,
        max_order_size_usd: float = 500.0,
        tick_size: float = 0.01,
    ) -> None:
        self.max_slippage_bps = max_slippage_bps
        self.order_deadline_seconds = order_deadline_seconds
        self.min_order_size_usd = min_order_size_usd
        self.max_order_size_usd = max_order_size_usd
        self.tick_size = tick_size

    def validate(
        self,
        market_id: str,
        side: str,
        price: float,
        size: float,
        mid_price: Optional[float] = None,
    ) -> PreflightResult:
        """
        Preflight check for a live order. Returns allowed=False with a reason
        when any check fails. Never raises; exceptions are caught and redacted.
        """
        order = {
            "market_id": market_id,
            "side": side.lower(),
            "price": price,
            "size": size,
        }

        try:
            # 1. Presence / type checks
            if not market_id or not str(market_id).strip():
                return PreflightResult(False, "missing market_id", order)

            if side.lower() not in ("buy", "sell"):
                return PreflightResult(False, f"invalid side: {side}", order)

            try:
                price_d = Decimal(str(price))
                size_d = Decimal(str(size))
            except (InvalidOperation, ValueError, TypeError):
                return PreflightResult(False, "price/size not numeric", order)

            if price_d <= 0 or size_d <= 0:
                return PreflightResult(False, "price and size must be positive", order)

            # 2. Tick-size validation (price must align to tick)
            if self.tick_size > 0:
                tick = Decimal(str(self.tick_size))
                remainder = price_d % tick
                if remainder != 0:
                    return PreflightResult(
                        False,
                        f"price {price} not aligned to tick {self.tick_size}",
                        order,
                    )

            # 3. Size limits (dedicated limited wallet: per-order cap)
            notional = float(price_d * size_d)
            if notional < self.min_order_size_usd:
                return PreflightResult(
                    False, f"notional {notional:.2f} < min {self.min_order_size_usd}", order
                )
            if notional > self.max_order_size_usd:
                return PreflightResult(
                    False, f"notional {notional:.2f} > max {self.max_order_size_usd}", order
                )

            # 4. Slippage check against mid price when provided
            slippage_bps = 0.0
            if mid_price is not None and mid_price > 0:
                mid_d = Decimal(str(mid_price))
                if side.lower() == "buy":
                    slippage_bps = float((price_d - mid_d) / mid_d * 10000)
                else:
                    slippage_bps = float((mid_d - price_d) / mid_d * 10000)
                if slippage_bps > self.max_slippage_bps:
                    return PreflightResult(
                        False,
                        f"slippage {slippage_bps:.0f}bps > max {self.max_slippage_bps}bps",
                        order,
                    )

            # 5. Deadline: order must be placed within deadline window
            order["deadline_at"] = time.time() + self.order_deadline_seconds

            # 6. Simulated fill estimate (no exchange call)
            simulated_fill = {
                "fill_pct": 1.0,
                "expected_price": float(price_d),
                "slippage_bps": slippage_bps,
            }

            return PreflightResult(
                True,
                "preflight passed",
                order,
                simulated_fill=simulated_fill,
            )

        except Exception as exc:
            # Redact exceptions before they reach logs/return path.
            return PreflightResult(
                False,
                f"preflight error: {type(exc).__name__}",
                order,
            )
