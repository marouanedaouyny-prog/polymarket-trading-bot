"""
Core configuration module for the Polymarket trading bot.
Handles environment variables, settings, and configuration management.
"""

import os
from typing import Optional

# Load environment variables
def get_env_var(var_name: str, default: Optional[str] = None) -> str:
    """Get environment variable or return default value."""
    return os.environ.get(var_name, default)

class Config:
    """Configuration class for the trading bot."""

    def __init__(self):
        # API Keys
        self.polymarket_api_key = get_env_var("POLYMARKET_API_KEY")
        self.polymarket_api_secret = get_env_var("POLYMARKET_API_SECRET")
        self.polymarket_api_passphrase = get_env_var("POLYMARKET_API_PASSPHRASE")

        # Database configuration
        self.db_host = get_env_var("DB_HOST", "localhost")
        self.db_port = int(get_env_var("DB_PORT", "5432"))
        self.db_name = get_env_var("DB_NAME", "polymarket_trading")
        self.db_user = get_env_var("DB_USER", "trader")
        self.db_password = get_env_var("DB_PASSWORD", "secret123")

        # Redis configuration
        self.redis_host = get_env_var("REDIS_HOST", "localhost")
        self.redis_port = int(get_env_var("REDIS_PORT", "6379"))
        self.redis_db = int(get_env_var("REDIS_DB", "0"))

        # Risk settings
        self.max_position_size = float(get_env_var("MAX_POSITION_SIZE", "0.05"))  # 5% default
        self.daily_loss_limit = float(get_env_var("DAILY_LOSS_LIMIT", "0.05"))  # 5% default
        self.max_drawdown_limit = float(get_env_var("MAX_DRAWDOWN", "0.10"))  # 10% default

# Global config instance
config = Config()
