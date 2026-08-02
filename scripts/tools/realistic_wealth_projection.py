"""
REALISTIC WEALTH PROJECTION SIMULATOR
=====================================
Uses Monte Carlo simulation to project earnings from $20 
accounting for slippage, fees, and intelligence gaps.
"""

import numpy as np
import random

def run_simulation(name, win_rate, starting_balance=20, trades=100, iterations=1000):
    results = []
    
    for _ in range(iterations):
        balance = starting_balance
        for t in range(trades):
            if balance < 1: # Bust
                balance = 0
                break
                
            # 1. Position Sizing
            bet = max(2, balance * 0.15)
            if bet > balance: bet = balance
            
            # 2. Market Friction (Slippage Model)
            # Higher volume trades have higher slippage
            # volume_impact = trade_size / market_depth (proxy)
            market_depth = 50000 # Assume $50k depth per market
            slippage_impact = (bet / market_depth) * 0.05 # 5% impact ratio
            slippage_pct = 0.005 + slippage_impact
            
            # 3. Fees (Polymarket + Gas)
            fee_pct = 0.02 # 2% 
            
            # 4. Outcome
            if random.random() < win_rate:
                # WIN
                profit = (bet * 0.8) * (1 - slippage_pct) * (1 - fee_pct)
                balance += profit
            else:
                # LOSS
                balance -= bet
                
        results.append(balance)
    
    results = np.array(results)
    return {
        "name": name,
        "mean": np.mean(results),
        "median": np.median(results),
        "min": np.min(results),
        "max": np.max(results),
        "success_rate": (results > starting_balance).mean(),
        "bust_rate": (results <= 0).mean()
    }

def main():
    print("="*60)
    print("      REALISTIC WEALTH PROJECTION ($20 START)")
    print("="*60)
    
    # Scenario 1: Current Project (MiroFish Offline, Static Intelligence)
    # Win rate is likely around 55-58% in real conditions
    curr = run_simulation("Current (Intelligence Offline)", 0.57)
    
    # Scenario 2: Optimized Project (MiroFish Online, ML Fully Trained)
    # Win rate targeted at 72-75%
    opt = run_simulation("Optimized (Intelligence Online)", 0.73)
    
    for res in [curr, opt]:
        print(f"\nPROJECTION: {res['name']}")
        print(f"--- Outcome Probability ---")
        print(f"Bust Rate (Lost Everything): {res['bust_rate']:.1%}")
        print(f"Profit Probability:         {res['success_rate']:.1%}")
        print(f"--- Expected Returns ---")
        print(f"Average Final Balance:       ${res['mean']:,.2f}")
        print(f"Median Final Balance:        ${res['median']:,.2f}")
        print(f"Lucky Day (Top 1%):         ${res['max']:,.2f}")
    
    print("\n" + "="*60)
    print("      ENGINEER'S VERDICT")
    print("="*60)
    if curr['bust_rate'] > 0.3:
        print("CRITICAL: Running the project in its current state has a high risk of bust.")
        print("The 'Static Intelligence' is not strong enough to overcome fees and slippage.")
    
    print("\nACTION PLAN:")
    print("1. FIX MIROFISH: Get the swarm intelligence engine online (5001 port).")
    print("2. TRAIN ON REAL DATA: Let the $20 bot run for 48 hours to refine the model.")
    print("3. DON'T DEPOSIT YET: Wait until 'Average Final Balance' > $50 in this sim.")

if __name__ == "__main__":
    main()
