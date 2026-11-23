"""
Risk management router for the API.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/limits")
async def get_risk_limits():
    """Get current risk limits."""
    return {"risk_limits": {}}

@router.post("/kill-switch")
async def toggle_kill_switch(state: bool):
    """Toggle the kill switch."""
    return {"kill_switch_enabled": state}