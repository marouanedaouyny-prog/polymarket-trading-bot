"""
Automated multi-run testing for LLM Trader v2
"""

import subprocess
import json
from datetime import datetime
import os

os.makedirs('data/test_runs', exist_ok=True)

results = []

print("=" * 70)
print("AUTOMATED 5-RUN TEST FOR LLM TRADER v2")
print("=" * 70)

for run in range(1, 6):
    print(f"\n>>> RUN {run}/5")
    result = subprocess.run(
        ['python', '-W', 'ignore', 'llm_intelligent_trader_v2.py'],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    output = result.stdout + result.stderr
    
    # Parse results
    lines = output.split('\n')
    for line in lines:
        if 'Win Rate:' in line:
            win_rate = float(line.split('Win Rate:')[1].split('%')[0].strip())
        if 'Profit:' in line and '$' in line:
            profit_str = line.split('Profit:')[1].split('(')[0].strip().replace('$', '')
            profit = float(profit_str)
        if 'Trades:' in line:
            trades = int(line.split('Trades:')[1].strip())
    
    results.append({'run': run, 'win_rate': win_rate, 'profit': profit, 'trades': trades})
    print(f"   Win Rate: {win_rate}% | Profit: ${profit:,.2f}")

avg_win = sum(r['win_rate'] for r in results) / len(results)
avg_profit = sum(r['profit'] for r in results) / len(results)

print(f"\n{'='*70}")
print("SUMMARY (5 Runs)")
print(f"{'='*70}")
for r in results:
    print(f"Run {r['run']}: {r['win_rate']}% win rate, ${r['profit']:,.2f} profit")
print(f"\nAverage Win Rate: {avg_win:.1f}%")
print(f"Average Profit: ${avg_profit:,.2f}")
print(f"{'='*70}")

with open('data/test_runs/llm_trader_v2_tests.json', 'w') as f:
    json.dump(results, f, indent=2)