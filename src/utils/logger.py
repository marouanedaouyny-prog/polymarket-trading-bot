"""
Centralized Logging
All modules should import from here
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Create logs directory
LOG_DIR = Path(__file__).parent.parent.parent / 'data' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logger
logger = logging.getLogger('polymarket_trading')

# Set level from config if available
try:
    from .config import config
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
except:
    level = logging.INFO

logger.setLevel(level)

# File handler
log_file = LOG_DIR / f'trading_{datetime.now().strftime("%Y%m%d")}.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(level)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(level)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name=None):
    """Get a logger instance"""
    if name:
        return logging.getLogger(f'polymarket_trading.{name}')
    return logger

# Convenience functions
def info(msg, **kwargs):
    logger.info(msg, **kwargs)

def error(msg, **kwargs):
    logger.error(msg, **kwargs)

def warning(msg, **kwargs):
    logger.warning(msg, **kwargs)

def debug(msg, **kwargs):
    logger.debug(msg, **kwargs)