"""
Automated stress test - 5000+ trades to verify stability
"""

import subprocess
import json
import os

os.makedirs('data/test_runs', exist_ok=True)

# Run 250 sessions of 20 trades each = 5000 trades
num_sessions = 250
trades_per_session = 20

results = []
total_trades = 0
total_wins = 0
total_losses = 0
total_profit = 0

print(f"=" * 70)
print(f"STRESS TEST: {num_sessions} SESSIONS x {trades_per_session} TRADES = {num_sessions * trades_per_session} TOTAL")
print(f"=" * 70)

for run in range(1, num_sessions + 1):
    result = subprocess.run(
        ['python', '-W', 'ignore', 'agent_trading_system.py'],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    output = result.stdout + result.stderr
    
    win_rate = 0
    profit = 0
    trades = 0
    wins = 0
    losses = 0
    
    lines = output.split('\n')
    for line in lines:
        if 'Win Rate:' in line:
            try:
                win_rate = float(line.split('Win Rate:')[1].split('%')[0].strip())
            except:
                pass
        if 'Total Trades:' in line:
            try:
                trades = int(line.split('Total Trades:')[1].strip())
            except:
                pass
        if 'Wins:' in line:
            try:
                wins_str = line.split('Wins:')[1].split('|')[0].strip()
                wins = int(wins_str)
                losses_str = line.split('Losses:')[1].strip().split()[0]
                losses = int(losses_str)
            except:
                pass
        if 'Profit:' in line and '$' in line:
            try:
                profit_str = line.split('Profit:')[1].split('(')[0].strip().replace('$', '').replace(',', '')
                profit = float(profit_str)
            except:
                pass
    
    total_trades += trades
    total_wins += wins
    total_losses += losses
    total_profit += profit
    
    # Progress update every 25 sessions
    if run % 25 == 0:
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        print(f"  Progress: {run}/{num_sessions} sessions | {total_trades} trades | "
              f"Win Rate: {overall_win_rate:.1f}% | Profit: ${total_profit:,.2f}")

# Final summary
overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

print(f"\n{'='*70}")
print(f"STRESS TEST RESULTS")
print(f"{'='*70}")
print(f"Total Sessions: {num_sessions}")
print(f"Total Trades: {total_trades}")
print(f"Wins: {total_wins} | Losses: {total_losses}")
print(f"Overall Win Rate: {overall_win_rate:.2f}%")
print(f"Total Profit: ${total_profit:,.2f}")
print(f"Average Profit/Session: ${total_profit/num_sessions:,.2f}")
print(f"{'='*70}")

# Save results
with open('data/test_runs/stress_test_5000.json', 'w') as f:
    json.dump({
        'sessions': num_sessions,
        'total_trades': total_trades,
        'wins': total_wins,
        'losses': total_losses,
        'win_rate': overall_win_rate,
        'total_profit': total_profit
    }, f, indent=2)

print(f"\nResults saved to data/test_runs/stress_test_5000.json")