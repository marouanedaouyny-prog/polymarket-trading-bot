# Machine Learning Models for Price Prediction

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from typing import Dict, List, Tuple
import joblib

try:
    import xgboost as xgb
except ImportError:
    xgb = None

try:
    import lightgbm as lgb
except ImportError:
    lgb = None

class PricePredictionModel:
    def __init__(self):
        if xgb is not None:
            self.xgb_model = xgb.XGBRegressor(
                n_estimators=100,
                random_state=42
            )
            self.xgb_backend = "xgboost"
        else:
            self.xgb_model = RandomForestRegressor(
                n_estimators=200,
                random_state=42
            )
            self.xgb_backend = "random_forest_fallback"

        if lgb is not None:
            self.lgb_model = lgb.LGBMRegressor(
                n_estimators=100,
                random_state=42
            )
            self.lgb_backend = "lightgbm"
        else:
            self.lgb_model = GradientBoostingRegressor(
                random_state=42
            )
            self.lgb_backend = "gradient_boosting_fallback"

        self.is_trained = False
        self.feature_columns = []

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for training"""
        # Create a copy of the data
        df = data.copy()

        # Add technical indicators as features
        df['price_momentum'] = df['price'].pct_change().fillna(0)
        df['volatility'] = df['price'].rolling(window=5).std().fillna(0)
        df['volume_sma'] = df['volume'].rolling(window=5).mean().fillna(0)

        # Select feature columns
        feature_cols = ['price', 'volume', 'price_momentum', 'volatility', 'volume_sma']
        self.feature_columns = [col for col in feature_cols if col in df.columns]

        return df

    def train(self, data: pd.DataFrame):
        """Train the price prediction models"""
        # Prepare the data
        df = self.prepare_features(data)

        # Create target variable (next period price)
        df['target'] = df['price'].shift(-1)

        # Remove rows with NaN values
        df = df.dropna()

        if len(df) < 10:  # Need minimum data to train
            print("Not enough data to train model")
            return False

        # Prepare features and target
        X = df[self.feature_columns]
        y = df['target']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train models
        try:
            self.xgb_model.fit(X_train, y_train)
            self.lgb_model.fit(X_train, y_train)
        except Exception as e:
            print(f"Model training failed: {e}")
            return False

        # Mark as trained
        self.is_trained = True

        # Calculate and print model performance
        xgb_pred = self.xgb_model.predict(X_test)
        lgb_pred = self.lgb_model.predict(X_test)

        print(f"{self.xgb_backend} MSE: {mean_squared_error(y_test, xgb_pred)}")
        print(f"{self.lgb_backend} MSE: {mean_squared_error(y_test, lgb_pred)}")

        return True

    def predict(self, features: Dict) -> Dict:
        """Make predictions using trained models"""
        if not self.is_trained:
            return {"error": "Model not trained yet"}

        # Convert features to DataFrame
        df = pd.DataFrame([features])

        # Make predictions
        xgb_pred = self.xgb_model.predict(df[self.feature_columns])[0] if self.is_trained else None
        lgb_pred = self.lgb_model.predict(df[self.feature_columns])[0] if self.is_trained else None

        return {
            "xgboost": xgb_pred,
            "lightgbm": lgb_pred,
            "xgb_backend": self.xgb_backend,
            "lgb_backend": self.lgb_backend
        }

    def save_model(self, filepath: str):
        """Save the trained models to disk"""
        if self.is_trained:
            joblib.dump(self.xgb_model, f"{filepath}_xgb_model.pkl")
            joblib.dump(self.lgb_model, f"{filepath}_lgb_model.pkl")
            print("Models saved successfully")
        else:
            print("No trained models to save")

    def load_model(self, filepath: str):
        """Load trained models from disk"""
        try:
            self.xgb_model = joblib.load(f"{filepath}_xgb_model.pkl")
            self.lgb_model = joblib.load(f"{filepath}_lgb_model.pkl")
            self.is_trained = True
            print("Models loaded successfully")
        except:
            print("Failed to load models")
