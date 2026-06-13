"""
Paper trading script for testing strategies without live capital.
"""

import asyncio
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the real src root to Python path so top-level packages resolve.
SRC_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SRC_ROOT))

from execution.order_manager import OrderManager
from strategies.market_making import MarketMakingStrategy


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _build_synthetic_market(previous_yes: float) -> dict:
    """
    Create synthetic market values around the previous price.
    Keeps prices in a realistic [0.01, 0.99] range for simulation.
    """
    movement = random.uniform(-0.02, 0.02)
    yes_price = min(0.99, max(0.01, previous_yes + movement))
    no_price = min(0.99, max(0.01, 1.0 - yes_price + random.uniform(-0.005, 0.005)))
    liquidity = random.uniform(0.4, 0.95)
    return {
        "yes_price": yes_price,
        "no_price": no_price,
        "liquidity": liquidity,
    }


async def run_paper_trading():
    """Run the bot in paper trading mode."""
    load_dotenv(PROJECT_ROOT / ".env")

    # Safety defaults: paper mode only.
    os.environ["TRADING_MODE"] = "paper"
    os.environ.setdefault("ENABLE_LIVE_TRADING", "false")

    iterations = _int_env("PAPER_ITERATIONS", 10)
    interval_seconds = _float_env("PAPER_INTERVAL_SECONDS", 1.0)
    order_size = _float_env("PAPER_ORDER_SIZE", 10.0)
    market_id = os.getenv("PAPER_MARKET_ID", "SIM_MARKET_001")

    strategy = MarketMakingStrategy()
    execution = OrderManager(mode="paper")

    print("Starting paper trading mode (safe simulation)")
    print(
        "Config: "
        f"iterations={iterations}, interval={interval_seconds}s, "
        f"order_size={order_size}, market_id={market_id}"
    )

    yes_price = 0.50

    for tick in range(1, iterations + 1):
        market_data = _build_synthetic_market(yes_price)
        yes_price = market_data["yes_price"]

        fair_value = strategy.calculate_fair_value(market_data)
        volatility = abs(market_data["yes_price"] - (1 - market_data["no_price"]))
        spread = strategy.optimize_spread(
            volatility=volatility,
            liquidity=market_data["liquidity"],
            volume=1000.0,
            market_depth=5000.0,
        )

        bid = round(max(0.01, fair_value - spread / 2), 4)
        ask = round(min(0.99, fair_value + spread / 2), 4)

        execution.place_order(
            {
                "market_id": market_id,
                "side": "buy",
                "price": bid,
                "size": order_size,
                "tick": tick,
            }
        )
        execution.place_order(
            {
                "market_id": market_id,
                "side": "sell",
                "price": ask,
                "size": order_size,
                "tick": tick,
            }
        )

        simulated_fill = random.choice([-1, 0, 1]) * (order_size * 0.1)
        inventory = execution.update_inventory(simulated_fill)

        print(
            f"[tick {tick:02d}] yes={market_data['yes_price']:.4f} "
            f"no={market_data['no_price']:.4f} fair={fair_value:.4f} "
            f"bid={bid:.4f} ask={ask:.4f} inventory={inventory:.2f}"
        )

        await asyncio.sleep(interval_seconds)

    print("Paper trading session completed.")
    print(f"Simulated open orders: {len(execution.open_orders)}")
    print(f"Final simulated inventory: {execution.inventory:.2f}")


if __name__ == "__main__":
    asyncio.run(run_paper_trading())
