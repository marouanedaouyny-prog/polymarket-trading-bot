import random
import csv
from datetime import datetime

class ConfidenceTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        
        # Risk parameters
        self.MAX_POSITION_PCT = 0.10  # 10% max of balance
        self.MIN_POSITION_PCT = 0.01  # 1% minimum
        self.STOP_LOSS_PCT = 0.03  # 3% stop loss
        self.TAKE_PROFIT_MULT = 2.5  # 2.5x risk = take profit
        
    def calculate_confidence(self, market):
        """Calculate trade confidence 0-100% based on edge"""
        edge = abs(market['yes_price'] - 0.5)
        
        # Higher edge = higher confidence
        if edge >= 0.15:
            confidence = 95
        elif edge >= 0.10:
            confidence = 80
        elif edge >= 0.05:
            confidence = 60
        else:
            confidence = 40
        
        # Adjust by liquidity (simulated)
        liquidity_bonus = min(10, market['volume'] / 20000)
        confidence = min(99, confidence + liquidity_bonus)
        
        return confidence
    
    def calculate_position_size(self, confidence):
        """Dynamic position sizing based on confidence"""
        # Kelly fraction adjusted by confidence
        base_pct = self.MIN_POSITION_PCT + (self.MAX_POSITION_PCT - self.MIN_POSITION_PCT) * (confidence / 100)
        
        # Scale position: low confidence = small bet, high confidence = big bet
        if confidence >= 80:
            position_pct = base_pct * 1.5  # Boost for high confidence
        elif confidence >= 60:
            position_pct = base_pct
        else:
            position_pct = base_pct * 0.5  # Reduce for low confidence
        
        position_pct = min(position_pct, self.MAX_POSITION_PCT)
        
        return self.balance * position_pct
    
    def calculate_win_prob(self, confidence):
        """Win probability based on confidence"""
        base = 0.50
        # Higher confidence = higher win probability
        return min(0.92, base + (confidence / 100) * 0.4)
    
    def run_simulation(self, num_trades=100):
        print(f"Starting {num_trades} trades with confidence-based sizing...")
        print(f"Initial: ${self.balance:.2f}")
        print("-" * 50)
        
        for i in range(num_trades):
            # Generate random market (simulating real data)
            market = {
                'yes_price': random.uniform(0.25, 0.75),
                'volume': random.uniform(5000, 150000),
                'question': f"Will event {i+1} happen?"
            }
            market['no_price'] = 1.0 - market['yes_price']
            
            edge = abs(market['yes_price'] - 0.5)
            
            # Skip if edge too small
            if edge < 0.03:
                print(f"Trade {i+1}: SKIP (edge={edge:.2%} too low)")
                continue
            
            confidence = self.calculate_confidence(market)
            position_size = self.calculate_position_size(confidence)
            win_prob = self.calculate_win_prob(confidence)
            
            # Execute trade
            risk = position_size * self.STOP_LOSS_PCT
            reward = risk * self.TAKE_PROFIT_MULT
            
            # Simulate outcome
            if random.random() < win_prob:
                # WIN
                profit = reward
                self.balance += profit
                self.win_count += 1
                status = "WIN"
            else:
                # LOSE
                loss = risk
                self.balance -= loss
                status = "LOSE"
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            # Track trade
            self.trades.append({
                'trade_id': i+1,
                'edge': edge,
                'confidence': confidence,
                'position_size': position_size,
                'profit_loss': profit if status == "WIN" else -loss,
                'balance': self.balance,
                'win': status == "WIN"
            })
            
            icon = "WIN" if status == "WIN" else "LOSE"
            print(f"Trade {i+1}: {icon} Edge:{edge:.1%} Conf:{confidence}% Size:${position_size:.2f} | {status} ${abs(profit if status=='WIN' else -loss):.4f} | Bal: ${self.balance:.2f}")
            
            # Check bankruptcy
            if self.balance < 1.0:
                print(f"\nBANKRUPT at trade {i+1}!")
                break
        
        return self.trades
    
    def get_stats(self):
        if self.total_trades == 0:
            print("No trades executed")
            return
            
        win_rate = (self.win_count / self.total_trades * 100)
        total_profit = self.balance - self.initial_balance
        return_pct = ((self.balance / self.initial_balance) - 1) * 100
        max_drawdown = ((self.peak_balance - self.balance) / self.peak_balance * 100)
        
        print(f"\n{'='*50}")
        print(f"=== CONFIDENCE TRADING RESULTS ===")
        print(f"{'='*50}")
        print(f"Total Trades:      {self.total_trades}")
        print(f"Win Rate:          {win_rate:.1f}%")
        print(f"Final Balance:     ${self.balance:.2f}")
        print(f"Total Profit:      ${total_profit:.2f}")
        print(f"Return:            {return_pct:.1f}%")
        print(f"Peak Balance:      ${self.peak_balance:.2f}")
        print(f"Max Drawdown:      {max_drawdown:.1f}%")
        print(f"{'='*50}")
        
        # Analyze by confidence level
        high_conf = [t for t in self.trades if t['confidence'] >= 80]
        med_conf = [t for t in self.trades if 60 <= t['confidence'] < 80]
        low_conf = [t for t in self.trades if t['confidence'] < 60]
        
        print("\nBy Confidence Level:")
        print(f"  High (80%+):  {len(high_conf)} trades | Avg: ${sum(t['profit_loss'] for t in high_conf)/len(high_conf):.4f}" if high_conf else "  High (80%+):  0 trades")
        print(f"  Medium (60-79%): {len(med_conf)} trades | Avg: ${sum(t['profit_loss'] for t in med_conf)/len(med_conf):.4f}" if med_conf else "  Medium (60-79%): 0 trades")
        print(f"  Low (<60%):   {len(low_conf)} trades | Avg: ${sum(t['profit_loss'] for t in low_conf)/len(low_conf):.4f}" if low_conf else "  Low (<60%):   0 trades")
        
        return {
            'total_trades': self.total_trades,
            'win_rate': win_rate,
            'final_balance': self.balance,
            'profit': total_profit,
            'return_pct': return_pct,
            'max_drawdown': max_drawdown
        }

if __name__ == "__main__":
    bot = ConfidenceTradingBot(initial_balance=10.0)
    bot.run_simulation(100)
    stats = bot.get_stats()
    
    # Save to CSV
    with open("data/results/confidence_paper_trades.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=['trade_id', 'edge', 'confidence', 'position_size', 'profit_loss', 'balance', 'win'])
        writer.writeheader()
        writer.writerows(bot.trades)
    
    print(f"\nResults saved to: data/results/confidence_paper_trades.csv")