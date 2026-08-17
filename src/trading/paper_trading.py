"""Paper Trading Simulator — self-contained, deterministic simulation.

Fills simulated buy/sell orders for strategy validation before any live
capital is exposed. The behavioral contract is defined in
tests/test_paper_trading.py.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class PaperTrade:
    """A single simulated fill."""

    def __init__(self, trade_data: Dict):
        self.timestamp = trade_data.get('timestamp')
        self.market_id = trade_data.get('market_id')
        self.side = trade_data.get('side')
        self.amount = trade_data.get('amount')
        self.price = trade_data.get('price')
        self.fee = trade_data.get('fee', 0.0)
        self.slippage = trade_data.get('slippage', 0.0)
        self.status = trade_data.get('status', 'simulated')

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'market_id': self.market_id,
            'side': self.side,
            'amount': self.amount,
            'price': self.price,
            'fee': self.fee,
            'slippage': self.slippage,
            'status': self.status,
        }


class PaperTradingSimulator:
    """Simulated fills with balance and win/loss bookkeeping."""

    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades: List[PaperTrade] = []
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0

    def execute_trade(self, trade_data: Dict) -> Optional[PaperTrade]:
        trade = PaperTrade(trade_data)
        amount = float(trade.amount or 0)
        fee = float(trade.fee or 0)

        if str(trade.side).lower() == 'buy':
            self.current_balance -= (amount + fee)
            self.total_loss += (amount + fee)
            self.losing_trades += 1
        else:
            self.current_balance += (amount - fee)
            self.total_profit += (amount - fee)
            self.winning_trades += 1

        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        self.trades.append(trade)
        return trade

    def get_performance_metrics(self) -> Dict:
        total_trades = len(self.trades)
        win_rate = (self.winning_trades / total_trades) if total_trades else 0.0
        profit_factor = (self.total_profit / self.total_loss) if self.total_loss > 0 else 0.0
        return {
            'starting_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'peak_balance': self.peak_balance,
        }

    def save_results(self, directory: str = 'data') -> bool:
        results = self.get_performance_metrics()
        results['trades'] = [t.to_dict() for t in self.trades]
        os.makedirs(directory, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(directory, f'paper_trading_results_{stamp}.json')
        with open(path, 'w') as f:
            json.dump(results, f, indent=2)
        return True

    def reset(self):
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.trades = []
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0


class PaperTradingIntegration:
    """Connect the paper simulator to the backtest engine."""

    def __init__(self, backtest_engine, paper_simulator):
        self.backtest_engine = backtest_engine
        self.paper_simulator = paper_simulator

    def run_integrated_test(self, strategy, start_time, end_time, initial_balance=1000.0):
        self.paper_simulator.reset()
        self.paper_simulator.initial_balance = initial_balance
        backtest_result = self.backtest_engine.run_backtest(
            strategy=strategy,
            start_time=start_time,
            end_time=end_time,
            starting_balance=initial_balance,
        )
        return {
            'backtest': backtest_result.to_dict(),
            'paper_trading': self.paper_simulator.get_performance_metrics(),
        }