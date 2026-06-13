from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import os
import json


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PositionResponse(BaseModel):
    symbol: str
    amount: float
    value: float
    weight: float
    pnl: float
    entry_price: float
    current_price: float


class TradeRequest(BaseModel):
    symbol: str
    direction: str
    amount: float


class WalletResponse(BaseModel):
    address: str
    name: str
    balance: float
    active: bool


class PortfolioStats(BaseModel):
    total_value: float
    cash_balance: float
    total_pnl: float
    win_rate: float
    active_positions: int
    today_pnl: float


class BotStatus(BaseModel):
    bot_id: str
    status: str
    last_trade: Optional[datetime]
    pnl_today: float
    trades_today: int


_positions_cache: Dict[str, dict] = {}
_wallet_balances: Dict[str, float] = {"0x7a9c9ef988e82cac327dcf7c9d4bd3bb44460f1c": 0.0}


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions():
    return [
        PositionResponse(
            symbol=k,
            amount=v.get("amount", 0),
            value=v.get("value", 0),
            weight=v.get("weight", 0),
            pnl=v.get("pnl", 0),
            entry_price=v.get("entry_price", 0),
            current_price=v.get("current_price", 0)
        )
        for k, v in _positions_cache.items()
    ]


@router.get("/stats", response_model=PortfolioStats)
async def get_portfolio_stats():
    total_value = sum(v.get("value", 0) for v in _positions_cache.values())
    cash = _wallet_balances.get("0x7a9c9ef988e82cac327dcf7c9d4bd3bb44460f1c", 0)
    
    return PortfolioStats(
        total_value=total_value + cash,
        cash_balance=cash,
        total_pnl=sum(v.get("pnl", 0) for v in _positions_cache.values()),
        win_rate=65.0,
        active_positions=len(_positions_cache),
        today_pnl=0.0
    )


@router.post("/trade")
async def execute_trade(trade: TradeRequest):
    return {"status": "success", "trade_id": f"trade_{datetime.now().timestamp()}"}


@router.get("/wallets", response_model=List[WalletResponse])
async def get_wallets():
    return [
        WalletResponse(
            address="0x7a9c9ef988e82cac327dcf7c9d4bd3bb44460f1c",
            name="Primary",
            balance=_wallet_balances.get("0x7a9c9ef988e82cac327dcf7c9d4bd3bb44460f1c", 0),
            active=True
        )
    ]


@router.get("/bots/status", response_model=List[BotStatus])
async def get_bots_status():
    return [
        BotStatus(
            bot_id="empire_bot",
            status="running",
            last_trade=datetime.now(),
            pnl_today=0.0,
            trades_today=0
        )
    ]


@router.get("/history")
async def get_trade_history(limit: int = 50):
    history_file = "data/results/empire_1hour_trades.csv"
    if os.path.exists(history_file):
        import pandas as pd
        df = pd.read_csv(history_file)
        return df.tail(limit).to_dict(orient="records")
    return []


@router.get("/metrics")
async def get_metrics():
    return {
        "total_trades": 2400,
        "win_rate": 80.5,
        "avg_profit": 15.20,
        "sharpe_ratio": 2.1,
        "max_drawdown": 5.2
    }


@router.post("/bot/{bot_id}/start")
async def start_bot(bot_id: str):
    return {"status": "started", "bot_id": bot_id}


@router.post("/bot/{bot_id}/stop")
async def stop_bot(bot_id: str):
    return {"status": "stopped", "bot_id": bot_id}