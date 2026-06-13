"""
Test script for the enhanced trading system
"""

import sys
import os

# Add the src directory to the path
sys.path.append('src')

def test_enhanced_features():
    """Test all enhanced features of the trading system"""
    print("Testing Enhanced Trading System Features")
    print("=" * 50)

    # Test enhanced ML models
    print("1. Testing Enhanced Machine Learning Models...")
    try:
        from src.ml.enhanced_ml_models import EnhancedMLModels
        ml_system = EnhancedMLModels()
        ml_system.create_advanced_models()
        print("   OK Advanced ML models created successfully")
    except Exception as e:
        print(f"   Error with ML models: {e}")

    # Test enhanced risk management
    print("2. Testing Enhanced Risk Management...")
    try:
        from src.risk.advanced_risk_manager import AdvancedRiskManager
        risk_manager = AdvancedRiskManager()
        print("   OK Advanced risk management initialized")
    except Exception as e:
        print(f"   Error with risk management: {e}")

    # Test enhanced analytics
    print("3. Testing Enhanced Analytics...")
    try:
        from src.ml.enhanced_analytics import EnhancedAnalyticsAgent
        analytics_agent = EnhancedAnalyticsAgent()
        print("   OK Enhanced analytics agent initialized")
    except Exception as e:
        print(f"   Error with analytics: {e}")

    # Test enhanced dashboard
    print("4. Testing Enhanced Dashboard...")
    try:
        from src.monitoring.enhanced_dashboard import TradingDashboard
        dashboard = TradingDashboard()
        print("   OK Enhanced dashboard initialized")
    except Exception as e:
        print(f"   Error with dashboard: {e}")

    # Test enhanced core features
    print("5. Testing Enhanced Core Features...")
    try:
        from src.core.enhanced_features import BacktestingFramework
        backtest = BacktestingFramework()
        data = backtest._generate_sample_data()
        results = backtest.run_strategy_backtest("sample_strategy", data)
        print("   OK Enhanced backtesting framework working")
    except Exception as e:
        print(f"   Error with backtesting: {e}")

    print("\nEnhanced system test completed!")

def main():
    """Main test function"""
    test_enhanced_features()

if __name__ == "__main__":
    main()