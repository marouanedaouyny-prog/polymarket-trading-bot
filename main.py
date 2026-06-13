# Main Application Orchestrator
# Coordinates all components of the trading system

import asyncio
import os
import uvicorn
import fastapi
from fastapi import FastAPI, Request, HTTPException, Depends
from data_pipeline import DataIngestionPipeline
from feature_engineering import FeatureEngineer
from strategies import StrategyEngine
from src.utils.logger import logger

app = FastAPI(title="Polymarket AI Trading System")

# Initialize system components
data_pipeline = DataIngestionPipeline()
feature_engineer = FeatureEngineer()
strategy_engine = StrategyEngine()

def _require_api_key(request: Request):
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv('FASTAPI_API_KEY'):
        raise HTTPException(status_code=401, detail='Unauthorized')
    return True

@app.get("/")
async def root():
    return {"message": "Polymarket AI Trading System is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/markets", dependencies=[Depends(_require_api_key)])
async def get_markets():
    # Return recent market data
    recent_data = data_pipeline.get_recent_data()
    return {"markets": recent_data}

@app.get("/opportunities", dependencies=[Depends(_require_api_key)])
async def get_opportunities():
    # Return recent arbitrage opportunities
    recent_data = data_pipeline.get_recent_data()
    opportunities = []

    for market_data in recent_data:
        opportunity = strategy_engine.detect_arbitrage_opportunity(market_data)
        if opportunity.get('confidence', 0) > 0.7:  # Only high confidence opportunities
            opportunities.append(opportunity)

    return {"opportunities": opportunities}

if __name__ == "__main__":
    logger.info("Starting Polymarket AI Trading System...")
    uvicorn.run(app, host="127.0.0.1", port=8000)