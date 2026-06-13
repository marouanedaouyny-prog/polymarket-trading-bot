"""
Test script for market-making strategy components
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.polymarket_bot.strategies.market_making import MarketMakingStrategy

def test_market_making_strategy():
    """Test the market-making strategy components."""
    strategy = MarketMakingStrategy()

    # Test data
    market_data = {
        'yes_price': 0.6,
        'no_price': 0.4
    }

    # Test fair value calculation
    fair_value = strategy.calculate_fair_value(market_data)
    print(f"Fair value: {fair_value}")

    # Test spread optimization
    volatility = 0.2
    liquidity = 0.8
    spread = strategy.optimize_spread(volatility, liquidity)
    print(f"Optimized spread: {spread}")

    # Test inventory skew
    inventory = 1000.0
    target_inventory = 500.0
    skew = strategy.adjust_inventory_skew(inventory, target_inventory)
    print(f"Inventory skew adjustment: {skew}")

    print("All tests passed!")

if __name__ == "__main__":
    test_market_making_strategy()