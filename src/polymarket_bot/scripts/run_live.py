"""
Live trading script for production deployment.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add package root (src/polymarket_bot) to Python path.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PACKAGE_ROOT))


def _is_live_enabled() -> bool:
    return os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"


async def run_live_trading():
    """Run the bot in live trading mode."""
    load_dotenv(PROJECT_ROOT / ".env")

    if not _is_live_enabled():
        print("Refusing to start live trading.")
        print("Set ENABLE_LIVE_TRADING=true in .env only when you are ready.")
        return

    os.environ["TRADING_MODE"] = "live"
    print("Starting live trading mode...")

    # Import here so the safety gate runs before bot startup.
    from main import main as bot_main

    await bot_main()


if __name__ == "__main__":
    asyncio.run(run_live_trading())
