import pytest
import unittest.mock as mock
import numpy as np

from src.ml.timesfm_predictor import TimesFMPredictor
from src.trading.strategies import TimesFMStrategy, MarketSnapshot, Action, Signal
from src.ml.market_predictor import MarketPredictor


class TestTimesFMPredictor:
    def test_singleton(self):
        a = TimesFMPredictor()
        b = TimesFMPredictor()
        assert a is b

    def test_forecast_short_series(self):
        p = TimesFMPredictor()
        p._loaded = True
        result = p.forecast([0.5] * 10, horizon=5)
        assert result is None

    def test_get_trend_signal_short_series(self):
        p = TimesFMPredictor()
        result = p.get_trend_signal([0.5] * 10)
        assert result["direction"] == 0
        assert result["confidence"] == 0.0
        assert result["reason"] == "forecast unavailable"

    def test_get_trend_signal_delegates_to_forecast(self):
        p = TimesFMPredictor()
        p._loaded = True
        prices = list(np.sin(np.linspace(0, 6, 50)))

        mock_point = np.array([[0.6, 0.65, 0.7, 0.72, 0.75]])
        mock_quantile = np.zeros((1, 5, 10))
        mock_quantile[0, :, 1] = [0.55, 0.58, 0.62, 0.64, 0.66]
        mock_quantile[0, :, -1] = [0.65, 0.72, 0.78, 0.80, 0.84]

        with mock.patch.object(p, 'forecast', return_value=(mock_point, mock_quantile)):
            result = p.get_trend_signal(prices, horizon=5)

            assert result["direction"] == 1
            assert result["confidence"] > 0
            assert "bullish" in result["reason"]
            assert result["forecast_end"] == 0.75
            assert result["uncertainty"] > 0

    def test_get_trend_signal_bearish(self):
        p = TimesFMPredictor()
        p._loaded = True
        prices = list(np.linspace(0.6, 0.55, 50))

        mock_point = np.array([[0.53, 0.51, 0.48, 0.45, 0.42]])
        mock_quantile = np.zeros((1, 5, 10))
        mock_quantile[0, :, 1] = [0.50, 0.48, 0.45, 0.42, 0.39]
        mock_quantile[0, :, -1] = [0.56, 0.54, 0.51, 0.48, 0.45]

        with mock.patch.object(p, 'forecast', return_value=(mock_point, mock_quantile)):
            result = p.get_trend_signal(prices, horizon=5)

            assert result["direction"] == -1
            assert result["confidence"] > 0
            assert "bearish" in result["reason"]

    def test_get_trend_signal_neutral(self):
        p = TimesFMPredictor()
        p._loaded = True
        prices = list(np.linspace(0.5, 0.5, 50))

        mock_point = np.array([[0.50, 0.50, 0.50, 0.50, 0.50]])
        mock_quantile = np.zeros((1, 5, 10))
        mock_quantile[0, :, 1] = [0.48, 0.48, 0.48, 0.48, 0.48]
        mock_quantile[0, :, -1] = [0.52, 0.52, 0.52, 0.52, 0.52]

        with mock.patch.object(p, 'forecast', return_value=(mock_point, mock_quantile)):
            result = p.get_trend_signal(prices, horizon=5)

            assert result["direction"] == 0
            assert result["confidence"] < 0.02

    def test_get_trend_signal_forecast_failure(self):
        p = TimesFMPredictor()
        p._loaded = True
        prices = list(np.sin(np.linspace(0, 6, 50)))

        with mock.patch.object(p, 'forecast', return_value=None):
            result = p.get_trend_signal(prices, horizon=5)

            assert result["direction"] == 0
            assert result["confidence"] == 0.0
            assert "unavailable" in result["reason"]

    def test_get_quantile_forecast(self):
        p = TimesFMPredictor()
        p._loaded = True
        prices = list(np.linspace(0, 1, 50))

        mock_point = np.array([[0.6, 0.65, 0.7]])
        mock_quantile = np.zeros((1, 3, 10))
        mock_quantile[0, -1, 5] = 0.72

        with mock.patch.object(p, 'forecast', return_value=(mock_point, mock_quantile)):
            result = p.get_quantile_forecast(prices, horizon=3, quantile_idx=5)
            assert result == 0.72

    def test_get_quantile_forecast_failure(self):
        p = TimesFMPredictor()
        p._loaded = True
        with mock.patch.object(p, 'forecast', return_value=None):
            result = p.get_quantile_forecast([0.5] * 50, horizon=3)
            assert result is None


class TestTimesFMStrategy:
    def make_snapshot(self, prices=None, current_price=None):
        if prices is None:
            prices = list(np.sin(np.linspace(0, 6, 50)))
        return MarketSnapshot(
            market_id="test-1",
            prices=prices,
            volumes=[1000] * len(prices),
            current_price=current_price or prices[-1],
            days_left=10,
            question="Test market?",
        )

    def test_hold_short_history(self):
        strategy = TimesFMStrategy()
        snapshot = self.make_snapshot(prices=[0.5] * 10)
        signal = strategy.generate_signal(snapshot)
        assert signal.action == Action.HOLD

    def test_buy_signal(self):
        strategy = TimesFMStrategy(min_confidence=0.3)
        snapshot = self.make_snapshot()

        mock_signal = {
            "direction": 1,
            "confidence": 0.75,
            "current_price": 0.5,
            "forecast_end": 0.62,
            "weighted_forecast": 0.58,
            "forecast_series": [0.55, 0.58, 0.60, 0.61, 0.62],
            "uncertainty": 0.08,
            "reason": "bullish (+0.0800 exp)",
        }

        with mock.patch(
            "src.ml.timesfm_predictor.TimesFMPredictor.get_trend_signal",
            return_value=mock_signal,
        ):
            signal = strategy.generate_signal(snapshot)

        assert signal.action == Action.BUY
        assert signal.confidence > 0
        assert "TimesFM" in signal.reason
        assert signal.metadata["forecast_end"] == 0.62

    def test_sell_signal(self):
        strategy = TimesFMStrategy(min_confidence=0.3)
        snapshot = self.make_snapshot()

        mock_signal = {
            "direction": -1,
            "confidence": 0.78,
            "current_price": 0.5,
            "forecast_end": 0.38,
            "weighted_forecast": 0.42,
            "forecast_series": [0.45, 0.43, 0.41, 0.39, 0.38],
            "uncertainty": 0.06,
            "reason": "bearish (-0.0800 exp)",
        }

        with mock.patch(
            "src.ml.timesfm_predictor.TimesFMPredictor.get_trend_signal",
            return_value=mock_signal,
        ):
            signal = strategy.generate_signal(snapshot)

        assert signal.action == Action.SELL
        assert signal.confidence > 0
        assert "TimesFM" in signal.reason

    def test_hold_low_confidence(self):
        strategy = TimesFMStrategy(min_confidence=0.8)
        snapshot = self.make_snapshot()

        mock_signal = {
            "direction": 1,
            "confidence": 0.5,
            "current_price": 0.5,
            "forecast_end": 0.52,
            "weighted_forecast": 0.51,
            "forecast_series": [0.51, 0.51, 0.52, 0.52, 0.52],
            "uncertainty": 0.15,
            "reason": "bullish (+0.0100 exp)",
        }

        with mock.patch(
            "src.ml.timesfm_predictor.TimesFMPredictor.get_trend_signal",
            return_value=mock_signal,
        ):
            signal = strategy.generate_signal(snapshot)

        assert signal.action == Action.HOLD

    def test_hold_neutral_direction(self):
        strategy = TimesFMStrategy(min_confidence=0.3)
        snapshot = self.make_snapshot()

        mock_signal = {
            "direction": 0,
            "confidence": 0.0,
            "current_price": 0.5,
            "forecast_end": 0.50,
            "weighted_forecast": 0.50,
            "forecast_series": [0.50, 0.50, 0.50, 0.50, 0.50],
            "uncertainty": 0.0,
            "reason": "neutral",
        }

        with mock.patch(
            "src.ml.timesfm_predictor.TimesFMPredictor.get_trend_signal",
            return_value=mock_signal,
        ):
            signal = strategy.generate_signal(snapshot)

        assert signal.action == Action.HOLD


class TestSignalFilterTimesFM:
    def test_enrich_adds_fields(self):
        from src.trading.signal_filter import _enrich_with_timesfm

        markets = [
            {"id": "m1", "price": 0.5, "volume": 50000, "days_left": 10, "question": "Test?"},
        ]

        mock_signal = {
            "direction": 1,
            "confidence": 0.82,
            "current_price": 0.5,
            "forecast_end": 0.58,
            "weighted_forecast": 0.55,
            "forecast_series": [0.52, 0.54, 0.56, 0.57, 0.58],
            "uncertainty": 0.06,
            "reason": "bullish (+0.0500 exp)",
        }

        with mock.patch(
            "src.ml.timesfm_predictor.TimesFMPredictor.get_trend_signal",
            return_value=mock_signal,
        ), mock.patch(
            "src.data.price_history.get_price_history",
            return_value=([0.5] * 30, [1000] * 30),
        ):
            _enrich_with_timesfm(markets)

        m = markets[0]
        assert m["timesfm_direction"] == 1
        assert m["timesfm_confidence"] > 0
        assert m["timesfm_forecast_end"] == 0.58
        assert m["timesfm_uncertainty"] > 0
        assert m["timesfm_reason"] == "bullish (+0.0500 exp)"

    def test_enrich_insufficient_data(self):
        from src.trading.signal_filter import _enrich_with_timesfm

        markets = [
            {"id": "m1", "price": 0.5, "volume": 50000, "days_left": 10, "question": "Test?"},
        ]

        with mock.patch(
            "src.data.price_history.get_price_history",
            return_value=([0.5] * 5, [1000] * 5),
        ):
            _enrich_with_timesfm(markets)

        m = markets[0]
        assert m["timesfm_direction"] == 0
        assert m["timesfm_confidence"] == 0.0
        assert m["timesfm_reason"] == "insufficient price history"

    def test_score_markets_with_timesfm_flag(self):
        from src.trading.signal_filter import score_markets

        markets = [
            {"id": "m1", "price": 0.5, "volume": 50000, "days_left": 10, "question": "Test?"},
        ]

        with mock.patch(
            "src.data.price_history.get_price_history",
            return_value=([0.5] * 30, [1000] * 30),
        ), mock.patch(
            "src.trading.signal_filter._enrich_with_timesfm",
        ) as mock_enrich:
            result = score_markets(markets, use_timesfm=True)
            mock_enrich.assert_called_once()

        with mock.patch(
            "src.data.price_history.get_price_history",
            return_value=([0.5] * 30, [1000] * 30),
        ), mock.patch(
            "src.trading.signal_filter._enrich_with_timesfm",
        ) as mock_enrich:
            result = score_markets(markets, use_timesfm=False)
            mock_enrich.assert_not_called()


class TestMarketPredictorTimesFM:
    @pytest.fixture
    def trained_predictor(self):
        p = MarketPredictor()
        train_data = []
        for i in range(50):
            train_data.append({
                "yes_price": 0.3 + (i % 10) * 0.05,
                "volume": 50000 + i * 1000,
                "days_to_close": max(1, 30 - i),
                "price_velocity": 0.01 * (i % 5),
                "bid_ask_spread": 0.02,
                "question": "Will event X happen? crypto",
                "outcome": "yes" if i < 30 else "no",
                "timestamp": f"2025-01-{max(1, 30 - i):02d}",
            })
        p.train(train_data)
        return p

    def test_predict_without_timesfm_signal(self, trained_predictor):
        prob = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
        )
        assert 0.02 <= prob <= 0.98

    def test_predict_with_timesfm_bullish_blend(self, trained_predictor):
        timesfm_signal = {"direction": 1, "confidence": 0.8}
        prob_with = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
            timesfm_signal=timesfm_signal,
        )
        prob_without = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
        )
        assert prob_with >= prob_without

    def test_predict_with_timesfm_bearish_blend(self, trained_predictor):
        timesfm_signal = {"direction": -1, "confidence": 0.8}
        prob_with = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
            timesfm_signal=timesfm_signal,
        )
        prob_without = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
        )
        assert prob_with <= prob_without

    def test_predict_low_confidence_no_blend(self, trained_predictor):
        timesfm_signal = {"direction": 1, "confidence": 0.3}
        prob_with = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
            timesfm_signal=timesfm_signal,
        )
        prob_without = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True, days_to_close=10,
        )
        assert prob_with == pytest.approx(prob_without, abs=0.001)

    def test_predict_blend_clamped(self, trained_predictor):
        timesfm_signal = {"direction": 1, "confidence": 0.95}
        prob = trained_predictor.predict_win_probability(
            price=0.98, volume=50000, is_crypto=True, days_to_close=1,
            timesfm_signal=timesfm_signal,
        )
        assert prob <= 0.98

    def test_fallback_predictor_with_signal(self):
        p = MarketPredictor()
        prob_without = p.predict_win_probability(price=0.5, volume=50000)
        prob_with = p.predict_win_probability(
            price=0.5, volume=50000,
            timesfm_signal={"direction": 1, "confidence": 0.8},
        )
        assert prob_with == pytest.approx(prob_without + 0.064, abs=0.001)

    def test_timesfm_signal_none(self, trained_predictor):
        prob = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True,
        )
        prob_none = trained_predictor.predict_win_probability(
            price=0.45, volume=50000, is_crypto=True,
            timesfm_signal=None,
        )
        assert prob == prob_none
