"""
Type-annotated config module
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).parent.parent / 'config'

ENV_FILE = CONFIG_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    ROOT_ENV = Path(__file__).parent.parent / '.env'
    if ROOT_ENV.exists():
        load_dotenv(ROOT_ENV)

class Config:
    # Polymarket API
    POLYMARKET_API_KEY: str = os.getenv('POLYMARKET_API_KEY', '')
    POLYMARKET_API_SECRET: str = os.getenv('POLYMARKET_API_SECRET', '')
    POLYMARKET_API_PASSPHRASE: str = os.getenv('POLYMARKET_API_PASSPHRASE', '')
    POLYMARKET_API_URL: str = os.getenv('POLYMARKET_API_URL', 'https://gamma-api.polymarket.com')
    
    # FastAPI
    FASTAPI_API_KEY: str = os.getenv('FASTAPI_API_KEY', 'dev_api_key_12345')
    FASTAPI_HOST: str = os.getenv('FASTAPI_HOST', '0.0.0.0')
    FASTAPI_PORT: int = int(os.getenv('FASTAPI_PORT', '8000'))
    
    # Trading Config
    STARTING_BALANCE: float = float(os.getenv('STARTING_BALANCE', '100'))
    MAX_POSITION_PCT: float = float(os.getenv('MAX_POSITION_PCT', '0.15'))
    MIN_EDGE: float = float(os.getenv('MIN_EDGE', '0.65'))
    MIN_CONFIDENCE: float = float(os.getenv('MIN_CONFIDENCE', '65'))
    MIN_VOLUME: float = float(os.getenv('MIN_VOLUME', '15000'))
    PRICE_MIN: float = float(os.getenv('PRICE_MIN', '0.01'))
    PRICE_MAX: float = float(os.getenv('PRICE_MAX', '0.35'))
    
    # Risk Config
    STOP_LOSS_PCT: float = float(os.getenv('STOP_LOSS_PCT', '0.25'))
    TAKE_PROFIT_PCT: float = float(os.getenv('TAKE_PROFIT_PCT', '2.0'))
    DAILY_LOSS_LIMIT: float = float(os.getenv('DAILY_LOSS_LIMIT', '0.20'))
    MAX_DAILY_TRADES: int = int(os.getenv('MAX_DAILY_TRADES', '20'))
    
    # MiroFish Configuration
    MIROFISH_ENABLED: bool = os.getenv('MIROFISH_ENABLED', 'true').lower() == 'true'
    MIROFISH_URL: str = os.getenv('MIROFISH_URL', 'http://localhost:5001')
    MIROFISH_CACHE_TTL: int = int(os.getenv('MIROFISH_CACHE_TTL', '3600'))
    MIROFISH_SIMULATION_ROUNDS: int = int(os.getenv('MIROFISH_SIMULATION_ROUNDS', '50'))
    MIROFISH_AGENT_COUNT: int = int(os.getenv('MIROFISH_AGENT_COUNT', '50'))
    MIROFISH_USE_CACHE: bool = os.getenv('MIROFISH_USE_CACHE', 'true').lower() == 'true'
    
    # Model
    MODEL_PATH: str = os.getenv('MODEL_PATH', 'models/comprehensive_model.json')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'data/logs/trading.log')

config: Config = Config()

def get_config() -> Config:
    return config
