"""
Test script for enhanced spread optimizer functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.polymarket_bot.strategies.market_making import MarketMakingStrategy

def test_spread_optimizer():
    """Test the enhanced spread optimizer."""
    strategy = MarketMakingStrategy()

    # Test with different market conditions
    print("Testing spread optimizer with different market conditions:")

    # Low volatility, high liquidity
    spread1 = strategy.optimize_spread(volatility=0.1, liquidity=0.9, volume=1000000, market_depth=100000)
    print(f"Low volatility, high liquidity: {spread1}")

    # High volatility, low liquidity
    spread2 = strategy.optimize_spread(volatility=0.9, liquidity=0.1, volume=10000, market_depth=5000)
    print(f"High volatility, low liquidity: {spread2}")

    # Medium conditions
    spread3 = strategy.optimize_spread(volatility=0.5, liquidity=0.5, volume=500000, market_depth=50000)
    print(f"Medium conditions: {spread3}")

    print("Spread optimizer tests completed!")

if __name__ == "__main__":
    test_spread_optimizer()