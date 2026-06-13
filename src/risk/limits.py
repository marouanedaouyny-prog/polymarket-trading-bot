"""
Risk management module for position limits and controls.
"""

class RiskManager:
    """Advanced risk management controls."""

    def __init__(self):
        self.max_position_size = 0.05  # 5% default
        self.daily_loss_limit = -0.05  # -5% default
        self.max_drawdown_limit = -0.10  # -10% default
        self.current_positions = {}
        self.daily_pnl = 0.0
        self.kill_switch_activated = False

    def check_position_size(self, market_id: str, proposed_size: float) -> bool:
        """Check if proposed position size is within limits."""
        current_position = self.current_positions.get(market_id, 0.0)
        new_position = current_position + proposed_size
        return abs(new_position) <= self.max_position_size

    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit has been exceeded."""
        return self.daily_pnl >= self.daily_loss_limit

    def check_max_drawdown(self, current_drawdown: float) -> bool:
        """Check if maximum drawdown limit has been exceeded."""
        return current_drawdown >= self.max_drawdown_limit

    def emergency_kill_switch(self) -> bool:
        """Emergency stop for all trading activities."""
        self.kill_switch_activated = True
        return True

    def set_position(self, market_id: str, position_size: float):
        """Set the current position for a market."""
        self.current_positions[market_id] = position_size

    def update_daily_pnl(self, pnl: float):
        """Update the daily PnL."""
        self.daily_pnl = pnl

    def check_risk_limits(self) -> dict:
        """Return current risk settings."""
        return {
            "max_position_size": self.max_position_size,
            "daily_loss_limit": self.daily_loss_limit,
            "max_drawdown_limit": self.max_drawdown_limit,
            "kill_switch_activated": self.kill_switch_activated
        }