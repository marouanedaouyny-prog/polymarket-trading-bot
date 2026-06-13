"""
Real ML Model using sklearn LogisticRegression
Trained on market data features
"""

import json
import os
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pickle

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

class MarketPredictor:
    """
    ML Model that predicts win probability based on market features:
    - price
    - volume
    - edge (calculated from price tier)
    - confidence (calculated from price + volume)
    - sector (crypto vs other)
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.model_path = os.path.join(MODEL_DIR, 'sklearn_model.pkl')
        self.scaler_path = os.path.join(MODEL_DIR, 'sklearn_scaler.pkl')
        
    def _calculate_features(self, price, volume, edge, confidence, is_crypto):
        """Calculate feature vector"""
        return [
            price,
            np.log1p(volume) if volume else 0,
            edge,
            confidence / 100.0,  # Normalize
            1.0 if is_crypto else 0.0
        ]
    
    def train(self, training_data):
        """
        Train the model on historical data
        
        training_data: list of dicts with keys:
            - price, volume, edge, confidence, is_crypto, won
        """
        if not training_data:
            print("No training data provided")
            return
            
        X = []
        y = []
        
        for record in training_data:
            features = self._calculate_features(
                record['price'],
                record.get('volume', 15000),
                record['edge'],
                record['confidence'],
                record.get('is_crypto', False)
            )
            X.append(features)
            y.append(1 if record['won'] else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        
        # Save model
        self._save_model()
        
        self.is_trained = True
        print(f"Model trained on {len(X)} samples")
        # Evaluate on a hold‑out set and save metrics
        self._evaluate_and_save_metrics(X_scaled, y)
    
    def _evaluate_and_save_metrics(self, X_scaled, y):
        """Compute advanced evaluation metrics and store them."""
        from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix, f1_score, brier_score_loss
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y)
        
        # Get probability predictions
        probs = self.model.predict_proba(X_test)[:, 1]
        # Get binary labels
        pred_labels = (probs >= 0.5).astype(int)
        
        # Core Metrics
        acc = accuracy_score(y_test, pred_labels)
        f1 = f1_score(y_test, pred_labels)
        brier = brier_score_loss(y_test, probs)
        
        try:
            auc = roc_auc_score(y_test, probs)
        except Exception:
            auc = None
            
        cm = confusion_matrix(y_test, pred_labels).tolist()
        
        # Profitability Proxy (Expectancy)
        # Assuming avg price of 0.20 (4:1 payout)
        avg_price = 0.20
        win_payout = (1 / avg_price) - 1
        expectancy = (probs.mean() * win_payout) - ((1 - probs.mean()) * 1.0)
        
        metrics = {
            'accuracy': acc,
            'f1_score': f1,
            'brier_score': brier, # Lower is better
            'roc_auc': auc,
            'confusion_matrix': cm,
            'avg_prediction': float(probs.mean()),
            'simulated_expectancy': float(expectancy),
            'samples': len(y_test),
            'timestamp': datetime.now().isoformat()
        }
        
        metrics_path = os.path.join(MODEL_DIR, 'metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Deep evaluation saved to {metrics_path}")

        
    def _save_model(self):
        """Save model and scaler to disk"""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"Model saved to {self.model_path}")
        
    def load_model(self):
        """Load model from disk"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            self.is_trained = True
            print("Model loaded from disk")
            return True
        except FileNotFoundError:
            print("No saved model found")
            return False
    
    def predict_win_probability(self, price, volume, edge, confidence, is_crypto=False):
        """
        Predict win probability using the trained model
        
        Returns probability between 0 and 1
        """
        if not self.is_trained:
            # Fallback to rule-based if model not trained
            return self._rule_based_probability(price, edge, confidence)
        
        features = np.array([self._calculate_features(
            price, volume, edge, confidence, is_crypto
        )])
        
        features_scaled = self.scaler.transform(features)
        
        # Get probability of winning (class 1)
        prob = self.model.predict_proba(features_scaled)[0][1]
        
        return min(max(prob, 0.3), 0.99)  # Clamp between 30% and 99%
    
    def _rule_based_probability(self, price, edge, confidence):
        """Fallback probability calculation"""
        # Price tier based
        if price <= 0.02:
            base = 0.96
        elif price <= 0.05:
            base = 0.93
        elif price <= 0.10:
            base = 0.89
        elif price <= 0.15:
            base = 0.85
        elif price <= 0.20:
            base = 0.82
        else:
            base = 0.74
        
        # Confidence adjustment
        if confidence >= 80:
            base = min(base + 0.03, 0.99)
        elif confidence < 65:
            base = max(base - 0.05, 0.50)
            
        return base


def create_training_data_from_resolved():
    """Create training data from actual resolved market outcomes.
    Uses the JSON file generated by fetch_resolved.py.
    """
    resolved_file = os.path.join('data', 'training', 'resolved_markets.json')
    if not os.path.isfile(resolved_file):
        raise FileNotFoundError(f"Resolved markets file not found: {resolved_file}")
    
    with open(resolved_file, 'r', encoding='utf-8') as f:
        resolved = json.load(f)
    
    training_data = []
    for m in resolved:
        price = (m.get('yes_price', 0) + (1 - m.get('no_price', 0))) / 2
        volume = m.get('volume', 0)
        # Derive edge from price tier (same mapping as in backtest)
        if price <= 0.02:
            edge = 0.96
        elif price <= 0.05:
            edge = 0.93
        elif price <= 0.10:
            edge = 0.89
        elif price <= 0.15:
            edge = 0.85
        elif price <= 0.20:
            edge = 0.82
        else:
            edge = 0.74
        confidence = min(100, max(65, price * 100))  # simple proxy
        is_crypto = any(kw in m.get('question', '').lower() for kw in ['crypto', 'bitcoin', 'ethereum', 'solana'])
        won = (m.get('outcome') == 'yes')
        
        training_data.append({
            'price': price,
            'volume': volume,
            'edge': edge,
            'confidence': confidence,
            'is_crypto': is_crypto,
            'won': won
        })
    
    print(f"Loaded {len(training_data)} resolved training samples")
    return training_data


def train_and_save_model():
    """Train the model on real resolved market data and save it"""
    # Generate training data from actual resolved markets
    training_data = create_training_data_from_resolved()
    
    # Create and train model
    predictor = MarketPredictor()
    predictor.train(training_data)
    
    # Test prediction
    prob = predictor.predict_win_probability(
        price=0.02,
        volume=50000,
        edge=0.95,
        confidence=90,
        is_crypto=True
    )
    print(f"Test prediction: {prob:.2%} win probability")
    
    return predictor


if __name__ == "__main__":
    train_and_save_model()