"""
Trade routes with simulated/live-safe execution state.
"""

import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..state import ORDER_MANAGER, RISK_MANAGER, get_training_service

try:
    from ...data.connectors.gamma import PolymarketAPI
except ImportError:
    from data.connectors.gamma import PolymarketAPI


class TradeRequest(BaseModel):
    market_id: str
    side: str  # "buy" or "sell"
    size: float
    price: float
    order_type: str = "limit"  # "limit" or "market"


class TradeResponse(BaseModel):
    status: str
    order_id: str
    message: Optional[str] = None


router = APIRouter()
gamma_api = PolymarketAPI()


def _maybe_activate_kill_switch():
    """
    Activate risk kill-switch when strict loss controls are breached.
    """
    max_daily_loss_abs = float(os.getenv("MAX_DAILY_LOSS_ABS", "-20.0"))
    max_consecutive_losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))

    # Sync risk manager with execution realized PnL.
    RISK_MANAGER.update_daily_pnl(ORDER_MANAGER.realized_pnl)

    if ORDER_MANAGER.realized_pnl <= max_daily_loss_abs:
        RISK_MANAGER.kill_switch_activated = True

    if ORDER_MANAGER.consecutive_losing_closes >= max_consecutive_losses:
        RISK_MANAGER.kill_switch_activated = True


@router.get("/training-status", response_model=dict)
async def get_training_status():
    """Return model training state used by buy flow."""
    return get_training_service().status()


@router.get("/", response_model=dict)
async def get_trades(
    market_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Return trade history.
    - If market_id is provided, also returns exchange trades from Gamma.
    - Always returns local execution history from this API process.
    """
    local_trades = ORDER_MANAGER.order_history[-limit:]
    exchange_trades = []
    if market_id:
        exchange_trades = await gamma_api.get_trades(market_id, limit=limit)

    return {
        "local_trades": local_trades,
        "exchange_trades": exchange_trades,
        "count_local": len(local_trades),
        "count_exchange": len(exchange_trades),
    }


@router.post("/trade", response_model=TradeResponse)
async def place_trade(trade_data: TradeRequest):
    """
    Place an order through OrderManager.
    For BUY orders: model training on current market data runs first.
    """
    order_id = f"api_ord_{uuid4().hex[:12]}"
    side = trade_data.side.lower().strip()

    _maybe_activate_kill_switch()
    if RISK_MANAGER.kill_switch_activated:
        return TradeResponse(
            status="error",
            order_id=order_id,
            message="Trade blocked: kill switch is active due to risk limits.",
        )

    training_result = None
    signal_result = None
    if side == "buy":
        markets = await gamma_api.get_markets(limit=200)
        training_result = get_training_service().train_from_markets(markets)
        if not training_result.get("trained", False):
            reason = training_result.get("reason", "training_failed")
            return TradeResponse(
                status="error",
                order_id=order_id,
                message=f"Buy blocked: model training failed ({reason}).",
            )

        market = await gamma_api.get_market(trade_data.market_id)
        signal_result = get_training_service().evaluate_buy_signal(
            market=market,
            fallback_price=trade_data.price,
            fallback_volume=trade_data.size,
        )
        if not signal_result.get("allow_buy", False):
            reason = signal_result.get("reason", "insufficient_edge")
            edge = signal_result.get("edge")
            required_edge = signal_result.get("required_edge")
            edge_pct = signal_result.get("edge_pct")
            required_edge_pct = signal_result.get("required_edge_pct")
            detail = ""
            if edge is not None and required_edge is not None:
                detail = f" edge={edge:.4f} required={required_edge:.4f}"
            if edge_pct is not None and required_edge_pct is not None:
                detail += f" edge_pct={(edge_pct * 100):.2f}% required_pct={(required_edge_pct * 100):.2f}%"
            return TradeResponse(
                status="error",
                order_id=order_id,
                message=f"Buy blocked: model signal rejected ({reason}).{detail}",
            )

    payload = trade_data.dict()
    payload["order_id"] = order_id
    if training_result:
        payload["training_rows"] = training_result.get("rows", 0)
        payload["training_backend_xgb"] = training_result.get("xgb_backend")
        payload["training_backend_lgb"] = training_result.get("lgb_backend")
    if signal_result:
        payload["signal_edge"] = signal_result.get("edge")
        payload["signal_edge_pct"] = signal_result.get("edge_pct")
        payload["signal_required_edge"] = signal_result.get("required_edge")
        payload["signal_required_edge_pct"] = signal_result.get("required_edge_pct")
        payload["signal_predicted_price"] = signal_result.get("predicted_price")

    success = ORDER_MANAGER.place_order(payload)
    _maybe_activate_kill_switch()

    if success:
        if training_result:
            row_count = training_result.get("rows", 0)
            xgb_backend = training_result.get("xgb_backend", "unknown")
            lgb_backend = training_result.get("lgb_backend", "unknown")
            message = (
                "Order submitted after training "
                f"({row_count} rows, {xgb_backend}/{lgb_backend})."
            )
        else:
            message = "Order submitted to order manager."
        if RISK_MANAGER.kill_switch_activated:
            message += " Kill switch activated after this trade due to strict risk rules."
        return TradeResponse(
            status="success",
            order_id=order_id,
            message=message,
        )

    return TradeResponse(
        status="error",
        order_id=order_id,
        message="Order was not submitted (live mode adapter unavailable or blocked).",
    )
