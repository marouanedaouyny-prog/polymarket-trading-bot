"""
Enhanced Trading System Main Controller
"""

import json
import os
import sys
from datetime import datetime
from src.agents.enhanced_trading_agent import EnhancedTradingAgent

class EnhancedTradingSystem:
    """Main enhanced trading system controller"""

    def __init__(self):
        self.agent = EnhancedTradingAgent()
        self.performance_metrics = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0.0
        }

    def run_enhanced_session(self, max_trades: int = 50):
        """Run an enhanced trading session with all new features"""
        print("Enhanced Trading System Session Started")

        # Initialize the enhanced trading agent
        enhanced_agent = self.agent
        metrics = enhanced_agent.run_enhanced_session(max_trades)

        return metrics

if __name__ == "__main__":
    # Run the enhanced system
    system = EnhancedTradingSystem()
    metrics = system.run_enhanced_session()
    print("Enhanced trading system completed session")