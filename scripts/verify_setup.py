#!/usr/bin/env python3
"""
Setup verification script for the Polymarket trading bot.
This script checks if all required components are properly configured.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

# Add the real project src directory so package imports resolve correctly.
sys.path.insert(0, str(SRC_DIR))

# Load env from the project root first, then fall back to local script/config files.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")


async def verify_setup():
    """Verify that all required components are properly set up."""
    print("Verifying Polymarket trading bot setup...")

    # Check if required environment variables are set
    print("1. Checking environment variables...")
    required_vars = ["POLYMARKET_API_KEY", "POLYMARKET_API_SECRET", "POLYMARKET_API_PASSPHRASE"]
    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        print(f"   Missing environment variables: {missing_vars}")
        print("   Please set these in your .env file")
        return False

    print("   [OK] Environment variables are set")

    # Try to import all modules
    print("2. Testing module imports...")
    try:
        from data.connectors.clob import CLOBConnector
        from data.connectors.gamma import PolymarketAPI

        _ = CLOBConnector, PolymarketAPI
        print("   [OK] Data connectors imported successfully")
    except Exception as e:
        print(f"   Error importing data connectors: {e}")
        return False

    try:
        from strategies.market_making import MarketMakingStrategy

        _ = MarketMakingStrategy
        print("   [OK] Strategy modules imported successfully")
    except Exception as e:
        print(f"   Error importing strategy modules: {e}")
        return False

    # Check database libraries
    print("3. Testing database libraries...")
    try:
        import asyncpg
        import redis

        _ = asyncpg, redis
        print("   [OK] Database libraries available")
    except ImportError as e:
        print(f"   Missing database libraries: {e}")
        return False

    print("All setup checks passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_setup())
    if success:
        print("Setup verification completed successfully!")
    else:
        print("Setup verification failed. Please check the errors above.")
