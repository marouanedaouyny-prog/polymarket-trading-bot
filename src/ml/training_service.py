"""
Model training service used by API order flow.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def _import_model_class():
    """Import PricePredictionModel from local models.py."""
    try:
        from .models import PricePredictionModel
        return PricePredictionModel
    except ImportError:
        from src.ml.models import PricePredictionModel
        return PricePredictionModel


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_price(market: Dict) -> float:
    price = _to_float(
        market.get("lastTradePrice")
        or market.get("yes_price")
        or market.get("yesPrice")
        or market.get("price")
        or market.get("probability")
    )
    if price > 0:
        return price

    outcome_prices = market.get("outcomePrices")
    parsed = outcome_prices
    if isinstance(outcome_prices, str):
        try:
            parsed = json.loads(outcome_prices)
        except json.JSONDecodeError:
            parsed = None

    if isinstance(parsed, list) and parsed:
        return _to_float(parsed[0], 0.0)

    return 0.0


def _extract_volume(market: Dict) -> float:
    return _to_float(
        market.get("volumeNum")
        or market.get("volume")
        or market.get("volume24hr")
        or market.get("liquidityNum")
        or market.get("liquidity")
    )


class TrainingService:
    """Wraps model training lifecycle and status."""

    def __init__(self):
        model_class = _import_model_class()
        self.model = model_class()
        self.last_trained_at: Optional[datetime] = None
        self.last_training_rows: int = 0
        self.last_training_ok: bool = False
        self.last_training_error: Optional[str] = None

    def _build_training_dataframe(self, markets: List[Dict]) -> pd.DataFrame:
        rows = []
        for market in markets:
            price = _extract_price(market)
            volume = _extract_volume(market)
            if price > 0 and volume >= 0:
                rows.append({"price": price, "volume": volume})
        return pd.DataFrame(rows)

    def _within_cooldown(self) -> bool:
        if not self.last_trained_at:
            return False
        min_interval = int(os.getenv("TRAINING_MIN_INTERVAL_SECONDS", "300"))
        elapsed = (datetime.now(timezone.utc) - self.last_trained_at).total_seconds()
        return elapsed < min_interval

    def train_from_markets(self, markets: List[Dict], force: bool = False) -> Dict:
        """
        Train model from latest market snapshot.
        Returns details for API responses/logging.
        """
        if self.model.is_trained and self._within_cooldown() and not force:
            return {
                "trained": True,
                "skipped": True,
                "reason": "cooldown_active",
                "rows": self.last_training_rows,
            }

        df = self._build_training_dataframe(markets)
        row_count = len(df)
        self.last_training_rows = row_count

        if row_count < 10:
            self.last_training_ok = False
            self.last_training_error = "insufficient_rows"
            return {
                "trained": False,
                "skipped": False,
                "reason": "insufficient_rows",
                "rows": row_count,
            }

        ok = bool(self.model.train(df))
        self.last_training_ok = ok
        self.last_training_error = None if ok else "training_failed"
        self.last_trained_at = datetime.now(timezone.utc) if ok else self.last_trained_at

        return {
            "trained": ok,
            "skipped": False,
            "rows": row_count,
            "xgb_backend": getattr(self.model, "xgb_backend", "unknown"),
            "lgb_backend": getattr(self.model, "lgb_backend", "unknown"),
        }

    def status(self) -> Dict:
        """Return training status snapshot."""
        return {
            "is_trained": bool(self.model.is_trained),
            "last_trained_at": self.last_trained_at.isoformat() if self.last_trained_at else None,
            "last_training_rows": self.last_training_rows,
            "last_training_ok": self.last_training_ok,
            "last_training_error": self.last_training_error,
            "xgb_backend": getattr(self.model, "xgb_backend", "unknown"),
            "lgb_backend": getattr(self.model, "lgb_backend", "unknown"),
        }

    def evaluate_buy_signal(
        self,
        market: Dict,
        fallback_price: Optional[float] = None,
        fallback_volume: Optional[float] = None,
    ) -> Dict:
        """
        Evaluate whether buy should be allowed from model prediction.
        Returns allow_buy + diagnostics.
        """
        if not self.model.is_trained:
            return {
                "allow_buy": False,
                "reason": "model_not_trained",
            }

        current_price = _extract_price(market)
        current_volume = _extract_volume(market)
        if current_price <= 0 and fallback_price is not None:
            current_price = float(fallback_price)
        if current_volume <= 0 and fallback_volume is not None:
            current_volume = float(fallback_volume)

        features = {
            "price": current_price,
            "volume": current_volume,
            "price_momentum": 0.0,
            "volatility": 0.0,
            "volume_sma": current_volume,
        }
        preds = self.model.predict(features)
        if "error" in preds:
            return {
                "allow_buy": False,
                "reason": preds["error"],
            }

        pred_xgb = preds.get("xgboost")
        pred_lgb = preds.get("lightgbm")
        pred_values = [v for v in [pred_xgb, pred_lgb] if v is not None]
        if not pred_values:
            return {
                "allow_buy": False,
                "reason": "no_prediction",
            }

        predicted_price = float(sum(pred_values) / len(pred_values))
        edge = predicted_price - float(current_price)
        min_edge = float(os.getenv("BUY_EDGE_THRESHOLD", "0.01"))
        edge_pct = 0.0
        if current_price > 0:
            edge_pct = edge / float(current_price)
        min_edge_pct = float(os.getenv("BUY_EDGE_PCT_THRESHOLD", "0.03"))
        allow_buy = edge >= min_edge and edge_pct >= min_edge_pct

        return {
            "allow_buy": allow_buy,
            "current_price": float(current_price),
            "predicted_price": predicted_price,
            "edge": edge,
            "edge_pct": edge_pct,
            "required_edge": min_edge,
            "required_edge_pct": min_edge_pct,
            "xgb_backend": preds.get("xgb_backend"),
            "lgb_backend": preds.get("lgb_backend"),
        }
