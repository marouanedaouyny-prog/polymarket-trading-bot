"""
Automated test - 1000 trades to verify stability
"""

import subprocess
import json
import os
import sys

os.makedirs('data/test_runs', exist_ok=True)

# Run 50 sessions of 20 trades each = 1000 trades
num_sessions = 50

results = []
total_trades = 0
total_wins = 0
total_losses = 0
total_profit = 0

print(f"=" * 70)
print(f"STABILITY TEST: {num_sessions} SESSIONS x 20 TRADES = 1000 TOTAL")
print(f"=" * 70)

for run in range(1, num_sessions + 1):
    result = subprocess.run(
        ['python', '-W', 'ignore', 'agent_trading_system.py'],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        timeout=30
    )
    
    output = result.stdout + result.stderr
    
    wins = 0
    losses = 0
    
    lines = output.split('\n')
    for line in lines:
        if 'Wins:' in line:
            try:
                wins = int(line.split('Wins:')[1].split('|')[0].strip())
                losses_str = line.split('Losses:')[1].strip().split()[0]
                losses = int(losses_str)
            except:
                pass
        if 'Profit:' in line and 'Balance:' not in line and '->' not in line:
            try:
                profit_str = line.split('Profit:')[1].split('(')[0].strip().replace('$', '').replace(',', '')
                profit = float(profit_str)
            except:
                pass
    
    total_wins += wins
    total_losses += losses
    total_trades += wins + losses
    
    # Progress update every 10 sessions
    if run % 10 == 0:
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        print(f"  Progress: {run}/{num_sessions} | {total_trades} trades | Win Rate: {overall_win_rate:.1f}%")

# Final summary
overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

print(f"\n{'='*70}")
print(f"STABILITY TEST RESULTS")
print(f"{'='*70}")
print(f"Total Sessions: {num_sessions}")
print(f"Total Trades: {total_trades}")
print(f"Wins: {total_wins} | Losses: {total_losses}")
print(f"Overall Win Rate: {overall_win_rate:.2f}%")
print(f"{'='*70}")

# Save results
with open('data/test_runs/stability_test_1000.json', 'w') as f:
    json.dump({
        'sessions': num_sessions,
        'total_trades': total_trades,
        'wins': total_wins,
        'losses': total_losses,
        'win_rate': overall_win_rate
    }, f, indent=2)

print(f"Results saved!")