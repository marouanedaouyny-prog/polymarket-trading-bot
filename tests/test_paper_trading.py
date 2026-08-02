"""
Test suite for paper trading simulator.
"""

import pytest
from datetime import datetime
from src.trading.paper_trading import PaperTrade, PaperTradingSimulator, PaperTradingIntegration


class TestPaperTrade:
    """Test PaperTrade object."""

    def test_paper_trade_creation(self):
        """Test PaperTrade object creation."""
        trade_data = {
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test-market',
            'side': 'buy',
            'amount': 100.0,
            'price': 0.60,
            'fee': 0.7,
            'slippage': 0.006,
            'status': 'simulated'
        }

        trade = PaperTrade(trade_data)

        assert trade.timestamp == '2023-01-01T10:00:00'
        assert trade.market_id == 'test-market'
        assert trade.side == 'buy'
        assert trade.amount == 100.0
        assert trade.price == 0.60
        assert trade.fee == 0.7
        assert trade.slippage == 0.006
        assert trade.status == 'simulated'

    def test_to_dict(self):
        """Test PaperTrade to_dict method."""
        trade_data = {
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test-market',
            'side': 'sell',
            'amount': 50.0,
            'price': 0.65,
            'fee': 0.35,
            'slippage': 0.00325,
            'status': 'simulated'
        }

        trade = PaperTrade(trade_data)
        result = trade.to_dict()

        assert result == trade_data


class TestPaperTradingSimulator:
    """Test PaperTradingSimulator functionality."""

    def test_initialization(self):
        """Test simulator initialization."""
        simulator = PaperTradingSimulator(initial_balance=1000.0)

        assert simulator.initial_balance == 1000.0
        assert simulator.current_balance == 1000.0
        assert simulator.peak_balance == 1000.0
        assert simulator.trades == []
        assert simulator.winning_trades == 0
        assert simulator.losing_trades == 0

    def test_execute_trade_buy(self):
        """Test executing a buy trade."""
        simulator = PaperTradingSimulator(initial_balance=1000.0)

        trade_data = {
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test-market',
            'side': 'buy',
            'amount': 100.0,
            'price': 0.60,
            'fee': 0.7,
            'slippage': 0.006
        }

        trade = simulator.execute_trade(trade_data)

        assert trade is not None
        assert simulator.current_balance == 1000.0 - 100.0 - 0.7
        assert simulator.total_loss == 100.0 + 0.7
        assert simulator.losing_trades == 1
        assert len(simulator.trades) == 1

    def test_execute_trade_sell(self):
        """Test executing a sell trade."""
        simulator = PaperTradingSimulator(initial_balance=1000.0)

        trade_data = {
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test-market',
            'side': 'sell',
            'amount': 100.0,
            'price': 0.65,
            'fee': 0.7,
            'slippage': 0.0065
        }

        trade = simulator.execute_trade(trade_data)

        assert trade is not None
        assert simulator.current_balance == 1000.0 + 100.0 - 0.7
        assert simulator.total_profit == 100.0 - 0.7
        assert simulator.winning_trades == 1
        assert len(simulator.trades) == 1

    def test_performance_metrics(self):
        """Test performance metrics calculation."""
        simulator = PaperTradingSimulator(initial_balance=1000.0)

        # Add some trades
        simulator.execute_trade({
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test',
            'side': 'buy',
            'amount': 100.0,
            'price': 0.60,
            'fee': 0.7
        })

        simulator.execute_trade({
            'timestamp': '2023-01-01T11:00:00',
            'market_id': 'test',
            'side': 'sell',
            'amount': 150.0,
            'price': 0.65,
            'fee': 1.05
        })

        metrics = simulator.get_performance_metrics()

        assert metrics['starting_balance'] == 1000.0
        assert metrics['current_balance'] == 1000.0 - 100.0 - 0.7 + 150.0 - 1.05
        assert metrics['total_trades'] == 2
        assert metrics['winning_trades'] == 1
        assert metrics['losing_trades'] == 1
        assert metrics['total_profit'] == 150.0 - 1.05
        assert metrics['total_loss'] == 100.0 + 0.7
        assert metrics['win_rate'] == 0.5
        assert metrics['profit_factor'] > 0

    def test_save_results(self):
        """Test saving results to file."""
        import os
        from pathlib import Path

        simulator = PaperTradingSimulator(initial_balance=1000.0)

        # Add a trade
        simulator.execute_trade({
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test',
            'side': 'buy',
            'amount': 100.0,
            'price': 0.60,
            'fee': 0.7
        })

        # Save results
        result = simulator.save_results()
        assert result == True

        # Check file exists
        files = list(Path("data").glob("paper_trading_results_*.json"))
        assert len(files) > 0

        # Clean up
        for file in files:
            file.unlink()

    def test_reset(self):
        """Test simulator reset."""
        simulator = PaperTradingSimulator(initial_balance=1000.0)

        # Add trades
        simulator.execute_trade({
            'timestamp': '2023-01-01T10:00:00',
            'market_id': 'test',
            'side': 'buy',
            'amount': 100.0,
            'price': 0.60,
            'fee': 0.7
        })

        # Reset
        simulator.reset()

        assert simulator.current_balance == 1000.0
        assert simulator.peak_balance == 1000.0
        assert simulator.trades == []
        assert simulator.winning_trades == 0
        assert simulator.losing_trades == 0


class TestPaperTradingIntegration:
    """Test paper trading integration with backtesting."""

    def test_integration(self):
        """Test basic integration functionality."""
        from src.backtesting.backtest_engine import BacktestEngine

        # Create instances
        backtest_engine = BacktestEngine("")
        paper_simulator = PaperTradingSimulator(initial_balance=1000.0)
        integration = PaperTradingIntegration(backtest_engine, paper_simulator)

        assert integration.backtest_engine == backtest_engine
        assert integration.paper_simulator == paper_simulator


if __name__ == "__main__":
    pytest.main([__file__, "-v"])