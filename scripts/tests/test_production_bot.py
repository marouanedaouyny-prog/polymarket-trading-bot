"""
Automated multi-run testing for Production LLM Bot
"""

import subprocess
import json
import os
import sys

os.makedirs('data/test_runs', exist_ok=True)

results = []

print("=" * 70)
print("AUTOMATED 5-RUN TEST FOR PRODUCTION LLM BOT")
print("=" * 70)

for run in range(1, 6):
    print(f"\n>>> RUN {run}/5")
    result = subprocess.run(
        ['python', '-W', 'ignore', 'production_llm_bot.py', 'paper'],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    output = result.stdout + result.stderr
    
    win_rate = 0
    profit = 0
    trades = 0
    stop_losses = 0
    
    lines = output.split('\n')
    for line in lines:
        if 'Win Rate:' in line:
            win_rate = float(line.split('Win Rate:')[1].split('%')[0].strip())
        if 'Profit:' in line and '$' in line:
            try:
                profit_str = line.split('Profit:')[1].split('(')[0].strip().replace('$', '').replace(',', '')
                profit = float(profit_str)
            except:
                pass
        if 'Total Trades:' in line:
            trades = int(line.split('Total Trades:')[1].strip())
        if 'Stop Losses:' in line:
            stop_losses = int(line.split('Stop Losses:')[1].strip())
    
    results.append({
        'run': run, 
        'win_rate': win_rate, 
        'profit': profit, 
        'trades': trades,
        'stop_losses': stop_losses
    })
    print(f"   Win Rate: {win_rate}% | Profit: ${profit:,.2f} | SL: {stop_losses}")

avg_win = sum(r['win_rate'] for r in results) / len(results)
avg_profit = sum(r['profit'] for r in results) / len(results)
avg_sl = sum(r['stop_losses'] for r in results) / len(results)

print(f"\n{'='*70}")
print("SUMMARY (5 Runs)")
print(f"{'='*70}")
for r in results:
    print(f"Run {r['run']}: {r['win_rate']}% win, ${r['profit']:,.2f} profit, {r['stop_losses']} SL")
print(f"\nAverage Win Rate: {avg_win:.1f}%")
print(f"Average Profit: ${avg_profit:,.2f}")
print(f"Average Stop Losses: {avg_sl:.1f}")
print(f"{'='*70}")

with open('data/test_runs/production_bot_tests.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to data/test_runs/production_bot_tests.json")