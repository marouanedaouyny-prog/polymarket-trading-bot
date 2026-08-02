"""
Main API application module with production features.
"""

import logging
import os
import signal
import atexit
import json

logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("FASTAPI_API_KEY")
if not API_KEY:
    raise ValueError("FASTAPI_API_KEY environment variable is required but not set")
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

# Initialize rate limiter (single definition)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
cors_methods = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,PATCH,DELETE").split(",")
cors_headers = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )


@app.on_event("startup")
async def startup_event():
    live_order_flag = os.getenv("POLYMARKET_ALLOW_REAL_ORDERS", "false").lower() == "true"
    live_enabled = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
    required_live_keys = [
        "POLYMARKET_API_KEY",
        "POLYMARKET_API_SECRET",
        "POLYMARKET_API_PASSPHRASE",
        "PRIVATE_KEY",
    ]
    missing_live_keys = [key for key in required_live_keys if not os.getenv(key)]

    if live_order_flag or live_enabled:
        if missing_live_keys:
            raise RuntimeError(f"CRITICAL: live trading requested but missing keys: {', '.join(missing_live_keys)}")
        print("🚀 LIVE TRADING MODE ENABLED")
    else:
        print("🛡️ PAPER TRADING MODE ENABLED (Safe)")


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    # Public routes
    if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/dashboard", "/api/dashboard/data"]:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API Key"}
        )
    return await call_next(request)


@app.middleware("http")
async def audit_logging(request: Request, call_next):
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Log to file
    log_entry = {
        "timestamp": start_time.isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration": duration,
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", "")
    }

    audit_path = PROJECT_ROOT / "data/logs/api_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.middleware("http")
async def ip_whitelisting(request: Request, call_next):
    """IP whitelisting middleware for enhanced security."""
    # Get client IP address
    client_ip = request.client.host if request.client else "unknown"

    # Check if IP whitelisting is enabled
    whitelist_enabled = os.getenv("IP_WHITELIST_ENABLED", "false").lower() == "true"

    if whitelist_enabled:
        # Get allowed IPs from environment variable
        allowed_ips = os.getenv("ALLOWED_IPS", "")
        allowed_ip_list = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]

        if allowed_ip_list and client_ip not in allowed_ip_list:
            logger.warning(f"Blocked access from non-whitelisted IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: IP not whitelisted"
            )

    return await call_next(request)


@app.middleware("http")
async def request_size_limiter(request: Request, call_next):
    """Request size limiting to prevent DoS attacks."""
    # Check content length
    max_size = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # Default: 1MB

    # Check headers first
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        logger.warning(f"Request too large: {content_length} bytes (max {max_size})")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request too large: maximum size is {max_size} bytes"
        )

    # For POST/PUT/PATCH requests, check actual body size
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if len(body) > max_size:
                logger.warning(f"Request body too large: {len(body)} bytes (max {max_size})")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request body too large: maximum size is {max_size} bytes"
                )
        except Exception:
            # If we can't read the body, reject the request
            logger.warning("Unable to read request body for size validation")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body"
            )

    return await call_next(request)


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
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
@limiter.limit("60/minute")
async def metrics(request: Request):
    """Prometheus metrics endpoint."""
    from src.monitoring.metrics import get_metrics, update_trading_metrics
    try:
        # Pull live state if the trading system is running
        from src.api.state import get_trading_state
        state = get_trading_state()
        update_trading_metrics(
            balance=state.get("balance", 0.0),
            drawdown=state.get("drawdown", 0.0),
            win_rate=state.get("win_rate", 0.0),
            open_positions=state.get("open_positions", 0),
            daily_pnl=state.get("daily_pnl", 0.0),
        )
    except Exception:
        pass
    return PlainTextResponse(get_metrics(), media_type="text/plain; version=0.0.4")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


from .performance_page import performance_router
from .routers import markets, performance, risk, signals, trades, system
from .web import router as web_router

app.include_router(markets.router, prefix="/markets")
app.include_router(signals.router, prefix="/signals")
app.include_router(trades.router, prefix="/trades")
app.include_router(risk.router, prefix="/risk")
app.include_router(performance.router, prefix="/performance")
app.include_router(system.router, prefix="/system")
app.include_router(performance_router, prefix="")
app.include_router(web_router)
