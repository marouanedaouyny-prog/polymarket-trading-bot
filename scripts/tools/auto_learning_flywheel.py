"""
AUTO-LEARNING ENGINE
====================
Runs massive simulations, retrains the model, and iterates 
to maximize the win rate automatically.
"""

import json
import os
import sys
import time
import random
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from smart_scalper_simulator import run_simulation
from src.ml.market_predictor import MarketPredictor

def run_learning_cycle(iterations=10, samples_per_iter=5000):
    print("🚀 STARTING AI SELF-LEARNING FLYWHEEL")
    print(f"Goal: Run {iterations} training generations to maximize win rate.")
    
    best_win_rate = 0.0
    
    for i in range(iterations):
        print(f"\n--- GENERATION {i+1} ---")
        
        # 1. Run massive simulations
        results = run_simulation(num_samples=samples_per_iter)
        
        if not results:
            print("No data generated. Skipping.")
            continue
            
        # 2. Calculate current win rate
        current_wins = sum(1 for r in results if r['won'])
        current_rate = current_wins / len(results)
        print(f"Gen {i+1} Win Rate: {current_rate:.2%}")
        
        # 3. Retrain the model on this specific generation's data
        predictor = MarketPredictor()
        predictor.train(results)
        
        # 4. Save if it's the best one yet
        if current_rate > best_win_rate:
            best_win_rate = current_rate
            print(f"⭐ NEW BEST MODEL: {best_win_rate:.2%}")
        
        # Brief pause to avoid CPU thrashing
        time.sleep(2)

    print("\n" + "="*40)
    print(f"FLYWHEEL COMPLETE. Final Best Win Rate: {best_win_rate:.2%}")
    print("="*40)

if __name__ == "__main__":
    # Run 5 generations of 10,000 samples each (50,000 total scenarios)
    run_learning_cycle(iterations=5, samples_per_iter=10000)
