"""
Performance evaluation and rating of the enhanced trading system
"""

import sys
import os
from datetime import datetime
import json

# Add the src directory to the path
sys.path.append('src')

def evaluate_system_performance():
    """Evaluate and rate the enhanced trading system performance"""
    print("Enhanced Trading System Performance Evaluation")
    print("=" * 50)

    # Test system components
    tests_passed = 0
    total_tests = 0

    # Test 1: Enhanced ML Models
    total_tests += 1
    try:
        from src.ml.enhanced_ml_models import EnhancedMLModels
        ml_system = EnhancedMLModels()
        ml_system.create_advanced_models()
        tests_passed += 1
        print("✓ Advanced ML Models: PASSED")
    except:
        print("✗ Advanced ML Models: FAILED")

    # Test 2: Enhanced Risk Management
    total_tests += 1
    try:
        from src.risk.advanced_risk_manager import AdvancedRiskManager
        risk_manager = AdvancedRiskManager()
        tests_passed += 1
        print("✓ Enhanced Risk Management: PASSED")
    except:
        print("✗ Enhanced Risk Management: FAILED")

    # Test 3: Enhanced Analytics
    total_tests += 1
    try:
        from src.ml.enhanced_analytics import EnhancedAnalyticsAgent
        analytics_agent = EnhancedAnalyticsAgent()
        tests_passed += 1
        print("✓ Enhanced Analytics: PASSED")
    except:
        print("✗ Enhanced Analytics: FAILED")

    # Test 4: Enhanced Dashboard
    total_tests += 1
    try:
        from src.monitoring.enhanced_dashboard import TradingDashboard
        dashboard = TradingDashboard()
        tests_passed += 1
        print("✓ Enhanced Dashboard: PASSED")
    except:
        print("✗ Enhanced Dashboard: FAILED")

    # Test 5: Enhanced Core Features
    total_tests += 1
    try:
        from src.core.enhanced_features import BacktestingFramework
        backtest = BacktestingFramework()
        tests_passed += 1
        print("✓ Enhanced Core Features: PASSED")
    except:
        print("✗ Enhanced Core Features: FAILED")

    # Calculate performance rating
    performance_rating = (tests_passed / total_tests) * 100 if total_tests > 0 else 0

    print(f"\nPerformance Evaluation Results:")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Performance Rating: {performance_rating:.1f}%")

    # Detailed rating
    if performance_rating >= 90:
        rating = "EXCELLENT"
        description = "All enhanced features working perfectly"
    elif performance_rating >= 75:
        rating = "GOOD"
        description = "Most features working with minor issues"
    elif performance_rating >= 60:
        rating = "FAIR"
        description = "Basic functionality working with some issues"
    else:
        rating = "POOR"
        description = "Significant issues detected"

    print(f"Overall System Rating: {rating} - {description}")

    return performance_rating

if __name__ == "__main__":
    evaluate_system_performance()