import random
import csv
import json
import time
from datetime import datetime
from data.polymarket_client import PolymarketClient

class LiveTrainingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        self.client = PolymarketClient()
        
        # Optimal config
        self.MAX_POSITION_PCT = 0.15
        self.STOP_LOSS_PCT = 0.05
        self.TAKE_PROFIT_MULT = 2.0
        self.POLYMARKET_FEE = 0.07
        self.MIN_EDGE = 0.05
        self.MIN_CONFIDENCE = 60
    
    def get_markets(self):
        markets = self.client.get_markets(50)
        parsed = []
        
        for m in markets:
            try:
                outcome_prices_str = m.get('outcomePrices', '[]')
                outcome_prices = json.loads(outcome_prices_str)
                
                if not outcome_prices or len(outcome_prices) < 2:
                    continue
                
                yes_price = float(outcome_prices[0])
                volume = float(m.get('volume', 0) or 0)
                
                if volume > 5000:  # Minimum liquidity
                    parsed.append({
                        'question': m.get('question', 'N/A')[:60],
                        'yes_price': yes_price,
                        'volume': volume,
                    })
            except:
                continue
        
        return parsed
    
    def run_training(self, num_iterations=1000, delay=1):
        print(f"Starting LIVE DATA TRAINING - {num_iterations} iterations")
        print(f"Balance: ${self.balance:.2f}")
        print("=" * 60)
        
        start_time = time.time()
        
        for i in range(num_iterations):
            markets = self.get_markets()
            
            if not markets:
                time.sleep(delay)
                continue
            
            # Filter good opportunities
            good = [m for m in markets if abs(m['yes_price']-0.5) >= self.MIN_EDGE]
            
            if not good:
                time.sleep(delay)
                continue
            
            market = random.choice(good)
            edge = abs(market['yes_price'] - 0.5)
            
            # Calculate confidence
            if edge >= 0.15:
                confidence = 85
            elif edge >= 0.10:
                confidence = 75
            elif edge >= self.MIN_EDGE:
                confidence = 60
            else:
                confidence = 40
            
            if confidence < self.MIN_CONFIDENCE:
                continue
            
            # Position sizing
            if confidence >= 80:
                position_pct = self.MAX_POSITION_PCT
            else:
                position_pct = self.MAX_POSITION_PCT * 0.7
            
            position_size = self.balance * position_pct
            
            # Execute trade (simulated based on confidence)
            if confidence >= 80:
                win_prob = 0.75
            elif confidence >= 60:
                win_prob = 0.65
            else:
                win_prob = 0.55
            
            won = random.random() < win_prob
            
            if won:
                reward = position_size * self.STOP_LOSS_PCT * self.TAKE_PROFIT_MULT
                net = reward * (1 - self.POLYMARKET_FEE)
                self.balance += net
                self.win_count += 1
            else:
                loss = position_size * self.STOP_LOSS_PCT
                self.balance -= loss
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            # Record trade
            self.trades.append({
                'iteration': i+1,
                'market': market['question'],
                'yes_price': market['yes_price'],
                'edge': edge,
                'confidence': confidence,
                'position': position_size,
                'won': won,
                'balance': self.balance
            })
            
            if (i+1) % 100 == 0:
                elapsed = time.time() - start_time
                win_rate = self.win_count / self.total_trades * 100 if self.total_trades > 0 else 0
                print(f"Progress: {i+1}/{num_iterations} | Trades: {self.total_trades} | Win%: {win_rate:.1f} | Balance: ${self.balance:.2f} | Time: {elapsed:.0f}s")
            
            time.sleep(delay)
            
            if self.balance < 1.0:
                print(f"BANKRUPT at iteration {i+1}!")
                break
        
        return self.trades
    
    def get_stats(self):
        if self.total_trades == 0:
            return
        
        win_rate = self.win_count / self.total_trades * 100
        
        print(f"\n{'='*60}")
        print(f"=== LIVE DATA TRAINING RESULTS ===")
        print(f"{'='*60}")
        print(f"Total Trades:      {self.total_trades}")
        print(f"Win Rate:           {win_rate:.1f}%")
        print(f"Final Balance:      ${self.balance:.2f}")
        print(f"Total Profit:       ${self.balance - self.initial_balance:.2f}")
        print(f"Return:             {(self.balance/self.initial_balance-1)*100:.1f}%")
        print(f"Peak Balance:       ${self.peak_balance:.2f}")
        print(f"{'='*60}")
        
        # Analyze by confidence
        high_conf = [t for t in self.trades if t['confidence'] >= 80]
        med_conf = [t for t in self.trades if 60 <= t['confidence'] < 80]
        
        print(f"\nBy Confidence:")
        print(f"  High (80%+): {len(high_conf)} trades | Win%: {sum(1 for t in high_conf if t['won'])/len(high_conf)*100:.1f}%" if high_conf else "  None")
        print(f"  Medium:      {len(med_conf)} trades | Win%: {sum(1 for t in med_conf if t['won'])/len(med_conf)*100:.1f}%" if med_conf else "  None")

if __name__ == "__main__":
    bot = LiveTrainingBot(initial_balance=10.0)
    bot.run_training(num_iterations=1000, delay=0.5)
    bot.get_stats()
    
    # Save all trades
    with open("data/results/live_training_1000.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['iteration', 'market', 'yes_price', 'edge', 'confidence', 'position', 'won', 'balance'])
        writer.writeheader()
        writer.writerows(bot.trades)
    
    print(f"\nSaved {len(bot.trades)} trades to data/results/live_training_1000.csv")