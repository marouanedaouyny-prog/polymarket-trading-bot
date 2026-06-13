"""
Advanced Risk Manager with Dynamic Risk Adjustment
Includes Kelly Criterion, Drawdown Tracking, Adaptive Limits
"""

import json
from datetime import datetime


class DynamicRiskManager:
    """
    Enhanced risk management with:
    - Kelly Criterion for position sizing
    - Real-time drawdown tracking
    - Adaptive loss limits based on streak
    - Volatility adjustment
    """
    
    def __init__(self, base_config=None):
        # Base risk configuration
        self.base = base_config or {
            'max_position_pct': 0.15,
            'max_daily_trades': 20,
            'stop_loss_pct': 0.25,
            'take_profit_pct': 2.0,
            'daily_loss_limit': 0.20,
            'min_edge': 0.65,
            'min_confidence': 65,
        }
        
        # Current adaptive settings
        self.current = self.base.copy()
        
        # Tracking state
        self.peak_balance = 0
        self.current_drawdown = 0
        self.max_drawdown = 0
        
        self.winning_streak = 0
        self.losing_streak = 0
        self.consecutive_losses = 0
        
        self.session_start_balance = 0
        self.daily_start_balance = 0
        
        # Performance tracking
        self.win_rate = 0.95
        self.avg_win = 0
        self.avg_loss = 0
        
    def start_session(self, balance):
        """Initialize for new session"""
        self.session_start_balance = balance
        self.daily_start_balance = balance
        if balance > self.peak_balance:
            self.peak_balance = balance
    
    def update_after_trade(self, won, profit, balance):
        """Update risk parameters after each trade"""
        # Update balance tracking
        if balance > self.peak_balance:
            self.peak_balance = balance
        
        # Calculate drawdown
        if self.peak_balance > 0:
            self.current_drawdown = (self.peak_balance - balance) / self.peak_balance
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
        
        # Track streaks
        if won:
            self.winning_streak += 1
            self.losing_streak = 0
            self.consecutive_losses = 0
        else:
            self.losing_streak += 1
            self.winning_streak = 0
            self.consecutive_losses += 1
        
        # Apply adaptive adjustments
        self._adjust_risk_for_drawdown()
        self._adjust_risk_for_streak()
        
        return self.current
    
    def _adjust_risk_for_drawdown(self):
        """Tighten risk when drawdown increases"""
        # If drawdown > 10%, reduce position size
        if self.current_drawdown > 0.10:
            reduction = min(self.current_drawdown * 2, 0.5)  # Max 50% reduction
            self.current['max_position_pct'] = self.base['max_position_pct'] * (1 - reduction)
        
        # If drawdown > 20%, further reduce
        if self.current_drawdown > 0.20:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.5
            self.current['daily_loss_limit'] = self.base['daily_loss_limit'] * 0.5
        
        # Reset to base if recovered
        if self.current_drawdown < 0.05:
            self.current['max_position_pct'] = self.base['max_position_pct']
            self.current['daily_loss_limit'] = self.base['daily_loss_limit']
    
    def _adjust_risk_for_streak(self):
        """Adjust risk based on winning/losing streaks"""
        # After 5+ consecutive losses, tighten limits
        if self.consecutive_losses >= 5:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.7
            self.current['daily_loss_limit'] = self.base['daily_loss_limit'] * 0.7
        
        # After 10 consecutive losses, go to minimum
        if self.consecutive_losses >= 10:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.5
            self.current['min_edge'] = min(self.base['min_edge'] + 0.10, 0.80)
        
        # Reset after wins
        if self.winning_streak >= 3:
            self.current['max_position_pct'] = self.base['max_position_pct']
            self.current['min_edge'] = self.base['min_edge']
            self.current['daily_loss_limit'] = self.base['daily_loss_limit']
    
    def calculate_kelly_position(self, win_prob, odds):
        """Calculate Kelly position size using win probability.
        Kelly % = (b * p - q) / b where:
          b = odds received on bet (decimal - 1)
          p = win_prob, q = 1 - p
        Returns a fraction of balance.
        """
        p = win_prob
        q = 1 - p
        b = (odds - 1) if odds > 1 else 0
        if b <= 0 or p <= 0:
            return 0.0
        kelly = (b * p - q) / b
        # Use half‑Kelly for safety
        kelly = max(0.01, min(kelly * 0.5, 0.20))
        return kelly

    def configure_from_history(self, stats: dict):
        """Adjust base config based on historical back‑test stats.
        ``stats`` should contain keys: ``win_rate``, ``drawdown``.
        Reduces max_position_pct if drawdown > 10% or win_rate < 60%.
        """
        if stats.get('drawdown', 0) > 0.10:
            self.base['max_position_pct'] = max(0.01, self.base.get('max_position_pct', 0.15) * 0.7)
        if stats.get('win_rate', 100) < 60:
            self.base['max_position_pct'] = max(0.01, self.base.get('max_position_pct', 0.15) * 0.8)
        # Ensure limits stay sensible
        self.base['max_position_pct'] = min(0.20, max(0.01, self.base.get('max_position_pct', 0.15)))

    
    def get_recommended_position(self, balance, edge, price, confidence):
        """Get recommended position size using combination of rules"""
        # Use base config as default
        base_pct = self.current['max_position_pct']
        
        # Try Kelly if edge is high
        if edge >= 0.80 and price > 0:
            kelly_pct = self.calculate_kelly_position(edge, 1/price)
            # Use smaller of Kelly or base
            recommended = min(kelly_pct, base_pct)
        else:
            recommended = base_pct
        
        # Apply drawdown adjustment
        if self.current_drawdown > 0.15:
            recommended *= 0.7
        
        # Apply streak adjustment
        if self.consecutive_losses >= 3:
            recommended *= 0.8
        
        return recommended
    
    def should_trade(self, edge, confidence, balance):
        """Determine if should trade based on current risk state"""
        # Check daily loss limit
        if self.daily_start_balance > 0:
            daily_loss = (self.daily_start_balance - balance) / self.daily_start_balance
            if daily_loss >= self.current['daily_loss_limit']:
                return False, "Daily loss limit reached"
        
        # Check minimum edge
        if edge < self.current['min_edge']:
            return False, f"Edge {edge:.0%} below minimum {self.current['min_edge']:.0%}"
        
        # Check minimum confidence
        if confidence < self.current['min_confidence']:
            return False, f"Confidence {confidence:.0f} below minimum {self.current['min_confidence']}"
        
        return True, "Approved"
    
    def get_risk_metrics(self):
        """Get current risk metrics for monitoring"""
        return {
            'current_position_pct': self.current['max_position_pct'],
            'drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'winning_streak': self.winning_streak,
            'losing_streak': self.losing_streak,
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_pct': (self.daily_start_balance - self.peak_balance) / self.daily_start_balance if self.daily_start_balance > 0 else 0,
        }
    
    def reset_daily(self, balance):
        """Reset daily tracking"""
        self.daily_start_balance = balance
        self.consecutive_losses = 0
    
    def get_summary(self):
        """Get risk manager summary"""
        return {
            'current_config': self.current,
            'peak_balance': self.peak_balance,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'streaks': {'wins': self.winning_streak, 'losses': self.losing_streak}
        }