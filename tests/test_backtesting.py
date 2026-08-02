"""
Test suite for backtesting engine.
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from src.backtesting.backtest_engine import BacktestEngine, Trade, BacktestResult, MonteCarloEngine
from src.backtesting.sample_strategy import mean_reversion_strategy


class TestBacktestEngine:
    """Test backtesting engine functionality."""

    def test_trade_creation(self):
        """Test Trade object creation."""
        trade = Trade(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            market_id="test-market",
            price=0.65,
            amount=100.0,
            side="buy",
            fee=0.7,
            slippage=0.01,
            latency=0.05
        )

        assert trade.timestamp == datetime(2023, 1, 1, 12, 0, 0)
        assert trade.market_id == "test-market"
        assert trade.price == 0.65
        assert trade.amount == 100.0
        assert trade.side == "buy"
        assert trade.fee == 0.7
        assert trade.slippage == 0.01
        assert trade.latency == 0.05

    def test_backtest_result_creation(self):
        """Test BacktestResult object creation."""
        result = BacktestResult(
            starting_balance=1000.0,
            ending_balance=1200.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            total_profit=300.0,
            total_loss=100.0,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            win_rate=0.6,
            profit_factor=3.0,
            trades=[]
        )

        assert result.starting_balance == 1000.0
        assert result.ending_balance == 1200.0
        assert result.total_trades == 10
        assert result.winning_trades == 6
        assert result.losing_trades == 4
        assert result.total_profit == 300.0
        assert result.total_loss == 100.0
        assert result.max_drawdown == 0.10
        assert result.sharpe_ratio == 1.5
        assert result.sortino_ratio == 2.0
        assert result.win_rate == 0.6
        assert result.profit_factor == 3.0

    def test_backtest_engine_initialization(self):
        """Test BacktestEngine initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample historical data
            sample_data = [
                {
                    "timestamp": "2023-01-01T10:00:00",
                    "price": 0.60,
                    "volume": 100000
                },
                {
                    "timestamp": "2023-01-01T11:00:00",
                    "price": 0.65,
                    "volume": 150000
                }
            ]

            # Write sample data
            market_file = Path(tmpdir) / "test-market.json"
            with open(market_file, 'w') as f:
                json.dump(sample_data, f)

            # Initialize engine
            engine = BacktestEngine(str(tmpdir))

            assert len(engine.historical_data) == 1
            assert "test-market" in engine.historical_data

    def test_trade_simulation(self):
        """Test trade simulation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample historical data
            sample_data = [
                {
                    "timestamp": "2023-01-01T10:00:00",
                    "price": 0.60,
                    "volume": 100000
                }
            ]

            # Write sample data
            market_file = Path(tmpdir) / "test-market.json"
            with open(market_file, 'w') as f:
                json.dump(sample_data, f)

            # Initialize engine
            engine = BacktestEngine(str(tmpdir))
            engine.set_start_time("2023-01-01T10:00:00")

            # Simulate trade
            trade = engine.simulate_trade(
                market_id="test-market",
                price=0.60,
                amount=100.0,
                side="buy",
                slippage_pct=0.01,
                latency_ms=50
            )

            assert trade is not None
            assert trade.market_id == "test-market"
            assert trade.price == 0.606  # 0.60 + 1% slippage
            assert trade.amount == 100.0
            assert trade.side == "buy"
            assert abs(trade.fee - 0.7) < 0.001  # 0.7% fee (allowing for floating point precision)

    def test_metrics_calculation(self):
        """Test performance metrics calculation."""
        # Create sample trades
        trades = [
            Trade(
                timestamp=datetime(2023, 1, 1, 10, 0, 0),
                market_id="test",
                price=0.60,
                amount=100.0,
                side="buy",
                fee=0.7,
                slippage=0.006,
                latency=0.05
            ),
            Trade(
                timestamp=datetime(2023, 1, 1, 11, 0, 0),
                market_id="test",
                price=0.65,
                amount=100.0,
                side="sell",
                fee=0.7,
                slippage=0.0065,
                latency=0.05
            )
        ]

        # Calculate metrics
        engine = BacktestEngine("")  # Empty path for testing
        result = engine._calculate_metrics(
            trades=trades,
            starting_balance=1000.0,
            peak_balance=1065.0  # After first trade
        )

        assert result.starting_balance == 1000.0
        # Paired P&L: (sell_price - buy_price) * qty - sell_fee = (0.65-0.60)*100 - 0.7 = 4.3
        assert abs(result.ending_balance - 1004.3) < 0.01
        assert result.total_trades == 1   # one closed round-trip
        assert result.winning_trades == 1
        assert result.losing_trades == 0
        assert result.total_profit > 0
        assert result.win_rate == 1.0

    def test_monte_carlo_simulation(self):
        """Test Monte Carlo simulation."""
        # Create sample backtest result
        result = BacktestResult(
            starting_balance=1000.0,
            ending_balance=1200.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            total_profit=300.0,
            total_loss=100.0,
            max_drawdown=0.10,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            win_rate=0.6,
            profit_factor=3.0,
            trades=[]
        )

        # Run Monte Carlo simulation
        mc_engine = MonteCarloEngine(result)
        mc_results = mc_engine.run_simulation(n_simulations=100)

        assert 'ending_balances' in mc_results
        assert 'max_drawdowns' in mc_results
        assert 'ruin_probability' in mc_results
        assert 'expected_final_balance' in mc_results
        assert 'cvar_95' in mc_results

        assert len(mc_results['ending_balances']) == 100
        assert len(mc_results['max_drawdowns']) == 100
        assert 0.0 <= mc_results['ruin_probability'] <= 1.0
        assert mc_results['expected_final_balance'] > 0


class TestSampleStrategy:
    """Test sample trading strategy."""

    def test_mean_reversion_strategy(self):
        """Test mean reversion strategy logic."""
        # Create sample historical data
        historical_data = {
            "test-market": [
                {"timestamp": "2023-01-01T10:00:00", "price": 0.60},
                {"timestamp": "2023-01-01T10:30:00", "price": 0.55},
                {"timestamp": "2023-01-01T11:00:00", "price": 0.58},
                {"timestamp": "2023-01-01T11:30:00", "price": 0.62}
            ]
        }

        # Test strategy at different times
        decisions = mean_reversion_strategy(
            current_time=datetime(2023, 1, 1, 10, 30, 0),
            current_balance=1000.0,
            historical_data=historical_data
        )

        # Should generate a buy signal (price below SMA - std)
        assert len(decisions) > 0
        assert decisions[0]['side'] == 'buy'
        assert decisions[0]['market_id'] == 'test-market'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])