import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import pickle
import os


@dataclass
class Prediction:
    symbol: str
    direction: str
    confidence: float
    price_target: float
    timestamp: datetime


class MarketPredictor:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.scaler = None
        self.feature_names = [
            'price_change', 'volume_change', 'volatility',
            'rsi', 'macd', 'bb_position', 'volume_ratio'
        ]
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        features = []
        
        df = df.copy()
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change() if 'volume' in df.columns else 0
        df['volatility'] = df['close'].rolling(10).std()
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        
        bb = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_position'] = (df['close'] - bb) / (2 * bb_std + 1e-10)
        
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean() if 'volume' in df.columns else 1
        
        df = df.dropna()
        
        for name in self.feature_names:
            if name in df.columns:
                features.append(df[name].values)
        
        return np.column_stack(features) if features else np.array([])

    def create_labels(self, df: pd.DataFrame, threshold: float = 0.02) -> np.ndarray:
        future_returns = df['close'].shift(-1) / df['close'] - 1
        labels = np.where(future_returns > threshold, 1,
                np.where(future_returns < -threshold, -1, 0))
        return labels[:-1]

    def train(self, df: pd.DataFrame) -> dict:
        X = self.prepare_features(df)
        y = self.create_labels(df)
        
        if len(X) != len(y):
            min_len = min(len(X), len(y))
            X = X[:min_len]
            y = y[:min_len]
        
        self.scaler = lambda x: (x - x.mean()) / (x.std() + 1e-10)
        X_scaled = self.scaler(X)
        
        from sklearn.linear_model import LogisticRegression
        self.model = LogisticRegression(max_iter=200)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        return {"status": "trained", "samples": len(X)}

    def predict(self, df: pd.DataFrame) -> List[Prediction]:
        if not self.is_trained:
            return []
        
        X = self.prepare_features(df)
        if len(X) == 0:
            return []
        
        X_scaled = self.scaler(X)
        last_features = X_scaled[-1:]
        
        logits = last_features @ self.model
        probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        
        direction_idx = np.argmax(probs[0])
        directions = ['SELL', 'HOLD', 'BUY']
        
        current_price = df['close'].iloc[-1]
        target_change = (probs[0][2] - probs[0][0]) * 0.05
        
        return [Prediction(
            symbol=df.get('symbol', 'UNKNOWN').iloc[-1] if hasattr(df.get('symbol'), 'iloc') else 'UNKNOWN',
            direction=directions[direction_idx],
            confidence=float(probs[0][direction_idx]),
            price_target=current_price * (1 + target_change),
            timestamp=datetime.now()
        )]

    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler}, f)

    def load(self, path: str):
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = True


class EnsemblePredictor:
    def __init__(self):
        self.predictors: List[MarketPredictor] = []
    
    def add_predictor(self, predictor: MarketPredictor):
        self.predictors.append(predictor)
    
    def predict(self, df: pd.DataFrame) -> Optional[Prediction]:
        if not self.predictors:
            return None
        
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        total_confidence = 0
        
        for predictor in self.predictors:
            preds = predictor.predict(df)
            if preds:
                votes[preds[0].direction] += 1
                total_confidence += preds[0].confidence
        
        direction = max(votes, key=votes.get)
        confidence = total_confidence / len(self.predictors) if self.predictors else 0
        
        return Prediction(
            symbol=df.get('symbol', 'UNKNOWN'),
            direction=direction,
            confidence=confidence,
            price_target=df['close'].iloc[-1] if len(df) > 0 else 0,
            timestamp=datetime.now()
        )