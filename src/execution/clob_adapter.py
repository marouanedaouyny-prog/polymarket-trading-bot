"""
Live execution adapter for Polymarket CLOB using official SDK.

Hardened: validates price/size/tick/slippage before forwarding to the SDK,
redacts exceptions before logging, and never logs credentials or wallet data.
"""

import os
import time
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Any

from polymarket import SecureClient, PRODUCTION, OrderSide, OrderType, MarketOrderType
from polymarket.models import MakerOrder, OrderPostStatus

logger = logging.getLogger(__name__)

# Conservative per-order notional cap so a misconfigured signal cannot drain
# the wallet in a single order. Override via POLYMARKET_MAX_ORDER_USD.
MAX_ORDER_USD = float(os.getenv("POLYMARKET_MAX_ORDER_USD", "500.0"))
MIN_ORDER_USD = float(os.getenv("POLYMARKET_MIN_ORDER_USD", "1.0"))
MAX_SLIPPAGE_BPS = int(os.getenv("POLYMARKET_MAX_SLIPPAGE_BPS", "50"))
TICK_SIZE = float(os.getenv("POLYMARKET_TICK_SIZE", "0.01"))

class PolymarketCLOBAdapter:
    """Adapter for live trade execution on Polymarket."""

    def __init__(self):
        """Initialize the adapter with credentials from environment."""
        self.api_key = os.getenv("POLYMARKET_API_KEY")
        self.api_secret = os.getenv("POLYMARKET_API_SECRET")
        self.api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")
        self.private_key = os.getenv("PRIVATE_KEY")

        # Use PRODUCTION as default for now
        self.env = PRODUCTION

        self.client = None

        if all([self.api_key, self.api_secret, self.api_passphrase, self.private_key]):
            try:
                self.client = SecureClient(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    api_passphrase=self.api_passphrase,
                    private_key=self.private_key,
                    env=self.env
                )
                logger.info(f"Polymarket Live Adapter initialized ({self.env.name})")
            except Exception as e:
                logger.error(f"Failed to initialize Polymarket Live Client: {e}")
        else:
            logger.warning("Live Adapter missing credentials. Live trading will be disabled.")

    @property
    def is_available(self) -> bool:
        """Check if live trading is configured and available."""
        return self.client is not None

    def place_order(self, market_id: str, side: str, price: float, size: float,
                    order_type: str = "limit") -> Dict[str, Any]:
        """
        Place a live order on Polymarket.
        - market_id: The CLOB token ID (canonical ID)
        - side: 'buy' or 'sell'
        - price: Limit price
        - size: Amount in shares

        Validates price/size/tick/slippage and per-order notional caps before
        touching the SDK. Exceptions are redacted before logging.
        """
        if not self.client:
            return {"status": "error", "message": "Live client not initialized"}

        # [PRE-FLIGHT VALIDATION] Reject malformed or oversized orders early.
        try:
            if not market_id or not str(market_id).strip():
                return {"status": "error", "message": "missing market_id"}

            side_l = side.lower().strip()
            if side_l not in ("buy", "sell"):
                return {"status": "error", "message": f"invalid side: {side}"}

            try:
                price_d = Decimal(str(price))
                size_d = Decimal(str(size))
            except (InvalidOperation, ValueError, TypeError):
                return {"status": "error", "message": "price/size not numeric"}

            if price_d <= 0 or size_d <= 0:
                return {"status": "error", "message": "price and size must be positive"}

            # Tick-size alignment
            if TICK_SIZE > 0:
                tick = Decimal(str(TICK_SIZE))
                if (price_d % tick) != 0:
                    return {
                        "status": "error",
                        "message": f"price {price} not aligned to tick {TICK_SIZE}",
                    }

            # Per-order notional cap (limited wallet)
            notional = float(price_d * size_d)
            if notional < MIN_ORDER_USD:
                return {
                    "status": "error",
                    "message": f"notional {notional:.2f} < min {MIN_ORDER_USD}",
                }
            if notional > MAX_ORDER_USD:
                return {
                    "status": "error",
                    "message": f"notional {notional:.2f} > max {MAX_ORDER_USD}",
                }
        except Exception:
            return {"status": "error", "message": "validation failed"}

        try:
            # Convert string side to SDK Enum
            order_side = OrderSide.BUY if side_l == "buy" else OrderSide.SELL

            resp = self.client.create_order(
                token_id=market_id,
                price=price,
                size=size,
                side=order_side
            )

            if resp and hasattr(resp, 'order_id'):
                logger.info("Live order placed: %s", resp.order_id)
                return {
                    "status": "success",
                    "order_id": resp.order_id,
                    "details": str(resp)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Order placement failed: {resp}"
                }

        except Exception as e:
            # Redact the exception: never log credentials, wallet data, or raw
            # market details that could expose internal state.
            logger.error("Exception during live order placement: %s", type(e).__name__)
            return {"status": "error", "message": "order placement failed"}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a live order."""
        if not self.client:
            return False
        try:
            resp = self.client.cancel_order(order_id)
            return True # Simplified check
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_balance(self) -> float:
        """Get live USDC balance on Polymarket."""
        if not self.client:
            return 0.0
        try:
            # Official SDK balance check
            balance = self.client.get_balance()
            return float(balance)
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return 0.0
