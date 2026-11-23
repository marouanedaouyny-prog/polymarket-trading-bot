"""
Type-annotated config module — single source of truth for all settings.

Conservative defaults safe for real-money trading.

DO NOT edit these values directly — set via environment variables or .env file.
If you need to change a default, update the documentation AND the .env.example
file, then create a GitHub Issue to record the rationale.

Version: 0.2.0 — conservative trading defaults aligned with README/agent prompts.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT_DIR / 'config'

ENV_FILE = CONFIG_DIR / '.env'
# Explicit shell/process env always wins over .env files. Previously override=True
# meant config/.env could silently flip TRADING_MODE to live even when the caller
# passed TRADING_MODE=paper.
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)
else:
    ROOT_ENV = ROOT_DIR / '.env'
    if ROOT_ENV.exists():
        load_dotenv(ROOT_ENV, override=False)


# ============================================================================
# Config class — single source of truth for all trading parameters
# ============================================================================
class Config:
    # ==================================================================
    # Polymarket API
    # ==================================================================
    POLYMARKET_API_KEY: str = os.getenv('POLYMARKET_API_KEY', '')
    """Polymarket API key — obtain from Polymarket developer portal.

    REQUIRED for live trading. Set via POLYMARKET_API_KEY env var.
    Never commit actual keys — use .env or CI secret storage.
    """

    POLYMARKET_API_SECRET: str = os.getenv('POLYMARKET_API_SECRET', '')
    """Polymarket API secret — obtain from Polymarket developer portal.

    REQUIRED for live trading. Set via POLYMARKET_API_SECRET env var.
    """

    POLYMARKET_API_PASSPHRASE: str = os.getenv('POLYMARKET_API_PASSPHRASE', '')
    """Polymarket API passphrase — obtain from Polymarket developer portal.

    REQUIRED for live trading. Set via POLYMARKET_API_PASSPHRASE env var.
    """

    POLYMARKET_API_URL: str = os.getenv('POLYMARKET_API_URL', 'https://gamma-api.polymarket.com')
    """Base URL for Polymarket Gamma API.

    Default: https://gamma-api.polymarket.com
    Can be overridden via POLYMARKET_API_URL env var.
    """

    PRIVATE_KEY: str = os.getenv('PRIVATE_KEY', '')
    """Private key for signed orders.

    Used for CLOB order signing. Set via PRIVATE_KEY env var.
    """

    # ==================================================================
    # FastAPI
    # ==================================================================
    FASTAPI_API_KEY: str = os.getenv('FASTAPI_API_KEY', '')
    """API key for authenticating against the FastAPI server.

    REQUIRED. Raises ValueError if not set. Set via FASTAPI_API_KEY env var.
    """

    FASTAPI_HOST: str = os.getenv('FASTAPI_HOST', '0.0.0.0')
    """Host address for FastAPI server.

    Default: 0.0.0.0 (bind all interfaces).
    Override via FASTAPI_HOST env var.
    """

    FASTAPI_PORT: int = int(os.getenv('FASTAPI_PORT', '8000'))
    """Port for FastAPI server.

    Default: 8000. Override via FASTAPI_PORT env var.
    """

    # ==================================================================
    # Security
    # ==================================================================
    IP_WHITELIST_ENABLED: bool = os.getenv('IP_WHITELIST_ENABLED', 'false').lower() == 'true'
    """Whether IP whitelisting is enabled.

    Default: false. Set via IP_WHITELIST_ENABLED env var (true/false).
    """

    ALLOWED_IPS: str = os.getenv('ALLOWED_IPS', '')
    """Comma-separated list of allowed IP addresses.

    Used when IP_WHITELIST_ENABLED=true. Format: "1.2.3.4,5.6.7.8"
    """

    MAX_REQUEST_SIZE: int = int(os.getenv('MAX_REQUEST_SIZE', '1048576'))
    """Maximum request body size in bytes.

    Default: 1MB (1048576). Set via MAX_REQUEST_SIZE env var.
    """

    RATE_LIMIT_ROOT: str = os.getenv('RATE_LIMIT_ROOT', '10/minute')
    """Rate limit for root endpoints.

    Default: 10 requests per minute. Set via RATE_LIMIT_ROOT env var.
    """

    RATE_LIMIT_HEALTH: str = os.getenv('RATE_LIMIT_HEALTH', '100/minute')
    """Rate limit for health check endpoints.

    Default: 100 requests per minute. Set via RATE_LIMIT_HEALTH env var.
    """

    RATE_LIMIT_METRICS: str = os.getenv('RATE_LIMIT_METRICS', '60/minute')
    """Rate limit for metrics endpoints.

    Default: 60 requests per minute. Set via RATE_LIMIT_METRICS env var.
    """

    # ==================================================================
    # CORS
    # ==================================================================
    CORS_ALLOW_ORIGINS: str = os.getenv('CORS_ALLOW_ORIGINS', '*')
    """Allowed CORS origins.

    Default: "*" (all origins). Override via CORS_ALLOW_ORIGINS env var.
    Production should set specific origins (e.g., "https://example.com").
    """

    CORS_ALLOW_METHODS: str = os.getenv('CORS_ALLOW_METHODS', 'GET,POST,PUT,PATCH,DELETE')
    """Allowed CORS methods.

    Default: GET,POST,PUT,PATCH,DELETE.
    """

    CORS_ALLOW_HEADERS: str = os.getenv('CORS_ALLOW_HEADERS', '*')
    """Allowed CORS headers.

    Default: "*" (all headers).
    """

    # ==================================================================
    # Trading — CONSERVATIVE defaults safe for real money
    # ==================================================================
    STARTING_BALANCE: float = float(os.getenv('STARTING_BALANCE', '100.0'))
    """Starting balance for paper/live trading sessions.

    Default: $100. Set via STARTING_BALANCE env var.
    This is the initial balance used by the Lead Agent.
    """

    MAX_POSITION_PCT: float = float(os.getenv('MAX_POSITION_PCT', '0.10'))
    """Maximum position size as fraction of total balance.

    Default: 10% (0.10). Set via MAX_POSITION_PCT env var.
    WARNING: Changing this requires updating agent prompts too!
    """

    MIN_EDGE: float = float(os.getenv('MIN_EDGE', '0.08'))
    """Minimum edge (expected value ratio) required to consider a trade.

    Default: 8% (0.08). Set via MIN_EDGE env var.
    WARNING: Changing this requires updating agent prompts too!
    Note: Old docs claimed 65%; config enforces 8% for conservative trading.
    """

    MIN_CONFIDENCE: float = float(os.getenv('MIN_CONFIDENCE', '85'))
    """Minimum confidence percentage required to consider a trade.

    Default: 85%. Set via MIN_CONFIDENCE env var.
    WARNING: Changing this requires updating agent prompts too!
    Note: Old docs/prompts claimed 65%; config enforces 85% for conservative trading.
    """

    MIN_VOLUME: float = float(os.getenv('MIN_VOLUME', '10000'))
    """Minimum trading volume in dollars required to consider a market.

    Default: $10,000. Set via MIN_VOLUME env var.
    Note: Old docs claimed $15K; config enforces $10K.
    """

    PRICE_MIN: float = float(os.getenv('PRICE_MIN', '0.05'))
    """Minimum market price to consider (inclusive).

    Default: $0.05. Set via PRICE_MIN env var.
    Note: Old docs claimed $0.01; config enforces $0.05 for consistency.
    """

    PRICE_MAX: float = float(os.getenv('PRICE_MAX', '0.50'))
    """Maximum market price to consider (inclusive).

    Default: $0.50. Set via PRICE_MAX env var.
    Note: Old docs claimed $0.35; config enforces $0.50 for consistency.
    """

    MIN_EV: float = float(os.getenv('MIN_EV', '0.10'))
    """Minimum expected value fraction required to consider a trade.

    Default: 10% (0.10). Set via MIN_EV env var.
    WARNING: Changing this requires updating agent prompts too!
    """

    MIN_BET: float = float(os.getenv('MIN_BET', '1.0'))
    """Minimum bet size in dollars.

    Default: $1. Set via MIN_BET env var.
    WARNING: Changing this requires updating agent prompts too!
    """

    # ==================================================================
    # Risk — CONSERVATIVE defaults
    # ==================================================================
    STOP_LOSS_PCT: float = float(os.getenv('STOP_LOSS_PCT', '0.15'))
    """Stop-loss percentage per trade.

    Default: 15% (0.15). Set via STOP_LOSS_PCT env var.
    Per-trade stop loss: position is closed if price moves against us by this %.
    """

    TAKE_PROFIT_PCT: float = float(os.getenv('TAKE_PROFIT_PCT', '0.50'))
    """Take-profit percentage per trade.

    Default: 50% (0.50). Set via TAKE_PROFIT_PCT env var.
    Per-trade take profit: position is closed if price moves in our favor by this %.
    """

    DAILY_LOSS_LIMIT: float = float(os.getenv('DAILY_LOSS_LIMIT', '0.05'))
    """Daily loss limit as fraction of starting balance.

    Default: 5% (0.05). Set via DAILY_LOSS_LIMIT env var.
    If daily P&L (balance - daily_start) / daily_start >= this limit, trading stops
    for the day. Enforced in risk_agent().
    """

    MAX_DAILY_TRADES: int = int(os.getenv('MAX_DAILY_TRADES', '5'))
    """Maximum number of trades allowed per day.

    Default: 5 trades per day. Set via MAX_DAILY_TRADES env var.
    Enforced in risk_agent() — once reached, all further trades are rejected.
    """

    MAX_DRAWDOWN: float = float(os.getenv('MAX_DRAWDOWN', '0.25'))
    """Maximum drawdown as fraction of peak balance.

    Default: 25% (0.25). Set via MAX_DRAWDOWN env var.
    If drawdown (peak_balance - current_balance) / peak_balance >= this limit,
    trading is suspended. Checked via circuit_breaker.
    """

    CIRCUIT_BREAKER_DRAWDOWN: float = float(os.getenv('CIRCUIT_BREAKER_DRAWDOWN', '0.25'))
    """Circuit breaker drawdown threshold.

    Same as MAX_DRAWDOWN default. When drawdown exceeds this, the circuit breaker
    triggers and trading stops until manually reset.
    """

    # ==================================================================
    # MiroFish
    # ==================================================================
    MIROFISH_ENABLED: bool = os.getenv('MIROFISH_ENABLED', 'true').lower() == 'true'
    """Whether MiroFish swarm intelligence is enabled.

    Default: true. Set via MIROFISH_ENABLED env var (true/false).
    When false, local fallback intelligence is used instead.
    """

    MIROFISH_URL: str = os.getenv('MIROFISH_URL', 'http://localhost:5001')
    """Base URL for MiroFish service.

    Default: http://localhost:5001. Set via MIROFISH_URL env var.
    """

    MIROFISH_CACHE_TTL: int = int(os.getenv('MIROFISH_CACHE_TTL', '3600'))
    """MiroFish cache time-to-live in seconds.

    Default: 3600 (1 hour). Set via MIROFISH_CACHE_TTL env var.
    """

    MIROFISH_SIMULATION_ROUNDS: int = int(os.getenv('MIROFISH_SIMULATION_ROUNDS', '50'))
    """Number of simulation rounds for MiroFish intelligence.

    Default: 50. Set via MIROFISH_SIMULATION_ROUNDS env var.
    More rounds = better intelligence but slower execution.
    """

    MIROFISH_AGENT_COUNT: int = int(os.getenv('MIROFISH_AGENT_COUNT', '50'))
    """Number of agents in the MiroFish swarm.

    Default: 50. Set via MIROFISH_AGENT_COUNT env var.
    More agents = more diverse intelligence but higher resource usage.
    """

    MIROFISH_USE_CACHE: bool = os.getenv('MIROFISH_USE_CACHE', 'true').lower() == 'true'
    """Whether to use MiroFish response caching.

    Default: true. Set via MIROFISH_USE_CACHE env var (true/false).
    """

    # ==================================================================
    # Model
    # ==================================================================
    MODEL_PATH: str = os.getenv('MODEL_PATH', 'models/comprehensive_model.json')
    """Path to the trained ML model file.

    Default: "models/comprehensive_model.json" relative to project root.
    Set via MODEL_PATH env var.
    """

    # ==================================================================
    # Logging
    # ==================================================================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    """Logging level.

    Default: "INFO". Set via LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    LOG_FILE: str = os.getenv('LOG_FILE', 'data/logs/trading.log')
    """Path to the log file.

    Default: "data/logs/trading.log" relative to project root.
    Set via LOG_FILE env var. Directory will be created if it doesn't exist.
    """

    # ==================================================================
    # Database
    # ==================================================================
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    """Database host address.

    Default: "localhost". Set via DB_HOST env var.
    """

    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    """Database port.

    Default: 5432 (Postgres). Set via DB_PORT env var.
    """

    DB_NAME: str = os.getenv('DB_NAME', 'polymarket_trading')
    """Database name.

    Default: "polymarket_trading". Set via DB_NAME env var.
    """

    DB_USER: str = os.getenv('DB_USER', 'trader')
    """Database user.

    Default: "trader". Set via DB_USER env var.
    """

    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    """Database password.

    Default: "" (empty). Set via DB_PASSWORD env var.
    """

    # ==================================================================
    # Redis
    # ==================================================================
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    """Redis host address.

    Default: "localhost". Set via REDIS_HOST env var.
    """

    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    """Redis port.

    Default: 6379. Set via REDIS_PORT env var.
    """

    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    """Redis database index.

    Default: 0. Set via REDIS_DB env var.
    """

    # ==================================================================
    # Live trading guard
    # ==================================================================
    ENABLE_LIVE_TRADING: bool = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
    """Whether live trading is enabled.

    Default: false. Set via ENABLE_LIVE_TRADING env var (true/false).
    WARNING: Live trading with real money is dangerous. Start with paper trading.
    """

    POLYMARKET_ALLOW_REAL_ORDERS: bool = os.getenv('POLYMARKET_ALLOW_REAL_ORDERS', 'false').lower() == 'true'
    """Whether to allow real orders on Polymarket.

    Default: false. Set via POLYMARKET_ALLOW_REAL_ORDERS env var (true/false).
    Always start with paper trading mode.
    """

    POLYMARKET_SANDBOX: bool = os.getenv('POLYMARKET_SANDBOX', 'true').lower() == 'true'
    """Whether to use Polymarket sandbox mode.

    Default: true. Set via POLYMARKET_SANDBOX env var (true/false).
    Sandbox mode uses test money only.
    """

    POLYMARKET_VERIFY_SSL: bool = os.getenv('POLYMARKET_VERIFY_SSL', 'true').lower() == 'true'
    """Whether to verify SSL certificates for Polymarket API requests.

    Default: true. Set via POLYMARKET_VERIFY_SSL env var (true/false).
    """


# ============================================================================
# Exported config instance
# ============================================================================

config: Config = Config()
TradingConfig = Config


def get_config() -> Config:
    return config