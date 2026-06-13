# Risk Management System
# Implements risk controls and position sizing

import asyncio
from typing import Dict, List
import math

class RiskManager:
    def __init__(self):
        # Risk limits
        self.max_drawdown_limit = 0.10  # 10% maximum drawdown
        self.max_position_size = 0.05   # 5% of portfolio per position
        self.daily_loss_limit = 0.05    # 5% daily loss limit
        self.trading_halted = False

    def calculate_position_size(self, account_balance: float, risk_per_trade: float = 0.01) -> float:
        """Calculate position size based on risk management rules"""
        # Risk 1% of account per trade
        position_size = account_balance * risk_per_trade
        return min(position_size, account_balance * self.max_position_size)

    def check_drawdown(self, current_value: float, peak_value: float) -> bool:
        """Check if drawdown limits are exceeded"""
        if peak_value == 0:
            return False

        drawdown = (peak_value - current_value) / peak_value
        return drawdown > self.max_drawdown_limit

    def emergency_stop(self) -> bool:
        """Emergency stop for all trading activities"""
        self.trading_halted = True
        return True

    def resume_trading(self) -> bool:
        """Resume trading after emergency stop"""
        self.trading_halted = False
        return True

    def validate_trade(self, position_size: float, account_balance: float) -> bool:
        """Validate if a trade is within risk limits"""
        # Check if position size is within limits
        max_allowed_size = account_balance * self.max_position_size
        return position_size <= max_allowed_size and not self.trading_halted