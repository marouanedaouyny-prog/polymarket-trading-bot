"""
Paper Trading Simulator — delegates to the authoritative engine in src.trading.paper.
Kept for backward-compatible imports.
"""

import logging
from typing import Dict, Optional
from .paper import PaperTradingEngine, PaperTrade, PaperPosition, SimulatedMarket

logger = logging.getLogger(__name__)


class PaperTradingSimulator:
    """Wrapper around PaperTradingEngine for backward compatibility."""

    def __init__(self, initial_balance: float = 1000.0):
        self.engine = PaperTradingEngine(initial_balance=initial_balance)
        self.initial_balance = initial_balance

    def execute_trade(self, trade_data: Dict) -> Optional[PaperTrade]:
        direction = trade_data.get('side', 'buy').upper()
        amount = trade_data.get('amount', 0)
        price = trade_data.get('price', 0)
        market_id = trade_data.get('market_id', 'unknown')

        if direction == 'BUY':
            success = self.engine.open_position(market_id, 'BUY', amount, price)
        else:
            success = True
            self.engine.close_position(market_id, price)

        if success:
            return PaperTrade(
                id=f"pt_{len(self.engine.trade_history) + 1}",
                symbol=market_id,
                direction=direction,
                amount=amount,
                price=price,
                timestamp=trade_data.get('timestamp'),
            )
        return None

    def get_performance_metrics(self) -> Dict:
        stats = self.engine.get_stats()
        return {
            'starting_balance': self.initial_balance,
            'current_balance': stats['balance'],
            'peak_balance': self.initial_balance + stats['total_pnl'],
            'total_trades': stats['total_trades'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades'],
            'total_profit': stats['total_pnl'],
            'total_loss': stats['total_pnl'],
            'win_rate': stats['win_rate'] / 100,
            'profit_factor': float('inf') if stats['total_pnl'] > 0 else 0,
            'max_drawdown': stats.get('return_pct', 0) / 100,
        }

    def reset(self):
        self.engine.reset()


class PaperTradingIntegration:
    """Integrate paper trading with backtesting."""

    def __init__(self, backtest_engine, paper_simulator):
        self.backtest_engine = backtest_engine
        self.paper_simulator = paper_simulator

    def run_integrated_test(self, strategy, start_time, end_time, initial_balance=1000.0):
        self.paper_simulator.reset()
        self.paper_simulator.initial_balance = initial_balance
        backtest_result = self.backtest_engine.run_backtest(
            strategy=strategy, start_time=start_time,
            end_time=end_time, starting_balance=initial_balance
        )
        return {'backtest': backtest_result.to_dict(), 'paper_trading': self.paper_simulator.get_performance_metrics()}