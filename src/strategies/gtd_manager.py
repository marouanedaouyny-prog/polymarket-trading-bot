"""
GTD (Good-Till-Date) auto-expire functionality for orders around market catalysts.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import os

class GTDManager:
    """Manages GTD (Good-Till-Date) auto-expire functionality."""

    def __init__(self):
        """Initialize the GTD manager."""
        self.orders = {}  # Dictionary to track orders with their expiry times

    def add_order(self, order_id: str, expiry_time: datetime):
        """Add an order with its expiry time."""
        self.orders[order_id] = expiry_time

    def check_expired_orders(self) -> List[str]:
        """Check for expired orders and return their IDs."""
        current_time = datetime.now()
        expired_orders = []

        # Find all expired orders
        for order_id, expiry_time in list(self.orders.items()):
            if current_time >= expiry_time:
                expired_orders.append(order_id)
                # Remove expired order from tracking
                del self.orders[order_id]

        return expired_orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order if it exists."""
        if order_id in self.orders:
            del self.orders[order_id]
            # In a real implementation, we would call the API to cancel the order
            print(f"Cancelled order {order_id}")
            return True
        return False

    def get_order_expiry(self, order_id: str) -> datetime:
        """Get the expiry time for an order."""
        return self.orders.get(order_id, None)

# Global GTD manager instance
gtd_manager = GTDManager()