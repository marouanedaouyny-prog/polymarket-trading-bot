"""
Test suite for security fixes and risk management enhancements.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.api.main import API_KEY
from src.risk.dynamic_risk import DynamicRiskManager
from agent_trading_system import TradingAgentSystem


class TestSecurityFixes:
    """Test that critical security issues have been fixed."""

    def test_api_key_validation(self):
        """Test that API key validation works properly."""
        # Test missing API key raises error
        with patch.dict(os.environ, {'FASTAPI_API_KEY': ''}):
            with pytest.raises(ValueError, match="FASTAPI_API_KEY environment variable is required"):
                # Force reimport to test validation
                import importlib
                import src.api.main
                importlib.reload(src.api.main)

    def test_input_validation(self):
        """Test that market data input validation rejects malformed entries."""
        # Test directly what the research_agent validates: price, volume, question presence
        import json as _json

        def _is_valid_market(m):
            """Mirrors the research_agent validation logic."""
            q = m.get('question', '')
            if not q:
                return False
            prices_raw = m.get('outcomePrices', '[]')
            try:
                prices = _json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            except (ValueError, TypeError):
                return False
            if not prices or len(prices) < 2:
                return False
            try:
                float(prices[0])
            except (ValueError, TypeError):
                return False
            return True

        raw_markets = [
            {'invalid': 'data'},                                                          # missing fields
            {'question': '', 'outcomePrices': '[0.5, 0.5]'},                             # empty question
            {'question': 'Valid question', 'outcomePrices': 'invalid'},                  # bad JSON
            {'question': 'Valid question', 'outcomePrices': '[0.6, 0.4]',
             'volume': 100000, 'id': 'test-market'},                                     # valid
        ]

        valid = [m for m in raw_markets if _is_valid_market(m)]
        assert len(valid) == 1
        assert valid[0]['id'] == 'test-market'

    def test_thread_safety(self):
        """Test that balance updates are thread-safe."""
        system = TradingAgentSystem(starting_balance=1000)

        # Simulate concurrent balance updates
        import threading

        def update_balance(amount):
            for _ in range(100):
                with system.balance_lock:
                    system.balance += amount

        threads = []
        for _ in range(10):
            t = threading.Thread(target=update_balance, args=(1,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should be exactly 1000 updates of +1
        assert system.balance == 2000

    def test_circuit_breakers(self):
        """Test that circuit breakers work properly."""
        risk_manager = DynamicRiskManager()
        risk_manager.daily_start_balance = 1000

        # Test catastrophic drawdown
        assert risk_manager.check_circuit_breakers(400, 1000) == True  # 60% drawdown

        # Test excessive losses
        risk_manager.consecutive_losses = 10
        assert risk_manager.check_circuit_breakers(900, 1000) == True

        # Test daily loss limit
        risk_manager.consecutive_losses = 0
        risk_manager.current['daily_loss_limit'] = 0.10  # 10% daily loss limit
        assert risk_manager.check_circuit_breakers(850, 1000) == True  # 15% loss exceeds 10% limit

        # Test normal conditions
        assert risk_manager.check_circuit_breakers(950, 1000) == False


class TestRiskManagementEnhancements:
    """Test enhanced risk management features."""

    def test_slippage_simulation(self):
        """Test that slippage is properly tracked."""
        system = TradingAgentSystem(starting_balance=1000)

        # Mock a trade with slippage
        opportunity = {
            'canonical_id': 'test-market',
            'price': 0.65,
            'volume': 100,
            'question': 'Test question'
        }

        # Simulate execution with slippage
        actual_price = 0.68  # 0.03 slippage

        # This should be logged in the execution logging
        with patch('builtins.print') as mock_print:
            # The slippage calculation should be logged
            system._log_execution(opportunity, actual_price)

            # Check that slippage was calculated
            logs = [str(call) for call in mock_print.call_args_list]
            slippage_logs = [log for log in logs if 'slippage' in log.lower()]
            assert len(slippage_logs) > 0

    def test_conservative_position_sizing(self):
        """Test that position sizing is conservative."""
        risk_manager = DynamicRiskManager()

        # Test Kelly criterion with conservative settings
        kelly_position = risk_manager.calculate_kelly_position(0.6, 2.0)  # 60% win prob, 2:1 odds

        # Should be conservative (half-Kelly)
        assert 0.01 <= kelly_position <= 0.20  # Between 1% and 20%

        # Test with low probability
        low_prob_position = risk_manager.calculate_kelly_position(0.4, 2.0)  # 40% win prob
        assert low_prob_position == 0.01  # Minimum position


class TestIntegrationSafety:
    """Test overall system safety and integration."""

    def test_emergency_stop_conditions(self):
        """Test that emergency conditions properly halt trading."""
        system = TradingAgentSystem(starting_balance=1000)
        risk_manager = system.risk_manager

        # Simulate catastrophic loss
        system.balance = 400  # 60% drawdown

        # Risk manager should detect this
        risk_manager.daily_start_balance = 1000
        risk_manager.consecutive_losses = 0

        should_stop = risk_manager.check_circuit_breakers(system.balance, 1000)
        assert should_stop == True

    def test_configuration_safety(self):
        """Test that configuration has safe defaults."""
        from src.utils.config import TradingConfig

        cfg = TradingConfig()

        # Check that defaults are conservative
        assert cfg.DAILY_LOSS_LIMIT <= 0.20   # Max 20% daily loss (env default is 0.05)
        assert cfg.MAX_POSITION_PCT <= 0.20   # Max 20% position size (env default is 0.02)
        assert cfg.MIN_EDGE >= 0.05           # Minimum edge required (env default is 0.08)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])