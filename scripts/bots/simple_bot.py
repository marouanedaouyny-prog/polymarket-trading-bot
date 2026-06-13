import random
import csv
from datetime import datetime

class SimpleTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        
    def run_simulation(self, num_trades=50):
        print(f"Running {num_trades} paper trades...")
        
        for i in range(num_trades):
            market = {
                'yes_price': random.uniform(0.30, 0.70),
                'no_price': lambda: 1.0 - self.yes_price,
                'volume': random.uniform(1000, 100000),
            }
            market['no_price'] = 1.0 - market['yes_price']
            
            edge = abs(market['yes_price'] - 0.5)
            
            if edge < 0.02:
                print(f"Trade {i+1}: SKIP (no edge)")
                continue
                
            position_size = min(self.balance * 0.03, 5.0)
            
            win = random.random() < 0.80
            
            if win:
                profit = position_size * edge * 2
                self.balance += profit
                self.win_count += 1
                status = "WIN"
            else:
                loss = position_size * 0.05
                self.balance -= loss
                status = "LOSE"
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            print(f"Trade {i+1}: {status} ${abs(profit if win else -loss):.4f} | Balance: ${self.balance:.2f}")
            
            if self.balance < 1.0:
                print("Bankrupt!")
                break
        
        return self.trades
    
    def get_stats(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        print(f"\n=== Results ===")
        print(f"Trades: {self.total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${self.balance - self.initial_balance:.2f}")
        print(f"Return: {((self.balance/self.initial_balance)-1)*100:.1f}%")

if __name__ == "__main__":
    bot = SimpleTradingBot(initial_balance=10.0)
    bot.run_simulation(50)
    bot.get_stats()
    
    with open("data/results/simple_paper_trades.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trade_id", "balance", "profit", "win"])
        for i in range(len(bot.trades)):
            writer.writerow([i+1, bot.trades[i].get('balance', 0), bot.trades[i].get('profit', 0), bot.trades[i].get('win', False)])
    
    print("\nSaved to data/results/simple_paper_trades.csv")