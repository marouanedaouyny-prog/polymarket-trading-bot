"""
Settings module for application configuration.
"""

import os
from typing import Optional

class Settings:
    """Application settings and configuration."""

    def __init__(self):
        # Load from environment variables
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

        # API settings
        self.polymarket_api_key = os.getenv("POLYMARKET_API_KEY")
        self.polymarket_api_secret = os.getenv("POLYMARKET_API_SECRET")
        self.polymarket_api_passphrase = os.getenv("POLYMARKET_API_PASSPHRASE")

        # Database settings
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "polymarket_trading")
        self.db_user = os.getenv("DB_USER", "trader")
        self.db_password = os.getenv("DB_PASSWORD", "secret123")

        # Redis settings
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))

        # Risk settings
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.05"))
        self.daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT", "0.05"))
        self.max_drawdown_limit = float(os.getenv("MAX_DRAWDOWN", "0.10"))

# Global settings instance
settings = Settings()
