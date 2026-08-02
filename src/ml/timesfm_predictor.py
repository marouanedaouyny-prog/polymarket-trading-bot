from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class TimesFMPredictor:
    _instance: Optional[TimesFMPredictor] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "google/timesfm-2.5-200m-pytorch"):
        if self._initialized:
            return
        self._initialized = True
        self.model_name = model_name
        self._model = None
        self._loaded = False

    def load_model(self) -> bool:
        if self._loaded:
            return True
        try:
            import torch
            import timesfm

            torch.set_float32_matmul_precision("high")

            self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(self.model_name)
            self._model.compile(timesfm.ForecastConfig(
                max_context=1024,
                max_horizon=256,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            ))
            self._loaded = True
            logger.info("TimesFM 2.5 model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load TimesFM model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def forecast(
        self,
        prices: list[float],
        horizon: int = 12,
    ) -> Optional[tuple[np.ndarray, np.ndarray]]:
        if len(prices) < 20:
            logger.debug(f"Price series too short ({len(prices)}), need >= 20")
            return None
        if not self._loaded:
            if not self.load_model():
                return None

        try:
            inputs = np.array(prices[-1024:], dtype=np.float64)
            point, quantile = self._model.forecast(
                horizon=horizon,
                inputs=[inputs],
            )
            return point, quantile
        except Exception as e:
            logger.error(f"TimesFM forecast failed: {e}")
            return None

    def get_trend_signal(
        self,
        prices: list[float],
        horizon: int = 12,
    ) -> dict:
        result = self.forecast(prices, horizon=horizon)
        if result is None:
            return {"direction": 0, "confidence": 0.0, "reason": "forecast unavailable"}

        point, quantile = result
        forecast_series = point[0]
        current_price = prices[-1]

        weights = np.linspace(0.5, 1.0, len(forecast_series))
        weighted_forecast = float(np.average(forecast_series, weights=weights))
        price_change = weighted_forecast - current_price

        quantile_lower = float(quantile[0, -1, 1])
        quantile_upper = float(quantile[0, -1, -1])
        uncertainty = quantile_upper - quantile_lower

        direction = 1 if price_change > 0 else (-1 if price_change < 0 else 0)
        magnitude_conf = min(abs(price_change) / 0.10, 0.95)
        uncertainty_penalty = min(uncertainty * 2.0, 0.5)
        confidence = max(magnitude_conf - uncertainty_penalty, 0.0)
        confidence = min(confidence, 0.95)

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "current_price": current_price,
            "weighted_forecast": round(weighted_forecast, 6),
            "forecast_end": float(forecast_series[-1]),
            "forecast_series": [float(x) for x in forecast_series],
            "uncertainty": round(uncertainty, 6),
            "reason": (
                f"bullish ({price_change:+.4f} exp)" if direction > 0
                else f"bearish ({price_change:+.4f} exp)" if direction < 0
                else "neutral"
            ),
        }

    def get_quantile_forecast(
        self,
        prices: list[float],
        horizon: int = 12,
        quantile_idx: int = 5,
    ) -> Optional[float]:
        result = self.forecast(prices, horizon=horizon)
        if result is None:
            return None
        _, quantile = result
        return float(quantile[0, -1, quantile_idx])
