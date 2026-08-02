"""
Sample trading strategy for backtesting demonstration.

This strategy implements a simple mean-reversion approach:
- Buy when price is below moving average
- Sell when price is above moving average
"""

from typing import List, Dict
from datetime import datetime
import numpy as np


def mean_reversion_strategy(
    current_time: datetime,
    current_balance: float,
    historical_data: Dict
) -> List[Dict]:
    """
    Simple mean reversion strategy.

    Args:
        current_time: Current simulation time
        current_balance: Available balance
        historical_data: Market historical data

    Returns:
        List of trade decisions
    """
    decisions = []

    # Simple strategy: trade first available market
    for market_id, market_data in historical_data.items():
        # Find data at current time
        for entry in market_data:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= current_time:
                price = entry['price']

                # Calculate simple moving average (last 10 entries)
                prices = []
                for e in reversed(market_data[:10]):
                    prices.append(e['price'])

                if prices:
                    sma = np.mean(prices)
                    std = np.std(prices)

                    # Mean reversion logic
                    if price < sma - std:  # Buy signal
                        amount = min(current_balance * 0.1, 100)  # Risk 10% of balance
                        decisions.append({
                            'market_id': market_id,
                            'price': price,
                            'amount': amount,
                            'side': 'buy'
                        })
                    elif price > sma + std:  # Sell signal
                        # For sell, we need to have position (simplified)
                        decisions.append({
                            'market_id': market_id,
                            'price': price,
                            'amount': amount,
                            'side': 'sell'
                        })
                break

    return decisions


if __name__ == "__main__":
    print("Sample mean reversion strategy loaded")
    print("Use with BacktestEngine.run_backtest()")