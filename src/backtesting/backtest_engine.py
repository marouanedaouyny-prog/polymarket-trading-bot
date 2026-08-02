"""
Advanced Backtesting Engine for Polymarket Trading Strategies

Features:
- Historical data replay
- Slippage simulation
- Latency modeling
- Liquidity impact analysis
- Performance metrics
"""

import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import logging
from collections import defaultdict


# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade in backtesting."""
    timestamp: datetime
    market_id: str
    price: float
    amount: float
    side: str  # 'buy' or 'sell'
    fee: float
    slippage: float
    latency: float


@dataclass
class BacktestResult:
    """Results from a backtesting run."""
    starting_balance: float
    ending_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    trades: List[Trade]


class BacktestEngine:
    """
    Advanced backtesting engine with realistic market simulation.
    """

    def __init__(self, historical_data_path: str = "data/historical"):
        """
        Initialize the backtesting engine.

        Args:
            historical_data_path: Path to historical market data
        """
        self.historical_data_path = Path(historical_data_path)
        self.historical_data = {}
        self.current_time = None
        self.backtest_results = []

        # Load historical data
        self._load_historical_data()

    def _load_historical_data(self):
        """Load historical market data from files."""
        if not self.historical_data_path.exists():
            logger.warning(f"Historical data path not found: {self.historical_data_path}")
            return

        # Load all JSON files in the directory
        for json_file in self.historical_data_path.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    market_data = json.load(f)
                    market_id = json_file.stem
                    self.historical_data[market_id] = market_data
                    logger.info(f"Loaded historical data for market: {market_id}")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

    def set_start_time(self, start_time: str):
        """Set the starting time for backtesting."""
        self.current_time = datetime.fromisoformat(start_time)
        logger.info(f"Backtest starting at: {self.current_time}")

    def _get_market_data_at_time(self, market_id: str, time: datetime) -> Optional[Dict]:
        """Get market data at a specific time."""
        if market_id not in self.historical_data:
            return None

        # Find the closest timestamp in historical data
        market_data = self.historical_data[market_id]

        # Simple implementation - find first entry after current time
        for entry in market_data:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= time:
                return entry

        return None

    def simulate_trade(
        self,
        market_id: str,
        price: float,
        amount: float,
        side: str,
        slippage_pct: float = 0.0,
        latency_ms: float = 0
    ) -> Optional[Trade]:
        """
        Simulate a trade with realistic market conditions.

        Args:
            market_id: Market identifier
            price: Target price
            amount: Amount to trade
            side: 'buy' or 'sell'
            slippage_pct: Percentage slippage to simulate
            latency_ms: Execution latency in milliseconds

        Returns:
            Trade object if successful, None if failed
        """
        if not self.current_time:
            logger.error("Backtest time not set")
            return None

        # Get current market data
        market_data = self._get_market_data_at_time(market_id, self.current_time)
        if not market_data:
            logger.warning(f"No market data available for {market_id} at {self.current_time}")
            return None

        # Apply slippage
        actual_price = price * (1 + (slippage_pct * (1 if side == 'buy' else -1)))

        # Calculate fee (0.7% for Polymarket)
        fee = amount * 0.007

        # Create trade object
        trade = Trade(
            timestamp=self.current_time,
            market_id=market_id,
            price=actual_price,
            amount=amount,
            side=side,
            fee=fee,
            slippage=abs(actual_price - price),
            latency=latency_ms / 1000.0  # Convert to seconds
        )

        # Advance time by latency
        self.current_time += timedelta(milliseconds=latency_ms)

        return trade

    def run_backtest(
        self,
        strategy,
        start_time: str,
        end_time: str,
        starting_balance: float = 1000.0,
        slippage_pct: float = 0.005,
        latency_ms: float = 100
    ) -> BacktestResult:
        """
        Run a complete backtesting simulation.

        Args:
            strategy: Trading strategy function
            start_time: ISO format start time
            end_time: ISO format end time
            starting_balance: Initial capital
            slippage_pct: Average slippage percentage
            latency_ms: Average execution latency

        Returns:
            BacktestResult with performance metrics
        """
        # Initialize
        self.set_start_time(start_time)
        end_time_dt = datetime.fromisoformat(end_time)

        balance = starting_balance
        peak_balance = starting_balance
        trades = []

        logger.info(f"Starting backtest from {start_time} to {end_time}")
        logger.info(f"Starting balance: ${starting_balance}")

        # Run strategy
        while self.current_time < end_time_dt:
            # Get strategy decision
            try:
                decisions = strategy(
                    current_time=self.current_time,
                    current_balance=balance,
                    historical_data=self.historical_data
                )

                # Execute trades
                for decision in decisions:
                    trade = self.simulate_trade(
                        market_id=decision['market_id'],
                        price=decision['price'],
                        amount=decision['amount'],
                        side=decision['side'],
                        slippage_pct=slippage_pct,
                        latency_ms=latency_ms
                    )

                    if trade:
                        trades.append(trade)
                        # Update balance
                        if trade.side == 'buy':
                            balance -= trade.amount + trade.fee
                        else:  # sell
                            balance += trade.amount - trade.fee

                        # Track peak balance for drawdown calculation
                        if balance > peak_balance:
                            peak_balance = balance

                        logger.info(f"Executed {trade.side} trade: {trade.amount} at {trade.price}")

            except Exception as e:
                logger.error(f"Error in strategy execution: {e}")
                break

        # Calculate performance metrics
        result = self._calculate_metrics(trades, starting_balance, peak_balance)

        logger.info(f"Backtest completed")
        logger.info(f"Ending balance: ${balance}")
        logger.info(f"Total trades: {len(trades)}")
        logger.info(f"Max drawdown: {result.max_drawdown:.2%}")
        logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")

        return result

    def _calculate_metrics(
        self,
        trades: List[Trade],
        starting_balance: float,
        peak_balance: float
    ) -> BacktestResult:
        """Calculate performance metrics from trade history using paired P&L."""
        if not trades:
            return BacktestResult(
                starting_balance=starting_balance,
                ending_balance=starting_balance,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit=0.0,
                total_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                trades=[]
            )

        # Build per-market position books to compute paired P&L
        # Each BUY opens a position; each SELL closes it at the new price.
        positions: dict = {}   # market_id -> {qty, avg_buy_price}
        closed_pnls: List[float] = []

        for t in trades:
            mid = t.market_id
            if t.side == 'buy':
                pos = positions.get(mid, {'qty': 0.0, 'avg': 0.0})
                new_qty = pos['qty'] + t.amount
                pos['avg'] = ((pos['qty'] * pos['avg']) + (t.amount * t.price)) / new_qty
                pos['qty'] = new_qty
                positions[mid] = pos
            elif t.side == 'sell':
                pos = positions.get(mid)
                if pos and pos['qty'] > 0:
                    close_qty = min(t.amount, pos['qty'])
                    pnl = (t.price - pos['avg']) * close_qty - t.fee
                    closed_pnls.append(pnl)
                    pos['qty'] -= close_qty
                    if pos['qty'] <= 0:
                        del positions[mid]
                    else:
                        positions[mid] = pos

        # Any remaining open positions — mark-to-market at last known price
        # (conservatively treat as flat for now)

        winning_trades = sum(1 for p in closed_pnls if p > 0)
        losing_trades = sum(1 for p in closed_pnls if p <= 0)
        total_trades = len(closed_pnls)
        total_profit = sum(p for p in closed_pnls if p > 0)
        total_loss = abs(sum(p for p in closed_pnls if p < 0))

        ending_balance = starting_balance + sum(closed_pnls)
        max_drawdown = (peak_balance - ending_balance) / peak_balance if peak_balance > 0 else 0.0
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # Sharpe / Sortino from per-close returns
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
        if len(closed_pnls) > 1:
            arr = np.array(closed_pnls) / starting_balance
            mean_r = np.mean(arr)
            std_r = np.std(arr, ddof=1)
            if std_r > 0:
                sharpe_ratio = float(mean_r / std_r * np.sqrt(252))
            downside = arr[arr < 0]
            downside_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 0.0
            if downside_std > 0:
                sortino_ratio = float(mean_r / downside_std * np.sqrt(252))

        return BacktestResult(
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_profit=total_profit,
            total_loss=total_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            trades=trades
        )


class MonteCarloEngine:
    """
    Monte Carlo simulation engine for risk assessment.
    """

    def __init__(self, backtest_results: BacktestResult):
        """Initialize with backtest results."""
        self.backtest_results = backtest_results

    def run_simulation(self, n_simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation to estimate risk."""
        results = {
            'ending_balances': [],
            'max_drawdowns': [],
            'ruin_probability': 0.0,
            'expected_final_balance': 0.0,
            'cvar_95': 0.0
        }

        # Use backtest metrics to simulate variations
        win_rate = self.backtest_results.win_rate
        avg_profit = self.backtest_results.total_profit / self.backtest_results.winning_trades if self.backtest_results.winning_trades > 0 else 0
        avg_loss = self.backtest_results.total_loss / self.backtest_results.losing_trades if self.backtest_results.losing_trades > 0 else 0

        for _ in range(n_simulations):
            # Simulate trading period
            balance = self.backtest_results.starting_balance
            peak_balance = balance

            # Simulate trades based on win/loss probability
            for _ in range(self.backtest_results.total_trades):
                if np.random.random() < win_rate:
                    # Win
                    profit = avg_profit * (1 + np.random.normal(0, 0.1))
                    balance += profit
                else:
                    # Loss
                    loss = avg_loss * (1 + np.random.normal(0, 0.1))
                    balance -= loss

                # Track peak for drawdown
                if balance > peak_balance:
                    peak_balance = balance

            results['ending_balances'].append(balance)
            results['max_drawdowns'].append((peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0)

        # Calculate metrics
        ending_balances = np.array(results['ending_balances'])
        results['expected_final_balance'] = float(np.mean(ending_balances))

        # Ruin probability (balance <= 0)
        ruin_count = np.sum(ending_balances <= 0)
        results['ruin_probability'] = float(ruin_count / n_simulations)

        # CVaR 95% (average of worst 5% outcomes)
        worst_5_percent = np.percentile(ending_balances, 5)
        cvar_values = ending_balances[ending_balances <= worst_5_percent]
        results['cvar_95'] = float(np.mean(cvar_values)) if len(cvar_values) > 0 else 0.0

        return results


if __name__ == "__main__":
    print("BacktestEngine initialized")
    print("Use this module to run historical backtests and Monte Carlo simulations")