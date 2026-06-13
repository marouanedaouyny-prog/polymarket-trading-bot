"""
Logging module for the Polymarket trading bot.
"""

import logging
import os
from datetime import datetime

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the application."""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger("polymarket_bot")
    return logger

class Logger:
    """Centralized logger for the trading bot."""

    def __init__(self):
        self.logger = setup_logging()

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)