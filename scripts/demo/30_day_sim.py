
import random

def run_30_day_simulation(start_bal=20.0, trades_per_day=100, days=30):
    print(f"\n{'='*70}")
    print(f" 30-DAY HFT SIMULATION: {days} Days @ {trades_per_day} trades/day")
    print(f" Starting Balance: ${start_bal:.2f}")
    print(f"{'='*70}\n")

    balance = start_bal
    fee = 0.07  # 7% fee per trade
    
    # We maintain a 60% win rate (requires high-edge strategy)
    win_prob = 0.60
    
    daily_history = []

    for d in range(1, days + 1):
        daily_profit = 0
        for t in range(1, trades_per_day + 1):
            if balance < 1.0:
                break
            
            # Risk Management: 5% of balance per trade
            bet_size = balance * 0.05
            won = random.random() < win_prob
            
            if won:
                # Return on trade (net of 7% fee)
                profit = (bet_size * (1 - fee))
            else:
                profit = -bet_size
            
            balance += profit
            daily_profit += profit
            
        daily_history.append(balance)
        print(f"Day {d:02d} | Daily Profit: {daily_profit:>+8.2f} | Balance: ${balance:>9.2f}")

    print(f"\n{'='*70}")
    print(f" 30-DAY FINAL REPORT")
    print(f" Initial: ${start_bal:.2f}")
    print(f" Final:   ${balance:.2f}")
    print(f" Total Trades: {days * trades_per_day}")
    print(f" Total ROI: {((balance - start_bal) / start_bal) * 100:.1f}%")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_30_day_simulation()
