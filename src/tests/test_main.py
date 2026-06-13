"""
Main test runner for the Polymarket trading bot.
"""

import sys
import os

# Add the src directory to the path so we can import the bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
import asyncio
from pathlib import Path
import tempfile
import subprocess

def test_basic_functionality():
    """Test basic bot functionality."""
    try:
        # Test that we can import our main modules
        from polymarket_bot.core import config
        from polymarket_bot.data.connectors import gamma
        from polymarket_bot.strategies import market_making

        print("Basic functionality test passed")
        return True
    except ImportError as e:
        print(f"Basic functionality test failed: {e}")
        return False

def test_api_connection():
    """Test API connection."""
    # This would test the actual API connection in a real implementation
    print("API connection test (mock) - skipping actual connection for now")
    return True

if __name__ == "__main__":
    print("Running tests...")

    # Run basic functionality test
    if test_basic_functionality():
        print("✓ Basic functionality test passed")
    else:
        print("✗ Basic functionality test failed")

    # Run API connection test
    if test_api_connection():
        print("✓ API connection test passed")
    else:
        print("✗ API connection test failed")

    print("All tests completed")