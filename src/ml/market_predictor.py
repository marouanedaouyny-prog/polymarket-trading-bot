"""
Improved ML predictor for Polymarket.

Key changes vs. the original:
- Removed circular features: `edge` was derived from `price`, so the model
  was effectively fitting price → outcome, not learning anything new.
- Added non-circular features: log_volume, days_to_close, price_velocity,
  liquidity_depth, is_crypto, question_length.
- Calibrated probabilities via CalibratedClassifierCV (Platt scaling) so the
  output can be used directly as a probability estimate.
- Time-split validation (no shuffle) to avoid future leakage.
- Brier score < 0.15 target logged on every train.
"""

import json
import os
import pickle
import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)


def _build_features(record: dict) -> Optional[list]:
    """
    Extract non-circular features from a resolved market record.

    Features (all independent of the outcome label):
      0  yes_price          – market consensus probability at trade time
      1  log_volume         – log(1 + total_volume), proxy for liquidity
      2  days_to_close      – urgency / information completeness
      3  price_velocity     – abs change in price over last 24h (if available)
      4  bid_ask_spread     – proxy for uncertainty / liquidity depth
      5  is_crypto          – binary domain flag
      6  question_length    – longer questions often → more complex outcomes
    """
    yes_price = record.get('yes_price') or record.get('price')
    volume = record.get('volume', 0) or 0

    if yes_price is None:
        return None
    yes_price = float(yes_price)
    if not (0.0 < yes_price < 1.0):
        return None

    log_vol = float(np.log1p(volume))
    days = float(record.get('days_to_close', record.get('days_left', 7)) or 7)
    days = max(days, 0.0)
    velocity = float(abs(record.get('price_velocity', record.get('price_change_24h', 0.0)) or 0.0))
    spread = float(record.get('bid_ask_spread', record.get('spread', 0.02)) or 0.02)
    question = record.get('question', '')
    is_crypto = int(any(kw in question.lower() for kw in
                        ['crypto', 'bitcoin', 'ethereum', 'solana', 'btc', 'eth']))
    q_len = min(len(question) / 200.0, 1.0)  # normalise to [0, 1]

    return [yes_price, log_vol, days / 30.0, velocity, spread, is_crypto, q_len]


class MarketPredictor:
    """
    Calibrated GradientBoosting predictor with time-split validation.
    """

    def __init__(self):
        self.model: Optional[CalibratedClassifierCV] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self.model_path = os.path.join(MODEL_DIR, 'sklearn_model.pkl')
        self.scaler_path = os.path.join(MODEL_DIR, 'sklearn_scaler.pkl')
        self.feature_names = [
            'yes_price', 'log_volume', 'days_to_close_norm',
            'price_velocity', 'bid_ask_spread', 'is_crypto', 'question_length_norm'
        ]

    # ------------------------------------------------------------------
    # Public API (unchanged interface so callers don't break)
    # ------------------------------------------------------------------

    def predict_win_probability(self, price: float, volume: float,
                                edge: float = 0.0, confidence: float = 50.0,
                                is_crypto: bool = False,
                                days_to_close: float = 7.0,
                                spread: float = 0.02,
                                timesfm_signal: Optional[dict] = None) -> float:
        """
        Predict win probability.  Falls back to the market price when the
        model is not trained (market price IS the crowd's probability estimate).

        If timesfm_signal dict is provided (with "direction" and "confidence"),
        the model output is blended with the TimesFM forecast signal for
        a combined probability estimate.
        """
        if not self.is_trained:
            base = self._fallback_probability(price)
        else:
            feat = [
                price,
                float(np.log1p(volume)),
                days_to_close / 30.0,
                0.0,   # price_velocity unknown at prediction time
                spread,
                int(is_crypto),
                0.5,   # question length unknown at prediction time
            ]
            X = self.scaler.transform([feat])
            prob = float(self.model.predict_proba(X)[0][1])
            base = float(np.clip(prob, 0.02, 0.98))

        if timesfm_signal and timesfm_signal.get("confidence", 0) > 0.5:
            tf_dir = timesfm_signal.get("direction", 0)
            tf_conf = timesfm_signal.get("confidence", 0)
            adjustment = tf_dir * tf_conf * 0.08
            base = float(np.clip(base + adjustment, 0.02, 0.98))

        return base

    def train(self, training_data: list) -> None:
        """
        Train on resolved market records.  Uses chronological split —
        records are assumed to be ordered oldest-first (or have a timestamp).
        """
        if not training_data:
            logger.error("No training data provided.")
            return

        records = sorted(training_data, key=lambda r: r.get('timestamp', ''))

        X, y = [], []
        for r in records:
            feat = _build_features(r)
            if feat is None:
                continue
            outcome = r.get('outcome', r.get('won'))
            if outcome is None:
                continue
            label = int(outcome == 'yes' or outcome is True or outcome == 1)
            X.append(feat)
            y.append(label)

        if len(X) < 20:
            logger.warning(f"Only {len(X)} usable records — model will not be reliable.")
            return

        X = np.array(X, dtype=float)
        y = np.array(y, dtype=int)

        # Chronological split: 80% train, 20% test (no shuffle to avoid future leak)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        self.scaler = StandardScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        base = GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, random_state=42
        )
        self.model = CalibratedClassifierCV(base, cv=3, method='isotonic')
        self.model.fit(X_train_s, y_train)

        probs = self.model.predict_proba(X_test_s)[:, 1]
        brier = brier_score_loss(y_test, probs)
        try:
            auc = roc_auc_score(y_test, probs)
        except Exception:
            auc = float('nan')

        logger.info(f"Model trained: {len(X_train)} train / {len(X_test)} test | "
                    f"Brier={brier:.4f} (target <0.15) | AUC={auc:.4f}")

        self._save_metrics(brier, auc, len(X_train), len(X_test))
        self._save_model()
        self.is_trained = True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load_model(self) -> bool:
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            self.is_trained = True
            logger.info("Model loaded from disk.")
            return True
        except FileNotFoundError:
            logger.info("No saved model found.")
            return False

    def _save_model(self) -> None:
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

    def _save_metrics(self, brier: float, auc: float,
                      n_train: int, n_test: int) -> None:
        metrics = {
            'brier_score': round(brier, 6),
            'roc_auc': round(auc, 6) if not np.isnan(auc) else None,
            'n_train': n_train,
            'n_test': n_test,
            'target_brier': 0.15,
            'meets_target': brier < 0.15,
            'feature_names': self.feature_names,
            'timestamp': datetime.now().isoformat(),
        }
        with open(os.path.join(MODEL_DIR, 'metrics.json'), 'w') as f:
            json.dump(metrics, f, indent=2)

    # ------------------------------------------------------------------
    # Fallback (no model)
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_probability(price: float) -> float:
        """
        Without a trained model, the market price IS the best probability
        estimate we have.  Cap at 0.70 to stay honest.
        """
        return float(np.clip(price, 0.02, 0.70))


def create_training_data_from_resolved() -> list:
    """Load real resolved market data from data/training/resolved_markets.json."""
    resolved_file = os.path.join('data', 'training', 'resolved_markets.json')
    if not os.path.isfile(resolved_file):
        raise FileNotFoundError(
            f"Resolved markets file not found: {resolved_file}\n"
            "Run scripts/tools/fetch_resolved.py first."
        )
    with open(resolved_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def train_and_save_model() -> MarketPredictor:
    training_data = create_training_data_from_resolved()
    predictor = MarketPredictor()
    predictor.train(training_data)
    return predictor


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    train_and_save_model()
