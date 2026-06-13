"""
Main API application module with production features.
"""

import os
import signal
import atexit
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("FASTAPI_API_KEY", "dev-key-change-in-production")
API_VERSION = "1.0.0"

limiter = Limiter(key_func=get_remote_address)

shutdown_handlers = []


def register_shutdown_handler(handler):
    """Register a function to be called on shutdown."""
    shutdown_handlers.append(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    def shutdown():
        for handler in shutdown_handlers:
            try:
                handler()
            except Exception:
                pass
    signal.signal(signal.SIGTERM, lambda s, f: shutdown())
    atexit.register(shutdown)
    yield


app = FastAPI(
    title="Polymarket Trading Bot API",
    description="API for the Polymarket trading bot",
    version=API_VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.get("/")
async def root():
    return {"message": "Polymarket Trading Bot API", "version": API_VERSION}


@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    return {
        "status": "healthy",
        "version": API_VERSION,
        "api_key_configured": bool(API_KEY and API_KEY != "dev-key-change-in-production")
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        from src.monitoring.metrics import get_metrics
        return PlainTextResponse(get_metrics(), media_type="text/plain")
    except ImportError:
        return {"metrics": "not available"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


from .performance_page import performance_router
from .routers import markets, performance, risk, trades

app.include_router(markets.router, prefix="/markets")
app.include_router(trades.router, prefix="/trades")
app.include_router(risk.router, prefix="/risk")
app.include_router(performance.router, prefix="/performance")
app.include_router(performance_router, prefix="")