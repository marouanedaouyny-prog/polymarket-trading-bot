# Feature Engineering Pipeline
# Processes market data to extract relevant features for ML models

import pandas as pd
import numpy as np
from typing import Dict, List
import math

class FeatureEngineer:
    def __init__(self):
        self.feature_cache = {}

    def calculate_price_momentum(self, current_price: float, previous_price: float) -> float:
        """Calculate price momentum indicator"""
        if previous_price == 0:
            return 0
        return (current_price - previous_price) / previous_price

    def calculate_orderbook_imbalance(self, bids: List[float], asks: List[float]) -> float:
        """Calculate order book imbalance"""
        total_bids = sum(bids) if bids else 0
        total_asks = sum(asks) if asks else 0

        if total_bids + total_asks == 0:
            return 0

        return (total_bids - total_asks) / (total_bids + total_asks)

    def calculate_volatility(self, prices: List[float], window: int = 10) -> float:
        """Calculate volatility over a given window"""
        if len(prices) < window:
            return 0

        recent_prices = prices[-window:]
        if len(recent_prices) < 2:
            return 0

        # Calculate standard deviation of returns
        returns = [0]
        for i in range(1, len(recent_prices)):
            returns.append((recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1])

        # Standard deviation of returns
        if len(returns) > 1:
            return np.std(returns)
        return 0

    def calculate_liquidity_score(self, volume: float, spread: float) -> float:
        """Calculate liquidity score based on volume and spread"""
        if spread == 0:
            return 0
        return volume / spread

    def extract_features(self, market_data: Dict) -> Dict:
        """Extract features from market data"""
        features = {}

        # Extract basic features
        if 'price' in market_data:
            features['current_price'] = market_data['price']

        if 'previous_price' in market_data:
            features['price_momentum'] = self.calculate_price_momentum(
                market_data['price'],
                market_data['previous_price']
            )

        if 'bids' in market_data and 'asks' in market_data:
            features['orderbook_imbalance'] = self.calculate_orderbook_imbalance(
                market_data['bids'],
                market_data['asks']
            )

        # Add more features as needed
        return features