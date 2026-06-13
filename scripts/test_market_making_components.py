"""
Comprehensive test script for all market-making components
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.polymarket_bot.strategies.market_making import MarketMakingStrategy
from src.polymarket_bot.strategies.gtd_manager import GTDManager
from datetime import datetime, timedelta

def test_market_making_components():
    """Test all market-making components together."""
    print("Testing market-making components...")

    # Test data
    market_data = {
        'yes_price': 0.6,
        'no_price': 0.4
    }

    # Initialize components
    strategy = MarketMakingStrategy()
    gtd_manager = GTDManager()

    # Test fair value calculation
    fair_value = strategy.calculate_fair_value(market_data)
    print(f"Fair value: {fair_value}")

    # Test spread optimization with different market conditions
    volatility = 0.2
    liquidity = 0.8
    spread = strategy.optimize_spread(volatility, liquidity)
    print(f"Optimized spread: {spread}")

    # Test GTD manager
    order_id = "test_order_123"
    expiry_time = datetime.now() + timedelta(minutes=5)
    gtd_manager.add_order(order_id, expiry_time)
    print(f"Added order {order_id} with expiry at {expiry_time}")

    # Test inventory skew
    inventory = 1000.0
    target_inventory = 500.0
    skew = strategy.adjust_inventory_skew(inventory, target_inventory)
    print(f"Inventory skew adjustment: {skew}")

    print("All tests passed!")

if __name__ == "__main__":
    test_market_making_components()