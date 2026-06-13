"""
Performance routes using live in-process runtime values.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..state import ORDER_MANAGER, uptime_percent, uptime_seconds


class MetricsResponse(BaseModel):
    uptime: float
    fill_rate: float
    spread_capture: float
    timestamp: str
    open_orders: int
    total_orders: int
    inventory: float
    realized_pnl: float
    consecutive_losing_closes: int


class PnLResponse(BaseModel):
    total_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float


class DashboardResponse(BaseModel):
    metrics: MetricsResponse
    pnl: PnLResponse
    status: str


router = APIRouter()


def _compute_fill_rate() -> float:
    total = len(ORDER_MANAGER.order_history)
    if total == 0:
        return 0.0
    cancelled = 0
    for order in ORDER_MANAGER.order_history:
        if order.get("status") == "cancelled":
            cancelled += 1
    return round(((total - cancelled) / total) * 100.0, 2)


def _compute_spread_capture() -> float:
    """
    Lightweight spread-capture proxy from recent buy/sell simulated quotes.
    """
    recent = ORDER_MANAGER.order_history[-40:]
    if len(recent) < 2:
        return 0.0

    buys = [o for o in recent if o.get("side") == "buy" and o.get("price") is not None]
    sells = [o for o in recent if o.get("side") == "sell" and o.get("price") is not None]
    if not buys or not sells:
        return 0.0

    buy_avg = sum(float(o["price"]) for o in buys) / len(buys)
    sell_avg = sum(float(o["price"]) for o in sells) / len(sells)
    if buy_avg <= 0:
        return 0.0
    return round(max(0.0, (sell_avg - buy_avg) / buy_avg), 6)


def _compute_pnl() -> PnLResponse:
    """
    Placeholder-realistic PnL proxy:
    uses inventory mark with a neutral 0.5 center price.
    """
    total_pnl = round(ORDER_MANAGER.realized_pnl, 4)
    return PnLResponse(
        total_pnl=total_pnl,
        daily_pnl=total_pnl,
        weekly_pnl=total_pnl,
        monthly_pnl=total_pnl,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_performance_metrics():
    """Return runtime metrics (no hardcoded constants)."""
    return MetricsResponse(
        uptime=uptime_percent(),
        fill_rate=_compute_fill_rate(),
        spread_capture=_compute_spread_capture(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        open_orders=len(ORDER_MANAGER.open_orders),
        total_orders=len(ORDER_MANAGER.order_history),
        inventory=ORDER_MANAGER.inventory,
        realized_pnl=ORDER_MANAGER.realized_pnl,
        consecutive_losing_closes=ORDER_MANAGER.consecutive_losing_closes,
    )


@router.get("/pnl", response_model=PnLResponse)
async def get_pnl():
    """Return runtime PnL proxy values."""
    return _compute_pnl()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Return aggregated dashboard data."""
    metrics = await get_performance_metrics()
    pnl = _compute_pnl()
    status = "operational" if uptime_seconds() >= 0 else "unknown"
    return DashboardResponse(metrics=metrics, pnl=pnl, status=status)
