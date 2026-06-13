"""
Live Training Session - $20 Balance
Runs a simulation that trains on live Polymarket data.
"""

from agent_trading_system import TradingAgentSystem
import sys
import json
import os
import random
from datetime import datetime

def seed_training_data():
    """Ensure training file has at least one win and one loss to prevent sklearn errors."""
    path = 'data/training/simulated_scalper_data.json'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        print("🌱 Seeding initial training data for ML engine...")
        seeds = []
        for i in range(10):
            seeds.append({
                'price': 0.10, 'volume': 50000, 'edge': 0.85, 'confidence': 80,
                'is_crypto': i % 2 == 0, 'won': i < 5,
                'predicted_prob': 0.75, 'timestamp': datetime.now().isoformat()
            })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(seeds, f, indent=2)

def main():
    # 0. Seed data
    seed_training_data()

    # 1. Initialize with $20 as requested
    balance = 20.0
    print(f"🚀 Initializing Live Training Session with ${balance}")
    
    # 2. Setup the agent system
    system = TradingAgentSystem(starting_balance=balance)
    
    # [TWEAK] Relax risk for $20 demo mode to ensure we get data
    system.risk['min_edge'] = 0.50 
    system.risk['min_confidence'] = 50
    system.risk['max_position_size'] = 0.25 
    
    # 3. Run session with 100 trades, retraining every 10 trades
    try:
        system.lead_agent(max_trades=100, retrain_every=10)
    except KeyboardInterrupt:
        print("\nSession interrupted by user.")
        system.finish()

if __name__ == "__main__":
    main()
