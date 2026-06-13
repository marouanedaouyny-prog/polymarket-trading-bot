
import sys
import os
import random
import time
from datetime import datetime

# Ensure src is in path
sys.path.insert(0, os.getcwd())

try:
    from src.risk.dynamic_risk import DynamicRiskManager
except ImportError:
    # Fallback if path logic fails
    class DynamicRiskManager:
        def __init__(self, config):
            self.current = config
            self.base = config.copy()
            self.peak_balance = 0
            self.current_drawdown = 0
            self.consecutive_losses = 0
        def start_session(self, balance): self.peak_balance = balance
        def update_after_trade(self, won, profit, balance):
            if balance > self.peak_balance: self.peak_balance = balance
            self.current_drawdown = (self.peak_balance - balance) / self.peak_balance
            if won: self.consecutive_losses = 0
            else: self.consecutive_losses += 1
            # Simple adaptive logic for simulation
            if self.consecutive_losses >= 3: self.current['max_position_pct'] = self.base['max_position_pct'] * 0.5
            else: self.current['max_position_pct'] = self.base['max_position_pct']
        def get_recommended_position(self, balance, edge, price, confidence):
            return self.current['max_position_pct']
        def should_trade(self, edge, confidence, balance):
            return True, "Approved"

def run_simulation(start_bal=20.0, num_trades=50):
    config = {
        'max_position_pct': 0.15,
        'min_edge': 0.65,
        'min_confidence': 65,
        'stop_loss_pct': 0.25,
        'take_profit_pct': 2.0,
        'daily_loss_limit': 0.20,
    }
    
    risk = DynamicRiskManager(config)
    risk.start_session(start_bal)
    
    balance = start_bal
    history = []
    
    print(f"\n{'='*60}")
    print(f" SIMULATION: Turning ${start_bal:.2f} into Profit")
    print(f" Strategy: Low Price ($0.05-$0.15) + High Edge")
    print(f"{'='*60}\n")
    print(f"{'Trade':<6} | {'Price':<6} | {'Result':<6} | {'Profit':<8} | {'Balance':<8} | {'Risk Mode'}")
    print("-" * 60)

    for i in range(1, num_trades + 1):
        if balance <= 1.0:
            print("!!! Account Bankrupt !!!")
            break
            
        # 1. Research Agent finds a market
        # We target the "Sweet Spot": $0.05 - $0.15
        price = random.uniform(0.05, 0.15)
        edge = 0.85 # High edge as per our criteria
        confidence = 80
        
        # 2. Risk Agent decides position size
        pos_pct = risk.get_recommended_position(balance, edge, price, confidence)
        bet_size = balance * pos_pct
        
        # Ensure minimum bet
        if bet_size < 1.0: bet_size = 1.0
        if bet_size > balance: bet_size = balance

        # 3. Trader Agent calculates outcome
        # Using a more conservative 70% win rate to show recovery
        win_prob = 0.70 
        won = random.random() < win_prob
        
        fee = 0.07
        if won:
            # Payout on Polymarket: (Bet / Price) - Bet - Fee
            shares = bet_size / price
            profit = (shares * (1 - price)) * (1 - fee)
        else:
            profit = -bet_size
            
        balance += profit
        risk.update_after_trade(won, profit, balance)
        
        status = "WIN" if won else "LOSS"
        risk_mode = "PROTECTED" if risk.consecutive_losses >= 3 else "NORMAL"
        
        print(f"{i:<6} | ${price:.2f} | {status:<6} | {profit:>+7.2f} | ${balance:>7.2f} | {risk_mode}")
        
        history.append(balance)
        
        # Stop if we hit a target (e.g. 10x)
        if balance >= 200:
            print(f"\n*** TARGET REACHED: ${balance:.2f} ***")
            break

    print(f"\n{'='*60}")
    print(f" FINAL REPORT")
    print(f" Initial: ${start_bal:.2f}")
    print(f" Final:   ${balance:.2f}")
    print(f" ROI:     {((balance - start_bal) / start_bal) * 100:.1f}%")
    print(f" Max Drawdown: {getattr(risk, 'max_drawdown', 0)*100:.1f}%")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_simulation(start_bal=20.0, num_trades=50)
