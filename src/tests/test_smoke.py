"""
Smoke test for the Polymarket trading bot.
"""

import pytest
import asyncio
from main import main

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        # Test core imports
        from core import config, logging, settings
        from data.connectors import gamma, clob, websocket
        from data.storage import postgres, redis_cache
        from strategies import market_making
        from risk import limits
        from execution import order_manager
        from telemetry import metrics
        from api import main as api_main
        from api.routers import markets, trades, risk as api_risk, performance

        print("All imports successful")
        assert True
    except Exception as e:
        pytest.fail(f"Import test failed: {e}")

if __name__ == "__main__":
    test_imports()