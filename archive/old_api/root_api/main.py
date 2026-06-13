from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os

# Initialize FastAPI app
app = FastAPI(
    title="Polymarket AI Trading System",
    description="Institutional-grade autonomous trading platform for prediction markets",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Protection
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key from header"""
    # Get key from config or environment
    valid_key = os.getenv('FASTAPI_API_KEY', 'dev_api_key_12345')
    
    if api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key header missing")
    if api_key != valid_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key

# Protected endpoint dependency
def require_auth():
    return Depends(get_api_key)

# Import routers
from api import data, trading, risk,ML
from api.routes import market_data, strategy, execution, analytics

# Include routers - all protected by default
app.include_router(market_data.router, prefix="/api/v1/market-data", dependencies=[require_auth()])
app.include_router(strategy.router, prefix="/api/v1/strategy", dependencies=[require_auth()])
app.include_router(execution.router, prefix="/api/v1/execution", dependencies=[require_auth()])
app.include_router(analytics.router, prefix="/api/v1/analytics", dependencies=[require_auth()])

@app.get("/")
def read_root():
    return {"message": "Polymarket AI Trading System API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}