"""
FastAPI endpoints for trading bot
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="Polymarket Trading Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulated trading state
trading_state = {
    "balance": 100.0,
    "starting_balance": 100.0,
    "is_running": False,
    "trades": [],
    "stats": {"wins": 0, "losses": 0},
    "opportunities": []
}


class TradeRequest(BaseModel):
    amount: float = 10.0
    num_trades: int = 100


class StartRequest(BaseModel):
    starting_amount: float = 10.0


@app.get("/")
def root():
    return {"status": "ok", "message": "Polymarket Trading Bot API"}


@app.get("/api/status")
def get_status():
    return {
        "connected": True,
        "mode": "paper" if not trading_state["is_running"] else "live",
        "win_rate": calculate_win_rate()
    }


def calculate_win_rate():
    total = trading_state["stats"]["wins"] + trading_state["stats"]["losses"]
    if total == 0:
        return 0
    return (trading_state["stats"]["wins"] / total) * 100


@app.get("/api/account")
def get_account():
    profit = trading_state["balance"] - trading_state["starting_balance"]
    roi = (profit / trading_state["starting_balance"] * 100) if trading_state["starting_balance"] > 0 else 0
    
    return {
        "starting_balance": trading_state["starting_balance"],
        "current_balance": trading_state["balance"],
        "total_profit": profit,
        "roi": roi,
        "win_rate": calculate_win_rate()
    }


@app.get("/api/trades")
def get_trades(limit: int = 20):
    return {
        "trades": trading_state["trades"][-limit:],
        "total": len(trading_state["trades"]),
        "wins": trading_state["stats"]["wins"],
        "losses": trading_state["stats"]["losses"]
    }


@app.get("/api/opportunities")
def get_opportunities():
    return {
        "opportunities": trading_state["opportunities"][:10],
        "total": len(trading_state["opportunities"])
    }


@app.post("/api/reset")
def reset_account():
    trading_state["balance"] = trading_state["starting_balance"]
    trading_state["trades"] = []
    trading_state["stats"] = {"wins": 0, "losses": 0}
    return {"message": "Account reset", "balance": trading_state["balance"]}


@app.post("/api/start")
def start_trading(request: StartRequest):
    trading_state["starting_balance"] = request.starting_amount
    trading_state["balance"] = request.starting_amount
    trading_state["is_running"] = True
    return {"message": "Trading started", "balance": trading_state["balance"]}


@app.post("/api/stop")
def stop_trading():
    trading_state["is_running"] = False
    return {"message": "Trading stopped"}


@app.get("/api/markets")
def get_markets(limit: int = 50):
    # This will fetch from Polymarket API
    from data.polymarket_client import PolymarketClient
    client = PolymarketClient()
    markets = client.get_markets(limit)
    
    result = []
    for m in markets:
        try:
            prices = json.loads(m.get('outcomePrices', '[]'))
            if prices:
                result.append({
                    "id": m.get('id'),
                    "question": m.get('question', '')[:60],
                    "yes_price": float(prices[0]),
                    "no_price": float(prices[1]) if len(prices) > 1 else 0,
                    "volume": float(m.get('volume', 0) or 0),
                    "liquidity": float(m.get('liquidity', 0) or 0)
                })
        except:
            continue
    
    return {"markets": result[:limit], "total": len(result)}


@app.post("/api/simulate")
def run_simulation(request: TradeRequest):
    """Run a trading simulation"""
    import random
    
    trading_state["starting_balance"] = request.amount
    trading_state["balance"] = request.amount
    trading_state["trades"] = []
    trading_state["stats"] = {"wins": 0, "losses": 0}
    
    # Simulate trades
    for i in range(request.num_trades):
        bet = min(trading_state["balance"] * 0.15, 25)
        bet = max(bet, 1)
        
        edge = random.uniform(0.70, 0.99)
        won = random.random() < edge
        
        if won:
            price = random.uniform(0.01, 0.20)
            profit = bet * (1/price - 1) * 0.93
            trading_state["stats"]["wins"] += 1
        else:
            profit = -bet
            trading_state["stats"]["losses"] += 1
        
        trading_state["balance"] += profit
        
        trading_state["trades"].append({
            "trade": i + 1,
            "won": won,
            "profit": round(profit, 2),
            "balance": round(trading_state["balance"], 2),
            "edge": round(edge * 100, 0)
        })
    
    return {
        "message": f"Simulation complete: {request.num_trades} trades",
        "final_balance": trading_state["balance"],
        "win_rate": calculate_win_rate()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)