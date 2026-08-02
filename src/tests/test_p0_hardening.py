import pytest
import unittest.mock as mock
from agent_trading_system import TradingAgentSystem
from src.utils.config import config

class TestP0Hardening:
    @pytest.fixture
    def trading_system(self):
        with mock.patch('src.data.polymarket_client.PolymarketClient') as mock_client, \
             mock.patch('src.ml.market_predictor.MarketPredictor') as mock_ml, \
             mock.patch('src.risk.dynamic_risk.DynamicRiskManager') as mock_rm, \
             mock.patch('src.data.sqlite_db.get_db') as mock_db:
            
            # Configure DynamicRiskManager mock instance
            instance = mock_rm.return_value
            instance.should_trade.return_value = (True, "Approved")
            instance.get_risk_metrics.return_value = {
                'drawdown': 0.0,
                'winning_streak': 0,
                'losing_streak': 0
            }
            
            ts = TradingAgentSystem(starting_balance=100)
            # Ensure ts uses our mocks
            ts.client = mock_client
            ts.ml_model = mock_ml
            ts.risk_manager = instance
            ts.db = mock_db
            
            # Force risk params in ts to match config for predictability
            ts.risk['max_daily_trades'] = 20
            ts.risk['daily_loss_limit'] = 0.05
            ts.risk['min_ev'] = 0.10
            ts.risk['min_edge'] = 0.08
            ts.risk['min_bet'] = 1.0
            ts.risk['max_position_size'] = 0.02
            
            return ts

    def test_ev_calculation(self, trading_system):
        # Manually verify EV formula
        # ev = (model_prob * ((1 / price - 1) * (1 - self.fee))) - (1 - model_prob)
        price = 0.10
        model_prob = 0.90
        fee = 0.07
        expected_ev = (0.90 * ((1 / 0.10 - 1) * (0.93))) - (1 - 0.90)
        
        # Test the formula in TradingAgentSystem context
        trading_system.ml_model.predict_win_probability.return_value = model_prob
        trading_system.ml_model.is_trained = True
        
        # Mock intelligence
        trading_system.get_llm_intelligence = mock.Mock(return_value={'sectors': ['crypto'], 'reasoning': 'Good', 'confidence_boost': 0})
        
        with mock.patch('src.agents.sentiment_agent.SentimentAgent.analyze_sentiment', return_value={'score': 0.9, 'reasoning': 'Bullish'}):
            markets = [{'question': 'Will BTC hit 100k?', 'outcomePrices': '[0.10, 0.90]', 'volume': 100000, 'id': '1'}]
            trading_system.client.get_markets.return_value = markets
            
            opps = trading_system.research_agent()
            assert len(opps) == 1
            assert abs(opps[0]['ev'] - expected_ev) < 0.001

    def test_minimum_balance_enforcement(self, trading_system):
        # Ensure risk parameters are set for this test
        trading_system.risk['min_edge'] = 0.05
        trading_system.risk['min_bet'] = 1.0
        trading_system.risk['max_position_size'] = 0.02
        trading_system.risk['price_range'] = (0.01, 0.99)
        trading_system.risk['min_volume'] = 1000
        trading_system.risk['min_ev'] = 0.01
        trading_system.risk['min_confidence'] = 10
        
        trading_system.balance = 50.0
        trading_system.daily_start = 50.0
        opp = {'price': 0.1, 'volume': 100000, 'ev': 1.0, 'edge': 0.5, 'confidence': 90}
        check = trading_system.risk_agent(opp)
        assert check['approved'] == True, f"Rejected for: {check.get('reason')}"
        
        trading_system.balance = 49.0
        check = trading_system.risk_agent(opp)
        assert check['approved'] == False
        assert 'Balance too low' in check['reason']

    def test_intelligence_failure_circuit_breaker(self, trading_system):
        trading_system.balance = 100.0
        opp = {'question': 'Test?', 'price': 0.1, 'volume': 100000, 'ev': 1.0, 'edge': 0.5, 'confidence': 90, 'canonical_id': 'TEST-1'}
        
        # Mock intelligence failure
        trading_system.get_llm_intelligence = mock.Mock(return_value=None)
        
        result = trading_system.trader_agent(opp)
        assert result.get('blocked') == True

    def test_daily_limits(self, trading_system):
        trading_system.balance = 100.0
        trading_system.daily_start = 100.0
        trading_system.trades_today = trading_system.risk['max_daily_trades']
        
        opp = {'price': 0.1, 'volume': 100000, 'ev': 1.0, 'edge': 0.5, 'confidence': 90}
        check = trading_system.risk_agent(opp)
        assert check['approved'] == False
        assert 'Daily trade limit reached' in check['reason']
        
        # Test daily loss limit
        trading_system.trades_today = 0
        trading_system.balance = 94.0 # 6% loss, limit is 5% in config
        check = trading_system.risk_agent(opp)
        assert check['approved'] == False
        assert 'Daily loss limit reached' in check['reason']

    def test_paper_ledger_recording(self, trading_system):
        trading_system.balance = 100.0
        trading_system.resolved_outcomes = {'TEST-1': 'yes'}
        trading_system.ml_model.predict_win_probability.return_value = 0.9
        trading_system.ml_model.is_trained = True
        trading_system.get_llm_intelligence = mock.Mock(return_value={'confidence_boost': 5, 'reasoning': 'Good'})
        
        opp = {
            'market_id': '1',
            'canonical_id': 'TEST-1',
            'question': 'Test?',
            'price': 0.1,
            'volume': 100000,
            'ev': 7.433,
            'edge': 0.8,
            'confidence': 85
        }
        
        with mock.patch('src.trading.ledger.PaperLedger.record_entry') as mock_entry, \
             mock.patch('src.trading.ledger.PaperLedger.record_resolution') as mock_res:
            
            trading_system.trader_agent(opp)
            
            assert mock_entry.called
            assert mock_res.called
