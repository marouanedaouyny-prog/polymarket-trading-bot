"""
Live execution adapter for Polymarket CLOB using official SDK.
"""

import os
import time
import logging
from typing import Dict, Optional, Any
from decimal import Decimal

from polymarket import SecureClient, PRODUCTION, OrderSide, OrderType, MarketOrderType
from polymarket.models import MakerOrder, OrderPostStatus

logger = logging.getLogger(__name__)

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
        """
        if not self.client:
            return {"status": "error", "message": "Live client not initialized"}

        try:
            # Convert string side to SDK Enum
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # Map order types
            # For Polymarket CLOB, we typically use GTC (Good Till Cancelled) or FOK
            # Default to GTC for limit orders

            # Create the order
            # Note: Size must be formatted correctly for the SDK (often Decimal or specific precision)
            resp = self.client.create_order(
                token_id=market_id,
                price=price,
                size=size,
                side=order_side
            )

            if resp and hasattr(resp, 'order_id'):
                logger.info(f"Live order placed: {resp.order_id}")
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
            logger.error(f"Exception during live order placement: {e}")
            return {"status": "error", "message": str(e)}

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
