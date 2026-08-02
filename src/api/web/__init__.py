"""Web dashboard router for the Polymarket trading bot."""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from src.api.state import get_trading_state

router = APIRouter(tags=["dashboard"])
HERE = Path(__file__).parent


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    html = (HERE / "templates" / "dashboard.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@router.get("/api/dashboard/data", include_in_schema=False)
async def dashboard_data():
    return JSONResponse(get_trading_state())
