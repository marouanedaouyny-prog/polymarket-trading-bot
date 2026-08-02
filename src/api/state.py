"""
Shared in-process runtime state for API routes.
"""

import os
from datetime import datetime, timezone
from typing import Dict

try:
    from ..execution.order_manager import OrderManager
    from ..ml.training_service import TrainingService
    from ..risk.limits import RiskManager
except ImportError:
    from execution.order_manager import OrderManager
    from ml.training_service import TrainingService
    from risk.limits import RiskManager

STARTED_AT = datetime.now(timezone.utc)
ORDER_MANAGER = OrderManager(mode=os.getenv("TRADING_MODE", "paper"))
RISK_MANAGER = RiskManager()
_training_service = None

# Live trading state pushed by TradingAgentSystem after every trade
_live_state: Dict = {
    "balance": 0.0,
    "drawdown": 0.0,
    "win_rate": 0.0,
    "open_positions": 0,
    "daily_pnl": 0.0,
}

# Dashboard state -- richer, updated by the trading system
_dashboard_state: Dict = {
    "balance": 100.0,
    "open_positions": {},
    "trade_history": [],
    "daily_pnl": 0.0,
    "win_rate": 0.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "drawdown": 0.0,
    "max_drawdown": 0.0,
    "consecutive_losses": 0,
    "circuit_breaker_triggered": False,
    "is_live": False,
    "peak_balance": 100.0,
    "started_at": STARTED_AT.isoformat(),
    "server_time": STARTED_AT.isoformat(),
}


def push_trading_state(
    balance: float,
    drawdown: float,
    win_rate: float,
    open_positions: int,
    daily_pnl: float,
) -> None:
    """Called by TradingAgentSystem after every trade to keep state fresh."""
    _live_state.update(
        balance=balance,
        drawdown=drawdown,
        win_rate=win_rate,
        open_positions=open_positions,
        daily_pnl=daily_pnl,
    )
    # Also push to dashboard state
    _dashboard_state.update(
        balance=balance,
        drawdown=drawdown,
        win_rate=win_rate,
        daily_pnl=daily_pnl,
    )


def update_dashboard_state(**kwargs) -> None:
    """Update dashboard state with any keyword arguments."""
    _dashboard_state.update(**kwargs)
    _dashboard_state["server_time"] = datetime.now(timezone.utc).isoformat()


def get_dashboard_state() -> Dict:
    """Return the full dashboard state, merged with live data."""
    _dashboard_state["server_time"] = datetime.now(timezone.utc).isoformat()
    if "open_positions" in _live_state:
        _dashboard_state["open_positions_count"] = _live_state["open_positions"]
    return dict(_dashboard_state)


def get_training_service():
    global _training_service
    if _training_service is None:
        _training_service = TrainingService()
    return _training_service


def get_trading_state() -> Dict:
    """Return current trading state for Prometheus metrics (live when agent is running)."""
    return dict(_live_state)


def uptime_seconds() -> float:
    """Return process uptime in seconds."""
    return max(0.0, (datetime.now(timezone.utc) - STARTED_AT).total_seconds())


def uptime_percent() -> float:
    """
    Lightweight uptime proxy.
    Returns 100 while process is healthy.
    """
    return 100.0


def risk_snapshot() -> Dict:
    """Return a normalized risk snapshot."""
    return RISK_MANAGER.check_risk_limits()