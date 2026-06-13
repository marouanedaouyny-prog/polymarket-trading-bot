"""
Enhanced Configuration Management System
"""

import json
import os
from typing import Dict, Any

class EnhancedConfigManager:
    """Enhanced configuration management system"""

    def __init__(self):
        self.config_file = "config/enhanced_config.json"
        self.config = self._load_default_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            "risk_management": {
                "max_position_size": 0.15,
                "stop_loss_percent": 0.25,
                "take_profit_percent": 2.0,
                "daily_loss_limit": 0.20
            },
            "trading_parameters": {
                "min_edge_threshold": 0.65,
                "min_confidence_threshold": 65,
                "max_daily_trades": 50
            },
            "analytics_settings": {
                "volatility_window": 14,
                "correlation_analysis": True,
                "sentiment_analysis": True
            },
            "enhanced_features": {
                "machine_learning": True,
                "real_time_monitoring": True,
                "advanced_analytics": True
            }
        }

    def load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return self.config

    def save_config(self, config_data: Dict[str, Any]):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving configuration: {e}")

# Enhanced configuration system implementation