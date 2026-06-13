"""
SMART SCALPER SIMULATOR
=======================
Runs thousands of simulations using the Smart Scalper strategy
and saves the data for ML training.
"""

import json
import os
import sys
import random
import numpy as np
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.market_predictor import MarketPredictor
from src.trading.live_trading import _extract_binary_prices, _extract_volume

# Load historical data
def load_data():
    paths = ['scripts/public_markets.json', 'public_markets.json']
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

def run_simulation(num_samples=2000):
    data = load_data()
    if not data:
        print("Data source not found.")
        return
    
    markets = data.get('data', [])
    print(f"Loaded {len(markets)} markets.")
    
    # Initialize Predictor (to use its logic)
    predictor = MarketPredictor()
    predictor.load_model() # Load existing if any
    
    simulation_results = []
    
    # Filter for closed markets with clear winners
    resolved_markets = []
    for m in markets:
        if not m.get('closed'): continue
        tokens = m.get('tokens', [])
        winner = None
        for t in tokens:
            if t.get('winner') is True:
                winner = t.get('outcome')
                break
        if winner:
            resolved_markets.append((m, winner))
    
    print(f"Found {len(resolved_markets)} resolved markets with winners.")
    
    # Target samples
    samples = random.sample(resolved_markets, min(num_samples, len(resolved_markets)))
    
    trades_executed = 0
    wins = 0
    
    for m, actual_winner in samples:
        # For historical data, prices are often 1 or 0 (resolved)
        # We simulate a mid-market price of 0.50 if the actual price is extreme
        # or use the provided outcomePrices if available.
        raw_prices = _extract_binary_prices(m)
        volume = _extract_volume(m)
        if volume < 500: volume = random.randint(5000, 50000) # Ensure some volume for simulation
        
        question = m.get('question', 'N/A')
        is_crypto = any(kw in question.lower() for kw in ['btc', 'eth', 'sol', 'crypto', 'bitcoin', 'ethereum'])

        # Strategy logic
        for side in ["yes", "no"]:
            # SIMULATE a trading price (not 1.0 or 0.0)
            is_actual_winner = (side.lower() == actual_winner.lower())
            
            if is_actual_winner:
                price = random.uniform(0.60, 0.95) # Buy high probability
            else:
                price = random.uniform(0.05, 0.40) # Buy low probability
            
            # 1. AI Edge
            ai_edge = 0.50
            if predictor.model:
                try: ai_edge = predictor.predict_win_probability(price, volume, 0.1, 60, is_crypto)
                except: pass
            else:
                ai_edge = 0.85 if price < 0.20 else 0.75 if price < 0.50 else 0.60
            
            # 2. Mock MiroFish Signal (WISDOM)
            # High quality signal for simulation
            if random.random() < 0.85: 
                swarm_prob = random.uniform(0.70, 0.99) if is_actual_winner else random.uniform(0.01, 0.30)
            else:
                swarm_prob = random.uniform(0.01, 0.30) if is_actual_winner else random.uniform(0.70, 0.99)
            
            swarm_conf = random.randint(50, 95)

            # Consensus logic
            final_prob = (ai_edge * 0.4) + (swarm_prob * 0.6)
            
            if final_prob >= 0.55: # Scalper threshold
                won = is_actual_winner
                
                # Record result for training
                simulation_results.append({
                    'price': price,
                    'volume': volume,
                    'edge': ai_edge,
                    'confidence': swarm_conf,
                    'is_crypto': is_crypto,
                    'won': won,
                    'question': question,
                    'side': side
                })
                
                trades_executed += 1
                if won: wins += 1

    print(f"Simulation Complete: {trades_executed} trades executed.")
    print(f"Simulated Win Rate: {wins/trades_executed:.1%}" if trades_executed > 0 else "No trades.")
    
    # Save for training
    output_file = 'data/training/simulated_scalper_data.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(simulation_results, f, indent=2)
    
    print(f"Saved {len(simulation_results)} samples to {output_file}")
    return simulation_results

if __name__ == "__main__":
    # Larger scale simulation
    results = run_simulation(10000)
    
    if results:
        # Train the model on the new data!
        print("\n--- Training Model on Simulated Data ---")
        predictor = MarketPredictor()
        predictor.train(results)
        print("Success. The AI is now smarter based on the Smart Scalper simulations.")
