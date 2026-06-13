"""
Risk management routes backed by in-process risk manager state.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from ..state import RISK_MANAGER, risk_snapshot


class RiskLimitsResponse(BaseModel):
    max_position_size: float
    daily_loss_limit: float
    max_drawdown_limit: float
    kill_switch_activated: bool


class KillSwitchRequest(BaseModel):
    enabled: bool


router = APIRouter()


@router.get("/limits", response_model=RiskLimitsResponse)
async def get_risk_limits():
    """Get current risk limits and kill-switch status."""
    snapshot = risk_snapshot()
    return RiskLimitsResponse(
        max_position_size=float(snapshot["max_position_size"]),
        daily_loss_limit=float(snapshot["daily_loss_limit"]),
        max_drawdown_limit=float(snapshot["max_drawdown_limit"]),
        kill_switch_activated=bool(snapshot["kill_switch_activated"]),
    )


@router.post("/kill-switch")
async def toggle_kill_switch(request: KillSwitchRequest):
    """Enable/disable kill switch in runtime risk manager."""
    RISK_MANAGER.kill_switch_activated = bool(request.enabled)
    return {
        "kill_switch_enabled": RISK_MANAGER.kill_switch_activated,
        "message": "Kill switch updated",
    }
