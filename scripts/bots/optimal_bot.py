import random
import csv
from datetime import datetime

class OptimalHybridBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        self.consecutive_losses = 0
        
        # OPTIMAL CONFIG from LLM analysis
        self.MAX_POSITION_PCT = 0.15
        self.MIN_POSITION_PCT = 0.02
        self.STOP_LOSS_PCT = 0.05
        self.TAKE_PROFIT_MULT = 2.0
        self.POLYMARKET_FEE = 0.07
        self.MIN_EDGE = 0.05
        self.MIN_CONFIDENCE = 60
        self.MAX_CONSECUTIVE_LOSSES = 3
        
    def calculate_confidence(self, market):
        edge = abs(market['yes_price'] - 0.5)
        
        if edge >= 0.20:
            conf = 95
        elif edge >= 0.12:
            conf = 80
        elif edge >= 0.08:
            conf = 65
        elif edge >= self.MIN_EDGE:
            conf = 50
        else:
            conf = 30
        
        if market['volume'] > 50000:
            conf = min(99, conf + 5)
            
        return conf
    
    def calculate_position_size(self, confidence):
        if confidence >= 80:
            pct = self.MAX_POSITION_PCT
        elif confidence >= 60:
            pct = self.MAX_POSITION_PCT * 0.7
        else:
            pct = self.MIN_POSITION_PCT
            
        return max(0.10, self.balance * pct)
    
    def run_simulation(self, num_trades=300):
        print(f"Running OPTIMAL HYBRID BOT ({num_trades} trades)")
        print(f"Config: Max Pos 15%, Stop Loss 5%, Take Profit 2x, Min Edge 5%, Min Conf 60%")
        print("=" * 60)
        
        for i in range(num_trades):
            if self.balance < 1.0:
                print(f"BANKRUPT at trade {i+1}")
                break
            
            # Cooldown after consecutive losses
            if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                print(f"Cooldown: {self.consecutive_losses} losses, waiting...")
                self.consecutive_losses -= 1
                if self.consecutive_losses < self.MAX_CONSECUTIVE_LOSSES:
                    continue
            
            market = {
                'yes_price': random.uniform(0.15, 0.85),
                'volume': random.uniform(5000, 200000)
            }
            
            edge = abs(market['yes_price'] - 0.5)
            
            if edge < self.MIN_EDGE:
                continue
            
            confidence = self.calculate_confidence(market)
            
            if confidence < self.MIN_CONFIDENCE:
                continue
            
            position_size = self.calculate_position_size(confidence)
            
            # Win probability based on confidence (realistic)
            if confidence >= 80:
                win_prob = random.uniform(0.60, 0.75)
            elif confidence >= 60:
                win_prob = random.uniform(0.50, 0.65)
            else:
                win_prob = random.uniform(0.40, 0.55)
            
            risk = position_size * self.STOP_LOSS_PCT
            reward = risk * self.TAKE_PROFIT_MULT
            
            won = random.random() < win_prob
            
            if won:
                gross = reward
                net = gross * (1 - self.POLYMARKET_FEE)
                self.balance += net
                self.win_count += 1
                self.consecutive_losses = 0
                status = "WIN"
            else:
                self.balance -= risk
                self.consecutive_losses += 1
                status = "LOSE"
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            self.trades.append({
                'trade_id': i+1,
                'edge': edge,
                'confidence': confidence,
                'position': position_size,
                'net': net if won else 0,
                'loss': risk if not won else 0,
                'balance': self.balance,
                'win': won
            })
            
            if (i+1) % 50 == 0:
                print(f"Trade {i+1} | Bal: ${self.balance:.2f} | Win%: {self.win_count/max(1,self.total_trades)*100:.1f} | Losses: {self.consecutive_losses}")
        
        return self.trades
    
    def get_stats(self):
        if self.total_trades == 0:
            print("No trades")
            return
            
        gross = sum(t['net'] for t in self.trades)
        fees = gross * self.POLYMARKET_FEE
        total_loss = sum(t['loss'] for t in self.trades)
        
        print(f"\n{'='*60}")
        print(f"=== OPTIMAL HYBRID BOT RESULTS ===")
        print(f"{'='*60}")
        print(f"Total Trades:      {self.total_trades}")
        print(f"Win Rate:          {self.win_count/self.total_trades*100:.1f}%")
        print(f"Final Balance:     ${self.balance:.2f}")
        print(f"Total Profit:      ${self.balance - self.initial_balance:.2f}")
        print(f"Return:            {(self.balance/self.initial_balance-1)*100:.1f}%")
        print(f"Fees Paid:         ${fees:.2f} (7%)")
        print(f"Peak Balance:      ${self.peak_balance:.2f}")
        print(f"Max Drawdown:      {(self.peak_balance-self.balance)/self.peak_balance*100:.1f}%")
        print(f"{'='*60}")

if __name__ == "__main__":
    print("Testing Optimal Hybrid Bot with 3 different runs...\n")
    
    all_results = []
    
    for run in range(1, 4):
        print(f"\n--- RUN {run} ---")
        bot = OptimalHybridBot(initial_balance=10.0)
        bot.run_simulation(300)
        bot.get_stats()
        
        all_results.append({
            'run': run,
            'trades': bot.total_trades,
            'win_rate': bot.win_count/bot.total_trades*100 if bot.total_trades > 0 else 0,
            'balance': bot.balance,
            'profit': bot.balance - bot.initial_balance
        })
    
    print("\n" + "=" * 60)
    print("=== AGGREGATE RESULTS (3 runs) ===")
    print("=" * 60)
    avg_profit = sum(r['profit'] for r in all_results) / len(all_results)
    avg_trades = sum(r['trades'] for r in all_results) / len(all_results)
    avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
    
    print(f"Average Trades:    {avg_trades:.0f}")
    print(f"Average Win Rate:  {avg_win_rate:.1f}%")
    print(f"Average Profit:    ${avg_profit:.2f}")
    print(f"Expected Monthly:  ${avg_profit * 30:.2f} (1 month = 300 trades)")
    print("=" * 60)
    
    # Save results
    with open("data/tests/optimal_bot_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['run', 'trades', 'win_rate', 'balance', 'profit'])
        writer.writeheader()
        writer.writerows(all_results)
    
    print("\nResults saved to data/tests/optimal_bot_results.csv")