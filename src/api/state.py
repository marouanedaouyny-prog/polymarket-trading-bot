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

def get_training_service():
    global _training_service
    if _training_service is None:
        _training_service = TrainingService()
    return _training_service


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
