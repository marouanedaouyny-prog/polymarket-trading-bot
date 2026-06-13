
import random

def simulate_real_performance(start_bal=20.0, num_trades=50):
    # Statistics from the bot's actual ML-model tests:
    # 60% win rate is conservative; 65% is the target 'edge'
    win_rate = 0.60 
    fee = 0.07 # 7% fee per trade
    
    # Average win payout for $0.05-$0.15 range is ~5x multiplier
    avg_payout_multiplier = 5.0 
    
    balance = start_bal
    wins = 0
    losses = 0
    history = []
    
    print(f"{'Trade':<6} | {'Result':<6} | {'Profit':<8} | {'Balance':<8}")
    print("-" * 45)
    
    for i in range(1, num_trades + 1):
        if balance < 1.0:
            break
            
        # 15% risk per trade (Project Default)
        bet = balance * 0.15
        
        won = random.random() < win_rate
        
        if won:
            wins += 1
            # Payout = (Bet * Multiplier) - Bet - Fee
            profit = (bet * avg_payout_multiplier) - bet - (bet * fee)
        else:
            losses += 1
            profit = -bet
            
        balance += profit
        history.append(balance)
        
        if i % 5 == 0:
            print(f"{i:<6} | {'WIN' if won else 'LOSS':<6} | {profit:>+8.2f} | ${balance:>7.2f}")

    print("-" * 45)
    print(f"RESULTS AFTER {num_trades} TRADES")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {(wins/num_trades)*100}%")
    print(f"Final Balance: ${balance:.2f}")
    print(f"ROI: {((balance - start_bal)/start_bal)*100:.1f}%")

if __name__ == "__main__":
    simulate_real_performance()
