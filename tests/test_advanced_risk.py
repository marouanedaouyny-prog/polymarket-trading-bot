"""
Test suite for advanced risk management features.
"""
import pytest
import numpy as np
from src.risk.dynamic_risk import DynamicRiskManager


class TestAdvancedRiskManagement:
    """Test advanced risk management features."""

    def test_portfolio_variance(self):
        """Test portfolio variance calculation."""
        risk_manager = DynamicRiskManager()

        # Simple test case
        positions = [0.6, 0.4]  # 60% in asset 1, 40% in asset 2
        covariance_matrix = np.array([
            [0.04, 0.01],  # Asset 1 variance and covariance
            [0.01, 0.09]   # Asset 2 variance
        ])

        variance = risk_manager.calculate_portfolio_variance(positions, covariance_matrix)

        # Manual calculation: 0.6²*0.04 + 0.4²*0.09 + 2*0.6*0.4*0.01
        expected_variance = 0.6*0.6*0.04 + 0.4*0.4*0.09 + 2*0.6*0.4*0.01
        assert abs(variance - expected_variance) < 0.001

    def test_monte_carlo_simulation(self):
        """Test Monte Carlo simulation."""
        risk_manager = DynamicRiskManager()
        risk_manager.wins = 100
        risk_manager.losses = 50
        risk_manager.total_profit = 1000  # $10 avg profit
        risk_manager.total_loss = 300    # $6 avg loss

        results = risk_manager.monte_carlo_simulation(1000, n_simulations=100, n_days=10)

        # Check that results are reasonable
        assert 'ending_balances' in results
        assert 'max_drawdowns' in results
        assert 'ruin_probability' in results
        assert 'expected_final_balance' in results
        assert 'cvar_95' in results

        # Should have 100 simulations
        assert len(results['ending_balances']) == 100
        assert len(results['max_drawdowns']) == 100

        # Ruin probability should be reasonable (not 0 or 1)
        assert 0.0 <= results['ruin_probability'] <= 0.5

        # Expected final balance should be positive
        assert results['expected_final_balance'] > 500  # Starting from 1000

    def test_mean_variance_optimization(self):
        """Test mean-variance portfolio optimization."""
        risk_manager = DynamicRiskManager()

        # Test with 3 assets
        expected_returns = np.array([0.10, 0.15, 0.08])  # 10%, 15%, 8% expected returns
        covariance_matrix = np.array([
            [0.04, 0.01, 0.005],
            [0.01, 0.09, 0.02],
            [0.005, 0.02, 0.06]
        ])

        result = risk_manager.mean_variance_optimization(expected_returns, covariance_matrix)

        assert result is not None
        assert 'weights' in result
        assert 'expected_return' in result
        assert 'risk' in result
        assert 'sharpe_ratio' in result

        # Weights should sum to 1
        weights_sum = sum(result['weights'])
        assert abs(weights_sum - 1.0) < 0.001

        # All weights should be between 0 and 1
        for weight in result['weights']:
            assert 0.0 <= weight <= 1.0

        # Expected return should be reasonable
        assert 0.08 <= result['expected_return'] <= 0.15

    def test_kelly_criterion(self):
        """Test Kelly criterion position sizing."""
        risk_manager = DynamicRiskManager()

        # Test various scenarios
        test_cases = [
            # (win_prob, odds, expected_position_range)
            (0.60, 2.0, (0.05, 0.15)),   # 60% win prob, 2:1 odds
            (0.55, 2.0, (0.01, 0.06)),   # 55% win prob, 2:1 odds
            (0.70, 3.0, (0.10, 0.20)),   # 70% win prob, 3:1 odds
            (0.40, 2.0, (0.01, 0.01)),   # 40% win prob - should be minimum
            (0.80, 1.5, (0.15, 0.25)),   # 80% win prob, 1.5:1 odds
        ]

        for win_prob, odds, (min_expected, max_expected) in test_cases:
            position = risk_manager.calculate_kelly_position(win_prob, odds)
            assert min_expected <= position <= max_expected, \
                f"Win prob {win_prob}, odds {odds}: got {position}, expected {min_expected}-{max_expected}"

    def test_circuit_breakers_comprehensive(self):
        """Test all circuit breaker conditions."""
        risk_manager = DynamicRiskManager()
        risk_manager.daily_start_balance = 1000

        # Test catastrophic drawdown
        assert risk_manager.check_circuit_breakers(400, 1000) == True  # 60% drawdown
        # Note: 501 balance would trigger daily loss limit (-499 < -200), so we test a smaller drawdown
        assert risk_manager.check_circuit_breakers(850, 1000) == False  # 15% drawdown (OK)

        # Test excessive losses
        risk_manager.consecutive_losses = 9
        assert risk_manager.check_circuit_breakers(900, 1000) == False

        risk_manager.consecutive_losses = 10
        assert risk_manager.check_circuit_breakers(900, 1000) == True

        # Test daily loss limit
        risk_manager.consecutive_losses = 0
        risk_manager.current['daily_loss_limit'] = 0.10  # 10% daily loss limit

        # 15% loss exceeds 10% limit
        assert risk_manager.check_circuit_breakers(850, 1000) == True

        # 9% loss is within limit
        assert risk_manager.check_circuit_breakers(910, 1000) == False


class TestRiskStatistics:
    """Test risk calculation utilities."""

    def test_win_rate_calculation(self):
        """Test win rate calculation."""
        risk_manager = DynamicRiskManager()

        # Default value
        assert risk_manager.get_win_rate() == 0.95  # Default from __init__

        # Test that it returns the property value
        risk_manager.win_rate = 0.6
        assert risk_manager.get_win_rate() == 0.6

    def test_average_profit_loss(self):
        """Test average profit/loss calculations."""
        risk_manager = DynamicRiskManager()

        # Default values
        assert risk_manager.get_average_profit() == 10.0
        assert risk_manager.get_average_loss() == 5.0

        # With actual data
        risk_manager.avg_win = 20
        assert risk_manager.get_average_profit() == 20.0

        risk_manager.avg_loss = 15
        assert risk_manager.get_average_loss() == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])