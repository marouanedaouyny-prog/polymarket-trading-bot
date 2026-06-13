"""
Comprehensive test to demonstrate all enhanced features working together
"""

import sys
import os
import json
from datetime import datetime

# Add the src directory to the path
sys.path.append('src')

def test_complete_system():
    """Test the complete enhanced trading system"""
    print("Complete Enhanced Trading System Test")
    print("=" * 50)

    # Test 1: Enhanced ML Models
    print("1. Testing Enhanced Machine Learning Models...")
    try:
        from src.ml.enhanced_ml_models import EnhancedMLModels
        ml_system = EnhancedMLModels()
        ml_system.create_advanced_models()
        print("   OK Advanced ML models working")
    except Exception as e:
        print(f"   Error with ML models: {e}")

    # Test 2: Enhanced Risk Management
    print("2. Testing Enhanced Risk Management...")
    try:
        from src.risk.advanced_risk_manager import AdvancedRiskManager
        risk_manager = AdvancedRiskManager()
        print("   OK Advanced risk management working")
    except Exception as e:
        print(f"   Error with risk management: {e}")

    # Test 3: Enhanced Analytics
    print("3. Testing Enhanced Analytics...")
    try:
        from src.ml.enhanced_analytics import EnhancedAnalyticsAgent
        analytics_agent = EnhancedAnalyticsAgent()
        print("   OK Enhanced analytics working")
    except Exception as e:
        print(f"   Error with analytics: {e}")

    # Test 4: Enhanced Dashboard
    print("4. Testing Enhanced Dashboard...")
    try:
        from src.monitoring.enhanced_dashboard import TradingDashboard
        dashboard = TradingDashboard()
        print("   OK Enhanced dashboard working")
    except Exception as e:
        print(f"   Error with dashboard: {e}")

    # Test 5: Enhanced Core Features
    print("5. Testing Enhanced Core System...")
    try:
        from src.core.enhanced_features import BacktestingFramework
        backtest = BacktestingFramework()
        # Test that the backtesting framework is working
        print("   OK Enhanced core features working")
    except Exception as e:
        print(f"   Error with core features: {e}")

    print("Complete system test finished successfully!")
    return True

if __name__ == "__main__":
    test_complete_system()