"""
Quick stability test - run 50 sessions of trading directly
"""

import json
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.makedirs('data/test_runs', exist_ok=True)

# Run 50 sessions
num_sessions = 50

total_wins = 0
total_losses = 0
total_profit = 0

print(f"=" * 60)
print(f"STABILITY TEST: {num_sessions} SESSIONS")
print(f"=" * 60)

for run in range(1, num_sessions + 1):
    # Import and run each session fresh
    from agent_trading_system import TradingAgentSystem
    
    system = TradingAgentSystem(starting_balance=100)
    result = system.lead_agent(max_trades=20)
    
    total_wins += system.stats['wins']
    total_losses += system.stats['losses']
    total_profit += system.balance - system.initial_balance
    
    # Progress
    if run % 10 == 0:
        total_trades = total_wins + total_losses
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        print(f"  Session {run}/{num_sessions} | Win Rate: {win_rate:.1f}% | Profit: ${total_profit:,.0f}")

# Summary
total_trades = total_wins + total_losses
win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

print(f"\n{'='*60}")
print(f"STABILITY TEST RESULTS")
print(f"{'='*60}")
print(f"Total Sessions: {num_sessions}")
print(f"Total Trades: {total_trades}")
print(f"Wins: {total_wins} | Losses: {total_losses}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Total Profit: ${total_profit:,.2f}")
print(f"{'='*60}")

with open('data/test_runs/stability_50.json', 'w') as f:
    json.dump({
        'sessions': num_sessions,
        'total_trades': total_trades,
        'wins': total_wins,
        'losses': total_losses,
        'win_rate': win_rate,
        'profit': total_profit
    }, f, indent=2)