"""
System control and health monitoring routes.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from ..state import RISK_MANAGER, ORDER_MANAGER, uptime_seconds, STARTED_AT

router = APIRouter()

@router.post("/stop")
async def stop_trading():
    """Emergency kill switch to halt all trading execution."""
    RISK_MANAGER.emergency_kill_switch()
    return {
        "status": "stopped",
        "message": "Emergency kill switch activated. All trading execution halted.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health")
async def enhanced_health_check():
    """Enhanced health check with status of critical components."""
    
    # Check MiroFish (simplified check for now)
    mirofish_url = os.getenv("MIROFISH_URL", "http://localhost:5001")
    # In a real scenario, we'd do a quick ping, but for now we'll report config
    mirofish_status = "configured" if mirofish_url else "not_configured"
    
    # Check Ledger Integrity
    ledger_path = Path("data/results/paper_ledger.json")
    ledger_ok = ledger_path.exists()
    ledger_size = ledger_path.stat().st_size if ledger_ok else 0
    
    # Bot status
    bot_status = "operational"
    if RISK_MANAGER.kill_switch_activated:
        bot_status = "stopped (kill-switch)"
        
    return {
        "status": "healthy" if bot_status == "operational" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds(),
        "components": {
            "bot": {
                "status": bot_status,
                "trades_today": ORDER_MANAGER.total_closed_trades,
                "realized_pnl": ORDER_MANAGER.realized_pnl
            },
            "mirofish": {
                "status": mirofish_status,
                "url": mirofish_url
            },
            "ledger": {
                "status": "ok" if ledger_ok else "missing",
                "path": str(ledger_path),
                "size_bytes": ledger_size
            }
        },
        "risk": RISK_MANAGER.check_risk_limits()
    }
