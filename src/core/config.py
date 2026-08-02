"""
Core configuration — delegates to the unified config in src.utils.config.
Kept for backward-compatible imports.
"""

from src.utils.config import config, Config, get_config

__all__ = ["config", "Config", "get_config"]