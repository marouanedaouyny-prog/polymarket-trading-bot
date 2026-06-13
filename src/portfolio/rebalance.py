from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class Position:
    symbol: str
    amount: float
    value: float
    weight: float
    pnl: float = 0.0


@dataclass
class RebalanceAction:
    symbol: str
    action: str  # 'BUY' or 'SELL'
    amount: float
    current_weight: float
    target_weight: float


class PortfolioRebalancer:
    def __init__(
        self,
        total_value: float,
        target_weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.05,
        max_weight: float = 0.3
    ):
        self.total_value = total_value
        self.target_weights = target_weights or {}
        self.threshold = threshold
        self.max_weight = max_weight
        self.positions: Dict[str, Position] = {}

    def set_positions(self, positions: Dict[str, dict]):
        self.positions = {
            symbol: Position(
                symbol=symbol,
                amount=pos.get('amount', 0),
                value=pos.get('value', 0),
                weight=pos.get('value', 0) / self.total_value if self.total_value > 0 else 0,
                pnl=pos.get('pnl', 0)
            )
            for symbol, pos in positions.items()
        }

    def set_target_weights(self, weights: Dict[str, float]):
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            weights = {k: v / total for k, v in weights.items()}
        
        for symbol, weight in weights.items():
            if weight > self.max_weight:
                weights[symbol] = self.max_weight
        
        self.target_weights = weights

    def get_actions(self) -> List[RebalanceAction]:
        actions = []
        
        for symbol, target_weight in self.target_weights.items():
            current_pos = self.positions.get(symbol)
            current_weight = current_pos.weight if current_pos else 0
            diff = target_weight - current_weight
            
            if abs(diff) > self.threshold:
                target_value = self.total_value * target_weight
                current_value = (current_pos.value if current_pos else 0)
                value_diff = target_value - current_value
                
                actions.append(RebalanceAction(
                    symbol=symbol,
                    action='BUY' if value_diff > 0 else 'SELL',
                    amount=abs(value_diff),
                    current_weight=current_weight,
                    target_weight=target_weight
                ))
        
        return sorted(actions, key=lambda x: abs(x.amount), reverse=True)

    def optimize_weights(self, expected_returns: Dict[str, float], risk_free_rate: float = 0.02) -> Dict[str, float]:
        if not expected_returns:
            return self.target_weights
        
        symbols = list(expected_returns.keys())
        n = len(symbols)
        
        returns = np.array([expected_returns[s] for s in symbols])
        cov = np.eye(n) * 0.01
        
        if n == 1:
            return {symbols[0]: 1.0}
        
        try:
            inv_cov = np.linalg.inv(cov + np.eye(n) * 0.001)
            weights = inv_cov @ returns
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum() if weights.sum() > 0 else np.ones(n) / n
            
            result = {symbols[i]: min(float(weights[i]), self.max_weight) for i in range(n)}
            
            remaining = 1.0 - sum(result.values())
            if remaining > 0:
                for s in result:
                    result[s] += remaining / n
            
            return result
        except:
            return {s: 1.0 / n for s in symbols}

    def get_stats(self) -> dict:
        total_pnl = sum(p.pnl for p in self.positions.values())
        current_weights = {s: p.weight for s, p in self.positions.items()}
        
        weight_diff = {}
        for symbol, target in self.target_weights.items():
            current = current_weights.get(symbol, 0)
            weight_diff[symbol] = target - current
        
        return {
            "total_value": self.total_value,
            "total_pnl": total_pnl,
            "num_positions": len(self.positions),
            "largest_position": max(self.positions.values(), key=lambda x: x.weight).symbol if self.positions else None,
            "weight_drift": {s: abs(d) for s, d in weight_diff.items()}
        }