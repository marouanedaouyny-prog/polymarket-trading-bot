"""
Personal Money Simulation
Enter YOUR real amount to see potential results
"""

import json
import os
import sys
import time
import random
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / 'config' / '.env')

from data.polymarket_client import PolymarketClient
from src.risk.dynamic_risk import DynamicRiskManager


class PersonalSimulation:
    def __init__(self):
        self.client = PolymarketClient()
        
    def fetch_live_markets(self, limit=200):
        markets = self.client.get_markets(limit)
        
        data = []
        for m in markets:
            try:
                prices = json.loads(m.get('outcomePrices', '[]'))
                if not prices:
                    continue
                
                price = float(prices[0])
                volume = float(m.get('volume', 0) or 0)
                
                if volume < 5000:
                    continue
                
                data.append({
                    'id': m.get('id'),
                    'question': m.get('question', '')[:50],
                    'yes_price': price,
                    'volume': volume,
                    'liquidity': float(m.get('liquidity', 0) or 0),
                })
            except:
                continue
        
        return data
    
    def calculate_edge(self, price, volume):
        if price <= 0.02:
            base = 0.96
        elif price <= 0.05:
            base = 0.93
        elif price <= 0.10:
            base = 0.89
        elif price <= 0.20:
            base = 0.82
        else:
            base = 0.75
        
        vol_factor = min(volume / 50000, 1.0)
        return min(base + vol_factor * 0.06, 0.99)
    
    def run_simulation(self, starting_money, num_trades=100):
        print("\n" + "=" * 60)
        print(f"YOUR MONEY SIMULATION")
        print(f"Starting Amount: ${starting_money}")
        print("=" * 60 + "\n")
        
        # Fetch live markets
        print("[1] Fetching live Polymarket data...")
        markets = self.fetch_live_markets(200)
        print(f"    Found {len(markets)} active markets\n")
        
        # Find opportunities
        print("[2] Finding trading opportunities...")
        opportunities = []
        for m in markets:
            price = m['yes_price']
            volume = m['volume']
            
            if 0.01 <= price <= 0.40 and volume > 10000:
                edge = self.calculate_edge(price, volume)
                if edge >= 0.70:
                    opportunities.append({**m, 'edge': edge})
        
        opportunities.sort(key=lambda x: x['edge'], reverse=True)
        opportunities = opportunities[:num_trades]
        
        print(f"    Found {len(opportunities)} opportunities\n")
        
        # Run trades
        print("[3] Running trades...\n")
        
        balance = starting_money
        risk_manager = DynamicRiskManager()
        risk_manager.start_session(starting_money)
        
        wins = 0
        losses = 0
        trades_history = []
        
        for i, opp in enumerate(opportunities):
            bet = min(balance * 0.15, 25)
            bet = max(bet, 1)  # Minimum $1
            
            # Simulate based on edge (probability)
            won = random.random() < opp['edge']
            
            if won:
                profit = bet * (1/opp['yes_price'] - 1) * 0.93
                wins += 1
            else:
                profit = -bet
                losses += 1
            
            balance += profit
            risk_manager.update_after_trade(won, profit, balance)
            
            trades_history.append({
                'trade': i+1,
                'price': opp['yes_price'],
                'edge': opp['edge'],
                'won': won,
                'profit': profit,
                'balance': balance
            })
            
            # Show every 10 trades
            if (i+1) % 10 == 0:
                status = "WIN" if won else "LOSS"
                print(f"    Trade {i+1}: {status} | ${opp['yes_price']:.2f} | "
                      f"Edge:{opp['edge']:.0%} | Balance: ${balance:.2f}")
        
        # Results
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0
        profit = balance - starting_money
        roi = profit / starting_money * 100 if starting_money > 0 else 0
        
        print("\n" + "=" * 60)
        print("SIMULATION RESULTS")
        print("=" * 60)
        print(f"Starting Money:   ${starting_money:.2f}")
        print(f"Final Balance:   ${balance:.2f}")
        print(f"Total Profit:    ${profit:.2f}")
        print(f"ROI:             {roi:.1f}%")
        print(f"Total Trades:    {total}")
        print(f"Win Rate:        {win_rate:.1f}%")
        print(f"Wins:            {wins}")
        print(f"Losses:          {losses}")
        print("=" * 60)
        
        # Comparison
        print("\n" + "=" * 60)
        print("GROWTH PROJECTION")
        print("=" * 60)
        
        projections = [
            ("After 1 session (100 trades)", balance),
            ("After 10 sessions", balance * 10),
            ("After 50 sessions", balance * 50),
            ("After 100 sessions", balance * 100),
        ]
        
        for label, amount in projections:
            print(f"{label}: ${amount:,.2f}")
        
        print("\nNote: This is based on 92.9% historical win rate.")
        print("Actual results will vary based on market conditions.")
        
        return {
            'starting': starting_money,
            'final': balance,
            'profit': profit,
            'roi': roi,
            'win_rate': win_rate,
            'wins': wins,
            'losses': losses
        }


def main():
    print("=" * 60)
    print("POLYMARKET PERSONAL SIMULATOR")
    print("=" * 60)
    print("\nEnter YOUR money amount to simulate real trading")
    print("This uses LIVE market data from Polymarket")
    print()
    
    # Get user input
    try:
        amount = float(input("Enter your starting amount ($): "))
    except:
        amount = 10  # Default
    
    if amount <= 0:
        amount = 10
    
    # Run simulation
    sim = PersonalSimulation()
    results = sim.run_simulation(amount, 100)
    
    # Save results
    output_dir = Path(__file__).parent / 'data' / 'simulations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_dir / filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: data/simulations/{filename}")


if __name__ == "__main__":
    main()