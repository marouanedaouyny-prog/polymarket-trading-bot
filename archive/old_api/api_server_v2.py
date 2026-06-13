"""
FastAPI Backend Server - Real-time Trading Dashboard
Provides REST API + WebSocket for live market data, trades, P&L
"""

import asyncio
import json
import os
import random
from datetime import datetime
from typing import List, Optional
from collections import deque
from dataclasses import dataclass, asdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# ============ CONFIGURATION ============
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8000))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

app = FastAPI(title="Polymarket Trading Bot API", version="2.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ DATA MODELS ============
@dataclass
class MarketData:
    id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    end_date: str
    category: str
    edge: float
    confidence: int

@dataclass
class Trade:
    id: str
    market_id: str
    question: str
    side: str  # YES/NO
    entry_price: float
    position_size: float
    win: bool
    payout: float
    pnl: float
    timestamp: datetime
    confidence: int
    edge: float

@dataclass
class PerformanceMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_profit: float
    roi: float
    sharpe_ratio: float
    max_drawdown: float
    current_balance: float
    starting_balance: float

# ============ IN-MEMORY STATE ============
class TradingState:
    def __init__(self):
        self.balance = 10.0
        self.starting_balance = 10.0
        self.is_running = True
        self.trades: List[Trade] = []
        self.active_positions: dict = {}
        self.markets: List[MarketData] = []
        self.connected_clients: List[WebSocket] = []
        self.price_history = {}  # For charts
        self.pnl_history = []
        self.timestamp_history = []

trading_state = TradingState()

# ============ WEBSOCKET MANAGER ============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============ API RESPONSE MODELS ============
class StatusResponse(BaseModel):
    bot_running: bool
    total_trades: int
    win_rate: float
    balance: float
    profit: float
    roi: float
    last_update: str

class MarketResponse(BaseModel):
    markets: List[dict]
    count: int

class TradeResponse(BaseModel):
    trades: List[dict]
    count: int

class PerformanceResponse(BaseModel):
    metrics: dict

# ============ MARKET DATA GENERATOR ============
SAMPLE_QUESTIONS = [
    "Will BTC reach $100K by EOY?",
    "Will Trump win 2024 election?",
    "Will Fed cut rates in 2024?",
    "Will Ethereum hit $5K?",
    "Will AI replace 50% of jobs by 2030?",
    "Will Mars be colonized by 2040?",
    "Will crypto market cap hit $5T?",
    "Will React remain dominant in 2025?",
    "Will Apple release AR glasses?",
    "Will Tesla deliver 2M cars in 2024?",
]

CATEGORIES = ["Crypto", "Politics", "Economics", "Tech", "Space", "Sports"]

def generate_markets(count=50) -> List[MarketData]:
    """Generate realistic market data"""
    markets = []
    for i in range(count):
        question = random.choice(SAMPLE_QUESTIONS)
        base_price = random.uniform(0.15, 0.85)
        volume = random.uniform(50000, 5000000)
        liquidity = random.uniform(100000, 10000000)

        # Calculate edge based on price deviation from 0.5 + some factors
        base_edge = abs(base_price - 0.5) * 1.2
        category_boost = random.uniform(0, 0.1)
        edge = min(base_edge + category_boost, 0.95)

        confidence = int(edge * 100) + random.randint(-5, 10)

        market = MarketData(
            id=f"mkt_{i}",
            question=question,
            yes_price=base_price,
            no_price=1.0 - base_price,
            volume=volume,
            liquidity=liquidity,
            end_date=(datetime.now().isoformat()),
            category=random.choice(CATEGORIES),
            edge=round(edge, 3),
            confidence=max(0, min(100, confidence))
        )
        markets.append(market)
    return markets

def update_market_prices(markets: List[MarketData]) -> List[MarketData]:
    """Simulate price movements"""
    updated = []
    for m in markets:
        # Small random price movement
        change = random.uniform(-0.02, 0.02)
        new_yes = max(0.01, min(0.99, m.yes_price + change))
        updated.append(MarketData(
            id=m.id,
            question=m.question,
            yes_price=new_yes,
            no_price=1.0 - new_yes,
            volume=m.volume + random.uniform(-1000, 1000),
            liquidity=m.liquidity + random.uniform(-5000, 5000),
            end_date=m.end_date,
            category=m.category,
            edge=m.edge,
            confidence=m.confidence
        ))
    return updated

# ============ TRADING ENGINE ============
def execute_trade(market: MarketData, position_size_pct=0.2) -> Optional[Trade]:
    """Simulate trade execution with realistic win probability"""
    if market.edge < 0.1 or market.confidence < 40:
        return None

    # Calculate win probability based on edge and confidence
    win_prob = min(0.5 + (market.edge * 0.6) + ((market.confidence - 50) * 0.01), 0.88)

    won = random.random() < win_prob
    position_size = trading_state.balance * position_size_pct

    # Payout calculation (Polymarket uses 1/price - 1 fee)
    fee = 0.07
    if won:
        payout = position_size * (1 / market.yes_price - fee)
    else:
        payout = -position_size

    new_balance = trading_state.balance + payout

    trade = Trade(
        id=f"trade_{len(trading_state.trades)+1}",
        market_id=market.id,
        question=market.question,
        side="YES",
        entry_price=market.yes_price,
        position_size=position_size,
        win=won,
        payout=round(payout, 2),
        pnl=round(payout, 2),
        timestamp=datetime.now(),
        confidence=market.confidence,
        edge=market.edge
    )

    trading_state.trades.append(trade)
    trading_state.balance = new_balance
    trading_state.pnl_history.append(new_balance)
    trading_state.timestamp_history.append(datetime.now().isoformat())

    # Keep only last 1000 data points
    if len(trading_state.pnl_history) > 1000:
        trading_state.pnl_history.pop(0)
        trading_state.timestamp_history.pop(0)

    return trade

# ============ REAL-TIME UPDATE TASK ============
async def market_update_loop():
    """Background task that updates markets and broadcasts"""
    while True:
        try:
            # Update market prices
            if trading_state.markets:
                trading_state.markets = update_market_prices(trading_state.markets)

                # Occasionally execute a trade
                if trading_state.is_running and random.random() < 0.3 and trading_state.markets:
                    market = random.choice(trading_state.markets)
                    if market.edge > 0.15 and market.confidence > 50:
                        trade = execute_trade(market)
                        if trade:
                            # Broadcast trade event
                            await manager.broadcast({
                                "type": "trade",
                                "data": {
                                    "id": trade.id,
                                    "question": trade.question,
                                    "win": trade.win,
                                    "pnl": trade.pnl,
                                    "balance": trading_state.balance,
                                    "timestamp": trade.timestamp.isoformat()
                                }
                            })

            # Broadcast state update
            state_data = {
                "type": "state",
                "data": {
                    "balance": round(trading_state.balance, 2),
                    "total_trades": len(trading_state.trades),
                    "bot_running": trading_state.is_running,
                    "win_rate": (
                        sum(1 for t in trading_state.trades if t.win) /
                        len(trading_state.trades) * 100
                        if trading_state.trades else 0
                    ),
                    "timestamp": datetime.now().isoformat()
                }
            }
            await manager.broadcast(state_data)

            await asyncio.sleep(2)  # Update every 2 seconds
        except Exception as e:
            print(f"Error in update loop: {e}")
            await asyncio.sleep(5)

# ============ ROUTES ============

@app.get("/")
async def root():
    return {"message": "Polymarket Trading Bot API", "version": "2.0.0"}

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current bot status"""
    wins = sum(1 for t in trading_state.trades if t.win)
    total = len(trading_state.trades)
    profit = trading_state.balance - trading_state.starting_balance
    roi = (profit / trading_state.starting_balance * 100) if trading_state.starting_balance else 0

    return StatusResponse(
        bot_running=trading_state.is_running,
        total_trades=total,
        win_rate=(wins / total * 100) if total else 0,
        balance=round(trading_state.balance, 2),
        profit=round(profit, 2),
        roi=round(roi, 2),
        last_update=datetime.now().isoformat()
    )

@app.get("/api/markets", response_model=MarketResponse)
async def get_markets(limit: int = 50, category: Optional[str] = None):
    """Get current market opportunities"""
    markets = trading_state.markets[:limit] if trading_state.markets else generate_markets(limit)
    if category:
        markets = [m for m in markets if m.category == category]
    return MarketResponse(
        markets=[asdict(m) for m in markets],
        count=len(markets)
    )

@app.get("/api/trades", response_model=TradeResponse)
async def get_trades(limit: int = 50):
    """Get recent trades"""
    trades = trading_state.trades[-limit:] if trading_state.trades else []
    return TradeResponse(
        trades=[{
            **asdict(t),
            "timestamp": t.timestamp.isoformat()
        } for t in trades],
        count=len(trades)
    )

@app.get("/api/performance", response_model=PerformanceResponse)
async def get_performance():
    """Get performance metrics"""
    total = len(trading_state.trades)
    wins = sum(1 for t in trading_state.trades if t.win)
    losses = total - wins
    profit = trading_state.balance - trading_state.starting_balance
    roi = (profit / trading_state.starting_balance * 100) if trading_state.starting_balance else 0

    # Calculate Sharpe ratio (simplified)
    if len(trading_state.pnl_history) > 1:
        returns = [trading_state.pnl_history[i] - trading_state.pnl_history[i-1]
                  for i in range(1, len(trading_state.pnl_history))]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
        sharpe = (avg_return / std_dev * (252 ** 0.5)) if std_dev else 0
    else:
        sharpe = 0

    # Max drawdown
    peak = trading_state.starting_balance
    max_dd = 0
    for balance in trading_state.pnl_history:
        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak * 100 if peak else 0
        max_dd = max(max_dd, dd)

    return PerformanceResponse(metrics={
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total else 0,
        "total_profit": round(profit, 2),
        "roi": round(roi, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "current_balance": round(trading_state.balance, 2),
        "starting_balance": trading_state.starting_balance
    })

@app.get("/api/charts/equity")
async def get_equity_chart():
    """Get equity curve data for charts"""
    return {
        "labels": trading_state.timestamp_history[-100:],
        "values": trading_state.pnl_history[-100:],
        "initial": trading_state.starting_balance
    }

@app.post("/api/trade/execute")
async def execute_trade_api(market_id: str, position_size_pct: float = 0.2):
    """Manually execute a trade"""
    if not trading_state.is_running:
        raise HTTPException(409, "Trading engine is paused")

    market = next((m for m in trading_state.markets if m.id == market_id), None)
    if not market:
        raise HTTPException(404, "Market not found")

    trade = execute_trade(market, position_size_pct)
    if not trade:
        raise HTTPException(400, "Trade did not meet criteria")

    return {"success": True, "trade": asdict(trade), "new_balance": trading_state.balance}

@app.post("/api/reset")
async def reset_account():
    """Reset account to starting balance"""
    trading_state.balance = trading_state.starting_balance
    trading_state.trades = []
    trading_state.pnl_history = []
    trading_state.timestamp_history = []
    return {"success": True, "message": "Account reset"}

@app.post("/api/start")
async def start_trading():
    """Resume automated trading loop."""
    trading_state.is_running = True
    return {"success": True, "message": "Trading started"}

@app.post("/api/pause")
async def pause_trading():
    """Pause automated trading loop without resetting state."""
    trading_state.is_running = False
    return {"success": True, "message": "Trading paused"}

@app.post("/api/stop")
async def stop_trading():
    """Stop automated trading loop."""
    trading_state.is_running = False
    return {"success": True, "message": "Trading stopped"}

@app.post("/api/config")
async def update_config(starting_balance: float = 10.0):
    """Update trading configuration"""
    trading_state.starting_balance = starting_balance
    trading_state.balance = starting_balance
    return {"success": True, "starting_balance": starting_balance}

# ============ WEBSOCKET ============
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")

# ============ STARTUP ============
@app.on_event("startup")
async def startup_event():
    """Initialize markets on startup"""
    trading_state.markets = generate_markets(50)
    # Start background update task
    asyncio.create_task(market_update_loop())
    print(f"API Server started on port {APP_PORT}")
    print(f"Generated {len(trading_state.markets)} markets")
    print(f"WebSocket: ws://localhost:{APP_PORT}/ws")

# ============ RUN ============
if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=DEBUG,
        log_level="info"
    )
