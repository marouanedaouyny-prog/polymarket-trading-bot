
import sys
import os
import random
from datetime import datetime

# Add src to path
sys.path.insert(0, os.getcwd())

def run_high_frequency_simulation(start_bal=20.0, num_trades=100):
    print(f"\n{'='*70}")
    print(f" HIGH-FREQUENCY SIMULATION: 100 TRADES/DAY")
    print(f" Starting Balance: ${start_bal:.2f}")
    print(f"{'='*70}\n")
    print(f"{'Trade':<6} | {'Price':<6} | {'Result':<6} | {'Profit':<8} | {'Balance':<8}")
    print("-" * 60)

    balance = start_bal
    fee = 0.07  # 7% fee per trade
    wins = 0
    losses = 0

    for i in range(1, num_trades + 1):
        if balance < 1.0:
            print(f"!!! Account Bankrupt at trade {i} !!!")
            break
            
        # Day trading: we trade markets with 50/50 probability (market making)
        # We need an edge to overcome the 7% fee.
        # Arbitrage/Market Making edge
        price = 0.50 # Market maker neutral stance
        bet_size = balance * 0.05 # 5% per trade for high volume
        
        # High win rate required to overcome fees
        win_prob = 0.58  # 58% win rate needed to overcome 7% fees
        won = random.random() < win_prob
        
        if won:
            wins += 1
            # Return on $0.50 price is 100% minus fee
            payout = bet_size * (1 - fee)
            profit = payout
        else:
            losses += 1
            profit = -bet_size
            
        balance += profit
        
        if i % 10 == 0 or i == 1:
            print(f"{i:<6} | ${price:.2f} | {'WIN' if won else 'LOSS':<6} | {profit:>+7.2f} | ${balance:>7.2f}")

    print(f"\n{'='*60}")
    print(f" FINAL REPORT (100 TRADES)")
    print(f" Initial: ${start_bal:.2f}")
    print(f" Final:   ${balance:.2f}")
    print(f" Win Rate: {(wins/num_trades)*100:.1f}%")
    print(f" ROI:     {((balance - start_bal) / start_bal) * 100:.1f}%")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_high_frequency_simulation()
