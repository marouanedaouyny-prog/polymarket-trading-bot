"""
Advanced Risk Manager with Dynamic Risk Adjustment
Includes Kelly Criterion, Drawdown Tracking, Adaptive Limits
Consolidated single source of truth — all 4 risk managers merged here.
"""

import json
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicRiskManager:
    """
    Enhanced risk management with:
    - Kelly Criterion for position sizing
    - Real-time drawdown tracking
    - Adaptive loss limits based on streak
    - Volatility adjustment
    - Circuit breakers for catastrophic loss
    """

    _DEFAULTS = {
        'max_position_pct': 0.10,        # 10% max per position
        'max_daily_trades': 5,           # 5 trades per day max
        'stop_loss_pct': 0.15,           # 15% stop-loss
        'take_profit_pct': 0.50,         # 50% take-profit
        'daily_loss_limit': 0.20,        # 20% daily loss cap (README-documented ceiling)
        'min_edge': 0.08,                # 8% minimum edge
        'min_confidence': 85,            # 85% min confidence
        'max_drawdown_limit': 0.25,      # 25% circuit breaker
    }

    def __init__(self, base_config=None):
        # Base risk configuration — CONSERVATIVE for real money.
        # Callers may pass a partial config; merge over defaults so no key is
        # ever missing at runtime (this also keeps circuit breakers safe when
        # a caller supplies only a subset of limits).
        self.base = dict(self._DEFAULTS)
        if base_config:
            self.base.update(base_config)

        # Current adaptive settings (starts as copy of base)
        self.current = self.base.copy()

        # Tracking state
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0

        self.winning_streak = 0
        self.losing_streak = 0
        self.consecutive_losses = 0

        self.session_start_balance = 0.0
        self.daily_start_balance = 0.0

        # Performance tracking
        self.win_rate = 0.95
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.win_count = 0
        self.loss_count = 0

    def start_session(self, balance: float):
        """Initialize for new session."""
        self.session_start_balance = balance
        self.daily_start_balance = balance
        if balance > self.peak_balance:
            self.peak_balance = balance

    def update_after_trade(self, won: bool, profit: float, new_balance: float):
        """Update risk state after each trade with enhanced safety checks."""
        # Update peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance

        # Calculate current drawdown
        if self.peak_balance > 0:
            self.current_drawdown = (self.peak_balance - new_balance) / self.peak_balance
        else:
            self.current_drawdown = 0.0

        # Track max drawdown
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown

        # Track streaks and update averages
        if won:
            self.winning_streak += 1
            self.losing_streak = 0
            self.win_count += 1
            self.avg_win = ((self.avg_win * (self.win_count - 1)) + profit) / self.win_count
        else:
            self.winning_streak = 0
            self.losing_streak += 1
            self.consecutive_losses += 1
            self.loss_count += 1
            self.avg_loss = ((self.avg_loss * (self.loss_count - 1)) + abs(profit)) / self.loss_count

        # Update daily start balance tracking
        if new_balance > self.daily_start_balance * 1.5:
            self.daily_start_balance = new_balance

        # Apply adaptive adjustments
        self._adjust_risk_for_drawdown()
        self._adjust_risk_for_streak()

    def _adjust_risk_for_drawdown(self):
        """Tighten risk when drawdown increases."""
        if self.current_drawdown > 0.10:
            reduction = min(self.current_drawdown * 2, 0.5)
            self.current['max_position_pct'] = self.base['max_position_pct'] * (1 - reduction)

        if self.current_drawdown > 0.20:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.5
            self.current['daily_loss_limit'] = self.base['daily_loss_limit'] * 0.5

        if self.current_drawdown < 0.05:
            self.current['max_position_pct'] = self.base['max_position_pct']
            self.current['daily_loss_limit'] = self.base['daily_loss_limit']

    def _adjust_risk_for_streak(self):
        """Adjust risk based on winning/losing streaks."""
        if self.consecutive_losses >= 5:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.7
            self.current['daily_loss_limit'] = self.base['daily_loss_limit'] * 0.7

        if self.consecutive_losses >= 10:
            self.current['max_position_pct'] = self.base['max_position_pct'] * 0.5
            self.current['min_edge'] = min(self.base['min_edge'] + 0.10, 0.80)

        if self.winning_streak >= 3:
            self.current['max_position_pct'] = self.base['max_position_pct']
            self.current['min_edge'] = self.base['min_edge']
            self.current['daily_loss_limit'] = self.base['daily_loss_limit']

    def check_circuit_breakers(self, current_balance: float, starting_balance: float) -> bool:
        """Check for catastrophic conditions. Returns True if trading should halt."""
        # 25% drawdown circuit breaker
        if starting_balance > 0:
            drawdown = (starting_balance - current_balance) / starting_balance
            if drawdown >= self.base['max_drawdown_limit']:
                logger.critical(
                    f"CIRCUIT BREAKER: {drawdown:.1%} drawdown >= "
                    f"{self.base['max_drawdown_limit']:.0%} limit"
                )
                return True

        # Catastrophic drawdown — 50% loss from peak
        if self.peak_balance > 0 and current_balance < self.peak_balance * 0.5:
            logger.critical(
                f"CATASTROPHIC DRAWDOWN: 50% loss from peak "
                f"({current_balance:.2f} vs peak {self.peak_balance:.2f})"
            )
            return True

        # Excessive consecutive losses
        if self.consecutive_losses >= 10:
            logger.critical(f"EXCESSIVE LOSSES: {self.consecutive_losses} consecutive losses")
            return True

        # Daily loss limit exceeded
        if self.daily_start_balance > 0:
            daily_pnl = current_balance - self.daily_start_balance
            daily_loss_limit = -abs(self.daily_start_balance * self.current['daily_loss_limit'])
            if daily_pnl < daily_loss_limit:
                logger.critical(
                    f"DAILY LOSS LIMIT EXCEEDED: {daily_pnl:.2f} < {daily_loss_limit:.2f}"
                )
                return True

        return False

    def calculate_kelly_position(self, win_prob: float, odds: float) -> float:
        """Calculate Kelly position size.
        Kelly % = (b * p - q) / b where b = odds - 1, p = win_prob, q = 1 - p
        Returns fraction of balance. Uses half-Kelly for safety.
        """
        p = win_prob
        q = 1 - p
        b = (odds - 1) if odds > 1 else 0
        if b <= 0 or p <= 0:
            return 0.0
        kelly = (b * p - q) / b
        # Half-Kelly capped at 20%
        return max(0.01, min(kelly * 0.5, 0.20))

    def configure_from_history(self, stats: dict):
        """Adjust base config from historical backtest stats."""
        if stats.get('drawdown', 0) > 0.10:
            self.base['max_position_pct'] = max(0.01, self.base.get('max_position_pct', 0.10) * 0.7)
        if stats.get('win_rate', 100) < 60:
            self.base['max_position_pct'] = max(0.01, self.base.get('max_position_pct', 0.10) * 0.8)
        self.base['max_position_pct'] = min(0.20, max(0.01, self.base.get('max_position_pct', 0.10)))

    def get_recommended_position(self, balance: float, edge: float, price: float,
                                  confidence: float) -> float:
        """Get recommended position size using combination of rules."""
        base_pct = self.current['max_position_pct']

        # Try Kelly if edge is high
        if edge >= 0.80 and price > 0:
            kelly_pct = self.calculate_kelly_position(edge, 1 / price)
            recommended = min(kelly_pct, base_pct)
        else:
            recommended = base_pct

        # Drawdown adjustment
        if self.current_drawdown > 0.15:
            recommended *= 0.7

        # Streak adjustment
        if self.consecutive_losses >= 3:
            recommended *= 0.8

        return recommended

    def should_trade(self, edge: float, confidence: float, balance: float):
        """Determine if we should trade based on current risk state."""
        # Daily loss limit
        if self.daily_start_balance > 0:
            daily_loss = (self.daily_start_balance - balance) / self.daily_start_balance
            if daily_loss >= self.current['daily_loss_limit']:
                return False, "Daily loss limit reached"

        # Minimum edge
        if edge < self.current['min_edge']:
            return False, f"Edge {edge:.0%} below minimum {self.current['min_edge']:.0%}"

        # Minimum confidence
        if confidence < self.current['min_confidence']:
            return False, f"Confidence {confidence:.0f} below minimum {self.current['min_confidence']}"

        return True, "Approved"

    def calculate_portfolio_variance(self, positions, covariance_matrix):
        """Calculate portfolio variance."""
        positions_array = np.array(positions)
        portfolio_variance = positions_array.T @ covariance_matrix @ positions_array
        return float(portfolio_variance)

    def mean_variance_optimization(self, expected_returns, covariance_matrix):
        """Mean-variance optimization via Sharpe maximization.

        Returns weights that sum to 1 and stay in [0, 1]. This is a portfolio
        allocation (fractions of portfolio), not a per-trade position size, so
        it is not capped by max_position_pct.
        """
        from scipy.optimize import minimize

        expected_returns = np.asarray(expected_returns, dtype=float)
        covariance_matrix = np.asarray(covariance_matrix, dtype=float)
        n = len(expected_returns)

        def neg_sharpe(w):
            ret = float(np.dot(w, expected_returns))
            var = float(w @ covariance_matrix @ w)
            vol = np.sqrt(var) if var > 0 else 0.0
            return -(ret / vol) if vol > 0 else 1e9

        bounds = [(0.0, 1.0)] * n
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        init = np.full(n, 1.0 / n)

        result = minimize(
            neg_sharpe, init, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000},
        )

        weights = result.x
        weights = np.maximum(weights, 0.0) / max(np.sum(weights), 1e-12)
        weights = weights / (np.sum(weights) or 1.0)

        port_return = float(np.dot(weights, expected_returns))
        variance = float(weights @ covariance_matrix @ weights)
        risk = float(np.sqrt(max(variance, 0.0)))
        sharpe = port_return / risk if risk > 0 else 0.0

        return {
            'weights': [float(w) for w in np.round(weights, 6)],
            'expected_return': port_return,
            'risk': risk,
            'sharpe_ratio': sharpe,
        }

    def monte_carlo_simulation(self, current_balance, n_simulations=1000, n_days=30):
        """Run Monte Carlo simulation to estimate risk of ruin."""
        results = {
            'ending_balances': [],
            'max_drawdowns': [],
            'ruin_probability': 0.0,
            'expected_final_balance': 0.0,
            'cvar_95': 0.0,
        }

        win_rate = self.win_rate
        avg_profit = self.avg_win if self.avg_win > 0 else 10.0
        avg_loss = self.avg_loss if self.avg_loss > 0 else 5.0

        for _ in range(n_simulations):
            balance = current_balance
            peak_balance = current_balance
            max_drawdown = 0.0

            for _ in range(n_days):
                if np.random.random() < win_rate:
                    profit = avg_profit * (1 + np.random.normal(0, 0.1))
                    balance += profit
                else:
                    loss = avg_loss * (1 + np.random.normal(0, 0.1))
                    balance -= loss

                if balance > peak_balance:
                    peak_balance = balance
                drawdown = (peak_balance - balance) / peak_balance
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            results['ending_balances'].append(balance)
            results['max_drawdowns'].append(max_drawdown)

        ending_balances = np.array(results['ending_balances'])
        results['expected_final_balance'] = float(np.mean(ending_balances))
        ruin_count = np.sum(ending_balances <= 0)
        results['ruin_probability'] = float(ruin_count / n_simulations)

        worst_5_percent = np.percentile(ending_balances, 5)
        cvar_values = ending_balances[ending_balances <= worst_5_percent]
        results['cvar_95'] = float(np.mean(cvar_values)) if len(cvar_values) > 0 else 0.0

        return results

    def get_win_rate(self) -> float:
        return self.win_rate

    def get_average_profit(self) -> float:
        return self.avg_win if self.avg_win > 0 else 10.0

    def get_average_loss(self) -> float:
        return self.avg_loss if self.avg_loss > 0 else 5.0

    def get_risk_metrics(self) -> dict:
        return {
            'current_position_pct': self.current['max_position_pct'],
            'drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'winning_streak': self.winning_streak,
            'losing_streak': self.losing_streak,
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_pct': (
                (self.daily_start_balance - self.peak_balance) / self.daily_start_balance
                if self.daily_start_balance > 0 else 0
            ),
        }

    def reset_daily(self, balance: float):
        self.daily_start_balance = balance
        self.consecutive_losses = 0

    def get_summary(self) -> dict:
        return {
            'current_config': self.current,
            'peak_balance': self.peak_balance,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'streaks': {'wins': self.winning_streak, 'losses': self.losing_streak},
        }