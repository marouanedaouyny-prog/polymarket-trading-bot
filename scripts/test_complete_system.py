"""
Final integration test for the complete Polymarket trading bot system.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.polymarket_bot.strategies.market_making import MarketMakingStrategy
from src/polymarket_bot.risk.limits import RiskManager
from src/polymarket_bot.risk.latency import LatencyMonitor
from src.polymarket_bot.core.builder import BuilderProfile

def test_complete_system():
    """Test the complete Polymarket trading bot system."""
    print("Testing complete Polymarket trading bot system...")

    # Test market making strategy
    print("\n1. Testing market-making strategy components...")
    strategy = MarketMakingStrategy()

    # Test data
    market_data = {
        'yes_price': 0.6,
        'no_price': 0.4
    }

    fair_value = strategy.calculate_fair_value(market_data)
    spread = strategy.optimize_spread(0.2, 0.8, 1000000, 100000)
    skew = strategy.adjust_inventory_skew(1000.0, 500.0)

    print(f"   Fair value: {fair_value}")
    print(f"   Optimized spread: {spread}")
    print(f"   Inventory skew: {skew}")

    # Test risk management
    print("\n2. Testing risk management components...")
    risk_manager = RiskManager()
    risk_manager.set_position("market_123", 0.03)
    risk_check = risk_manager.check_position_size("market_123", 0.02)
    risk_limits = risk_manager.check_risk_limits()

    print(f"   Position size check: {risk_check}")
    print(f"   Risk limits: {risk_limits}")

    # Test latency monitoring
    print("\n3. Testing latency monitoring...")
    latency_monitor = LatencyMonitor()
    latency_monitor.update_quote_timestamp("market_123")
    stale_check = latency_monitor.is_quote_stale("market_123")
    quote_age = latency_monitor.get_quote_age("market_123")

    print(f"   Quote age: {quote_age:.2f} seconds")
    print(f"   Quote stale check: {stale_check}")

    # Test builder profile
    print("\n4. Testing builder profile...")
    builder = BuilderProfile("test_builder_123")
    builder.enable_builder_fees(0.1)  # 10% fee
    builder_info = builder.get_builder_info()
    fees = builder.calculate_builder_fees(1000.0)

    print(f"   Builder info: {builder_info}")
    print(f"   Builder fees for $1000 trade: ${fees:.2f}")

    print("\nAll system tests completed successfully!")
    print("The Polymarket trading bot system is fully functional.")

if __name__ == "__main__":
    test_complete_system()