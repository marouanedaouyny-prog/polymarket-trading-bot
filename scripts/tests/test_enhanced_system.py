"""
Test script for the enhanced trading system
"""

import sys
import os

# Add the src directory to the path
sys.path.append('src')

from src.core.enhanced_trading_system import EnhancedTradingSystem

def main():
    """Test the enhanced trading system"""
    print("Testing Enhanced Trading System...")

    # Initialize the enhanced system
    system = EnhancedTradingSystem()

    # Run a test session
    metrics = system.run_enhanced_session(20)

    print("Test completed successfully!")

if __name__ == "__main__":
    main()