"""
Live Trading Runner
Uses existing API credentials from config/.env
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

for proxy_var in (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
):
    os.environ.pop(proxy_var, None)

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.trading.live_trading import TradingSession


def run_live_trading(starting_balance: float = 500, dry_run: bool = True):
    """Run live trading setup with the configured Polymarket credentials."""

    api_key = os.getenv("POLYMARKET_API_KEY", "")
    api_secret = os.getenv("POLYMARKET_API_SECRET", "")
    api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE", "")
    wallet_address = os.getenv("POLYMARKET_WALLET_ADDRESS", "")
    private_key = os.getenv("PRIVATE_KEY", "")
    allow_real_orders = os.getenv("POLYMARKET_ALLOW_REAL_ORDERS", "false").lower() == "true"

    print("=" * 60)
    print("POLYMARKET LIVE TRADING")
    print("=" * 60)

    if not api_key or not api_secret or not api_passphrase:
        print("ERROR: API credentials not found!")
        print("Please check config/.env")
        return None

    print(f"API Key: {api_key[:10]}...")
    print(f"Wallet: {wallet_address}")
    print(f"Starting Balance: ${starting_balance}")
    print(f"Mode: {'DRY RUN (paper)' if dry_run else 'LIVE TRADING'}")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE] - No real money will be used\n")
        mode = "paper"
    else:
        missing = []
        if not private_key:
            missing.append("PRIVATE_KEY")
        if not wallet_address:
            missing.append("POLYMARKET_WALLET_ADDRESS")
        if not allow_real_orders:
            missing.append("POLYMARKET_ALLOW_REAL_ORDERS=true")

        if missing:
            print("\nERROR: Live order execution is not enabled.")
            print("Missing: " + ", ".join(missing))
            return None

        print("\n[LIVE MODE] - Real orders are enabled by config\n")
        mode = "live"

    session = TradingSession(
        starting_balance=starting_balance,
        mode=mode,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        private_key=private_key,
    )

    balance_info = session.executor.get_balance()
    print(f"Account Status: {balance_info}")

    max_position_pct = float(os.getenv("MAX_POSITION_SIZE", 0.15))
    daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT", 0.05))
    max_consecutive_losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))

    print("\nRisk Parameters:")
    print(f"  Max Position: {max_position_pct*100}%")
    print(f"  Daily Loss Limit: {daily_loss_limit*100}%")
    print(f"  Max Consecutive Losses: {max_consecutive_losses}")

    print("\n" + "=" * 60)
    print("Trading session created successfully!")
    print("=" * 60)

    return session


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Live Trading Runner")
    parser.add_argument("--balance", type=float, default=500, help="Starting balance")
    parser.add_argument("--live", action="store_true", help="Run in live mode (not dry run)")

    args = parser.parse_args()

    session = run_live_trading(
        starting_balance=args.balance,
        dry_run=not args.live,
    )

    if session:
        print(f"\nSession ready. Current balance: ${session.balance}")
