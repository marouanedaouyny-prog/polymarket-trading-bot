"""
Dashboard routes serving the trading web UI.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..state import get_dashboard_state, update_dashboard_state

HERE = Path(__file__).resolve().parent

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the trading dashboard HTML page."""
    template_path = HERE / "templates" / "dashboard.html"
    if not template_path.exists():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=500)
    html = template_path.read_text(encoding="utf-8")
    return HTMLResponse(html)


@router.get("/api/dashboard/data")
async def dashboard_data(request: Request):
    """Return live dashboard state as JSON."""
    state = get_dashboard_state()
    # Build position list from open_positions dict
    positions = [
        {
            "market_id": mid,
            "direction": p.get("direction", "unknown"),
            "entry_price": p.get("entry_price", 0.0),
            "current_price": p.get("current_price", p.get("entry_price", 0.0)),
            "size": p.get("size", 0.0),
            "pnl": p.get("pnl", 0.0),
            "unrealized_pnl": p.get("unrealized_pnl", 0.0),
        }
        for mid, p in state.get("open_positions", {}).items()
    ]

    # Build trade history from state list
    trade_history = list(state.get("trade_history", []))

    return {
        "balance": state.get("balance", 0.0),
        "daily_pnl": state.get("daily_pnl", 0.0),
        "win_rate": state.get("win_rate", 0.0),
        "total_trades": state.get("total_trades", 0),
        "winning_trades": state.get("winning_trades", 0),
        "losing_trades": state.get("losing_trades", 0),
        "drawdown": state.get("drawdown", 0.0),
        "max_drawdown": state.get("max_drawdown", 0.0),
        "consecutive_losses": state.get("consecutive_losses", 0),
        "circuit_breaker_triggered": state.get("circuit_breaker_triggered", False),
        "is_live": state.get("is_live", False),
        "peak_balance": state.get("peak_balance", 100.0),
        "started_at": state.get("started_at", ""),
        "server_time": state.get("server_time", ""),
        "positions": positions,
        "trade_history": trade_history,
    }