"""
Type-annotated config module — single source of truth for all settings.

Conservative defaults safe for real-money trading.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT_DIR / 'config'

ENV_FILE = CONFIG_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
else:
    ROOT_ENV = ROOT_DIR / '.env'
    if ROOT_ENV.exists():
        load_dotenv(ROOT_ENV, override=True)


class Config:
    # ------------------------------------------------------------------
    # Polymarket API
    # ------------------------------------------------------------------
    POLYMARKET_API_KEY: str = os.getenv('POLYMARKET_API_KEY', '')
    POLYMARKET_API_SECRET: str = os.getenv('POLYMARKET_API_SECRET', '')
    POLYMARKET_API_PASSPHRASE: str = os.getenv('POLYMARKET_API_PASSPHRASE', '')
    POLYMARKET_API_URL: str = os.getenv('POLYMARKET_API_URL', 'https://gamma-api.polymarket.com')
    PRIVATE_KEY: str = os.getenv('PRIVATE_KEY', '')

    # ------------------------------------------------------------------
    # FastAPI
    # ------------------------------------------------------------------
    FASTAPI_API_KEY: str = os.getenv('FASTAPI_API_KEY', '')
    if not FASTAPI_API_KEY:
        raise ValueError("FASTAPI_API_KEY environment variable is required")
    FASTAPI_HOST: str = os.getenv('FASTAPI_HOST', '0.0.0.0')
    FASTAPI_PORT: int = int(os.getenv('FASTAPI_PORT', '8000'))

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    IP_WHITELIST_ENABLED: bool = os.getenv('IP_WHITELIST_ENABLED', 'false').lower() == 'true'
    ALLOWED_IPS: str = os.getenv('ALLOWED_IPS', '')
    MAX_REQUEST_SIZE: int = int(os.getenv('MAX_REQUEST_SIZE', '1048576'))
    RATE_LIMIT_ROOT: str = os.getenv('RATE_LIMIT_ROOT', '10/minute')
    RATE_LIMIT_HEALTH: str = os.getenv('RATE_LIMIT_HEALTH', '100/minute')
    RATE_LIMIT_METRICS: str = os.getenv('RATE_LIMIT_METRICS', '60/minute')

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ALLOW_ORIGINS: str = os.getenv('CORS_ALLOW_ORIGINS', '*')
    CORS_ALLOW_METHODS: str = os.getenv('CORS_ALLOW_METHODS', 'GET,POST,PUT,PATCH,DELETE')
    CORS_ALLOW_HEADERS: str = os.getenv('CORS_ALLOW_HEADERS', '*')

    # ------------------------------------------------------------------
    # Trading — CONSERVATIVE defaults safe for real money
    # ------------------------------------------------------------------
    STARTING_BALANCE: float = float(os.getenv('STARTING_BALANCE', '100.0'))
    MAX_POSITION_PCT: float = float(os.getenv('MAX_POSITION_PCT', '0.10'))   # 10% max
    MIN_EDGE: float = float(os.getenv('MIN_EDGE', '0.08'))                    # 8% minimum edge
    MIN_CONFIDENCE: float = float(os.getenv('MIN_CONFIDENCE', '85'))          # 85% min
    MIN_VOLUME: float = float(os.getenv('MIN_VOLUME', '10000'))               # $10k min volume
    PRICE_MIN: float = float(os.getenv('PRICE_MIN', '0.05'))                  # $0.05-$0.50 range
    PRICE_MAX: float = float(os.getenv('PRICE_MAX', '0.50'))
    MIN_EV: float = float(os.getenv('MIN_EV', '0.10'))                        # 10% expected value
    MIN_BET: float = float(os.getenv('MIN_BET', '1.0'))                       # $1 minimum bet

    # ------------------------------------------------------------------
    # Risk — CONSERVATIVE defaults
    # ------------------------------------------------------------------
    STOP_LOSS_PCT: float = float(os.getenv('STOP_LOSS_PCT', '0.15'))          # 15% stop-loss
    TAKE_PROFIT_PCT: float = float(os.getenv('TAKE_PROFIT_PCT', '0.50'))      # 50% take-profit
    DAILY_LOSS_LIMIT: float = float(os.getenv('DAILY_LOSS_LIMIT', '0.05'))    # 5% daily loss cap
    MAX_DAILY_TRADES: int = int(os.getenv('MAX_DAILY_TRADES', '5'))           # max 5 trades/day
    MAX_DRAWDOWN: float = float(os.getenv('MAX_DRAWDOWN', '0.25'))             # 25% max drawdown
    CIRCUIT_BREAKER_DRAWDOWN: float = float(os.getenv('CIRCUIT_BREAKER_DRAWDOWN', '0.25'))

    # ------------------------------------------------------------------
    # MiroFish
    # ------------------------------------------------------------------
    MIROFISH_ENABLED: bool = os.getenv('MIROFISH_ENABLED', 'true').lower() == 'true'
    MIROFISH_URL: str = os.getenv('MIROFISH_URL', 'http://localhost:5001')
    MIROFISH_CACHE_TTL: int = int(os.getenv('MIROFISH_CACHE_TTL', '3600'))
    MIROFISH_SIMULATION_ROUNDS: int = int(os.getenv('MIROFISH_SIMULATION_ROUNDS', '50'))
    MIROFISH_AGENT_COUNT: int = int(os.getenv('MIROFISH_AGENT_COUNT', '50'))
    MIROFISH_USE_CACHE: bool = os.getenv('MIROFISH_USE_CACHE', 'true').lower() == 'true'

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    MODEL_PATH: str = os.getenv('MODEL_PATH', 'models/comprehensive_model.json')

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'data/logs/trading.log')

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    DB_NAME: str = os.getenv('DB_NAME', 'polymarket_trading')
    DB_USER: str = os.getenv('DB_USER', 'trader')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))

    # ------------------------------------------------------------------
    # Live trading guard
    # ------------------------------------------------------------------
    ENABLE_LIVE_TRADING: bool = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
    POLYMARKET_ALLOW_REAL_ORDERS: bool = os.getenv('POLYMARKET_ALLOW_REAL_ORDERS', 'false').lower() == 'true'
    POLYMARKET_SANDBOX: bool = os.getenv('POLYMARKET_SANDBOX', 'true').lower() == 'true'
    POLYMARKET_VERIFY_SSL: bool = os.getenv('POLYMARKET_VERIFY_SSL', 'true').lower() == 'true'


config: Config = Config()
TradingConfig = Config


def get_config() -> Config:
    return config