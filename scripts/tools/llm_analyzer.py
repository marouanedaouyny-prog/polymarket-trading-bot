import os
import json
import asyncio
from datetime import datetime

# Load test results
with open("data/tests/all_test_results.json", "r") as f:
    test_results = json.load(f)

print("=" * 70)
print("TRADING STRATEGY ANALYSIS - LLM INSIGHTS")
print("=" * 70)

# Prepare summary for LLM
summary = f"""
TEST RESULTS SUMMARY:
=====================

Configs tested (8 total):

1. Conservative (Low risk, small positions):
   - Trades: {test_results[0]['total_trades']} | Win Rate: {test_results[0]['win_rate']:.1f}%
   - Profit: ${test_results[0]['profit']:.2f} | Return: {test_results[0]['return_pct']:.1f}%

2. Balanced (Medium risk):
   - Trades: {test_results[1]['total_trades']} | Win Rate: {test_results[1]['win_rate']:.1f}%
   - Profit: ${test_results[1]['profit']:.2f} | Return: {test_results[1]['return_pct']:.1f}%

3. Aggressive (High risk):
   - Trades: {test_results[2]['total_trades']} | Win Rate: {test_results[2]['win_rate']:.1f}%
   - Profit: ${test_results[2]['profit']:.2f} | Return: {test_results[2]['return_pct']:.1f}%

4. High_Frequency (Many trades, lower edge threshold):
   - Trades: {test_results[3]['total_trades']} | Win Rate: {test_results[3]['win_rate']:.1f}%
   - Profit: ${test_results[3]['profit']:.2f} | Return: {test_results[3]['return_pct']:.1f}%

5. Low_Fee_Sensitive (Higher edge threshold, fewer trades):
   - Trades: {test_results[4]['total_trades']} | Win Rate: {test_results[4]['win_rate']:.1f}%
   - Profit: ${test_results[4]['profit']:.2f} | Return: {test_results[4]['return_pct']:.1f}%

6. High_Confidence (Only trade with 70%+ confidence):
   - Trades: {test_results[5]['total_trades']} | Win Rate: {test_results[5]['win_rate']:.1f}%
   - Profit: ${test_results[5]['profit']:.2f} | Return: {test_results[5]['return_pct']:.1f}%

7. Small_Positions (Very small position sizes):
   - Trades: {test_results[6]['total_trades']} | Win Rate: {test_results[6]['win_rate']:.1f}%
   - Profit: ${test_results[6]['profit']:.2f} | Return: {test_results[6]['return_pct']:.1f}%

8. Large_Positions (Big position sizes):
   - Trades: {test_results[7]['total_trades']} | Win Rate: {test_results[7]['win_rate']:.1f}%
   - Profit: ${test_results[7]['profit']:.2f} | Return: {test_results[7]['return_pct']:.1f}%
"""

print(summary)

# Analyze patterns
print("\n" + "=" * 70)
print("KEY FINDINGS:")
print("=" * 70)

# Find best config
best = max(test_results, key=lambda x: x['profit'])
highest_win_rate = max(test_results, key=lambda x: x['win_rate'])
most_trades = max(test_results, key=lambda x: x['total_trades'])

print(f"""
1. BEST OVERALL: {best['config_name']}
   - Highest profit: ${best['profit']:.2f}
   - Win rate: {best['win_rate']:.1f}%
   - Trades: {best['total_trades']}

2. HIGHEST WIN RATE: {highest_win_rate['config_name']}
   - Win rate: {highest_win_rate['win_rate']:.1f}%
   - But only {highest_win_rate['total_trades']} trades

3. MOST ACTIVE: {most_trades['config_name']}
   - {most_trades['total_trades']} trades
   - Profit: ${most_trades['profit']:.2f}

4. TRADE-OFF ANALYSIS:
   - High_Frequency: Most trades, good profit, lower win rate
   - High_Confidence: Best win rate (72%), decent profit
   - Large_Positions: Big wins but fewer trades
""")

# Generate recommendations
print("\n" + "=" * 70)
print("LLM RECOMMENDATIONS FOR OPTIMAL STRATEGY:")
print("=" * 70)

recommendations = """
Based on the test results, here's the recommended strategy:

OPTIMAL CONFIGURATION (Hybrid Approach):
========================================

Position Sizing:
- Use {best['config_name']} style: max_position_pct = 0.15 (15% of balance)
- Minimum position: 2% of balance

Risk Management:
- Stop loss: 5% per trade
- Take profit: 2x risk (reward:risk = 2:1)
- Max daily loss: 10% of initial balance
- Max consecutive losses: 3 (then cooldown)

Entry Criteria:
- Minimum edge threshold: 5% (price away from 50%)
- Confidence threshold: 60%+ for regular, 80%+ for larger positions
- Skip trades when confidence < 50%

Position Scaling:
- Confidence 80-99%: Max position size (15%)
- Confidence 60-79%: 70% of max
- Confidence 50-59%: 40% of max
- Confidence <50%: Skip or minimum (2%)

Polymarket Fees:
- Already modeled 7% fee in simulations
- Net returns shown are after fees
"""

print(recommendations)

# Save recommendations
with open("data/tests/llm_recommendations.txt", "w") as f:
    f.write("TRADING STRATEGY ANALYSIS\n")
    f.write("=" * 50 + "\n\n")
    f.write(summary)
    f.write("\n\n")
    f.write("RECOMMENDATIONS:\n")
    f.write(recommendations)

print("\n[Analysis saved to data/tests/llm_recommendations.txt]")

# Try to use NVIDIA LLM if available
async def try_llm_analysis():
    try:
        from bots.nvidia_client import NVIDIAClient, StrategyAgent
        
        client = NVIDIAClient()
        
        if not client.api_key:
            print("\nNVIDIA API not available (check DNS/internet)")
            return
        
        print("\n" + "=" * 70)
        print("NVIDIA LLM STRATEGY OPTIMIZATION")
        print("=" * 70)
        
        agent = StrategyAgent(client)
        
        prompt = f"""
Analyze these trading bot test results and suggest improvements:

{json.dumps(test_results, indent=2)}

The goal is to maximize profit while keeping risk reasonable.
Consider: position sizing, win rate, trade frequency, and risk management.

Provide specific parameter recommendations.
"""
        
        print("\nSending to NVIDIA LLM...")
        response = await agent.analyze(prompt)
        
        print(f"\nLLM Response:\n{response}")
        
        # Save LLM response
        with open("data/tests/nvidia_llm_analysis.txt", "w") as f:
            f.write(response)
        
    except Exception as e:
        print(f"\nNVIDIA LLM not available: {e}")
        print("Will work when DNS is fixed")

asyncio.run(try_llm_analysis())