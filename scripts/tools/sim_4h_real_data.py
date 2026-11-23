"""
4-HOUR REAL-MARKET ACCELERATED SIMULATOR
========================================
Simulates a real-time 4-hour session with $20 starting balance.
Uses actual resolved Polymarket data for maximum realism.
"""

import json
import os
import sys
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path (scripts/tools/ -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.market_predictor import MarketPredictor

def load_real_data():
    resolved_file = 'data/training/resolved_markets.json'
    if not os.path.isfile(resolved_file):
        print("Error: No real data found. Run fetch_resolved.py first.")
        return []
    with open(resolved_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_4h_sim(start_balance=50.0):
    print("\n" + "="*60)
    print(f"STARTING 4-HOUR REAL-MARKET SIMULATION")
    print(f"Starting Capital: ${start_balance:.2f}")
    print(f"Strategy: Smart Scalper (High-Frequency / Conservative)")
    print("="*60 + "\n")

    markets = load_real_data()
    if not markets: return
    
    predictor = MarketPredictor()
    predictor.load_model()
    
    balance = start_balance
    trades = []
    
    # Simulate scanning until exactly TARGET_TRADES trades are recorded
    TARGET_TRADES = 100
    current_sim_time = datetime.now()

    while len(trades) < TARGET_TRADES:
        current_sim_time += timedelta(minutes=2)
        timestamp = current_sim_time.strftime("%H:%M")

        # Pick a random market from real resolved data
        m = random.choice(markets)
        actual_winner = m.get('outcome')
        question = m.get('question')
        
        # ---- Model-driven side selection (MECHANICS TEST ONLY) ----
        # NOTE: yes/no prices in resolved_markets.json are FINAL SETTLEMENT
        # prices. Feeding them to the model + grading against `outcome` is
        # hindsight (the answer is baked into the price). So the loop below
        # exercises sizing/fee/balance mechanics, NOT predictive edge.
        yes_price = float(m.get('yes_price', 0.5) or 0.5)
        no_price = float(m.get('no_price', 0.5) or 0.5)
        volume = m.get('volume', 0) or 0
        is_crypto = str(m.get('tag', '')).lower() in ('crypto', 'cryptocurrency')

        # Normalize entry price into a stable band for the model
        entry_price = min(max(yes_price, 0.05), 0.95)
        spread = 0.04
        days_to_close = 7.0

        pred = predictor.predict_win_probability(
            entry_price, volume,
            is_crypto=is_crypto, days_to_close=days_to_close, spread=spread,
        )
        chosen_side = "yes" if pred >= 0.5 else "no"
        won = (chosen_side == actual_winner)

        # Skip low-conviction trades — trade fewer, but better
        CONF_MIN = 0.10
        if abs(pred - 0.5) < CONF_MIN:
            continue

        # Payout at the chosen side's real price, clamped to sane scalp band
        price = yes_price if chosen_side == "yes" else no_price
        price = min(max(price, 0.20), 0.85)

        # Scalper Position Sizing: 4% of balance
        bet_amount = round(balance * 0.04, 2)
        if bet_amount < 1.0: bet_amount = 1.0 # Minimum bet

        # Calculate Payout
        if won:
            # 1 / price payout minus 7% fee
            profit = bet_amount * (1 / price - 1) * 0.93
        else:
            profit = -bet_amount
            
        balance += profit
        
        trade_log = {
            'time': timestamp,
            'q': question[:45],
            'side': chosen_side.upper(),
            'bet': bet_amount,
            'price': price,
            'result': "WIN" if won else "LOSS",
            'profit': profit,
            'balance': balance
        }
        trades.append(trade_log)
        
        print(f"[{timestamp}] {trade_log['result']} | {trade_log['q']}...")
        print(f"        Side: {trade_log['side']} at ${price:.2f} | Bet: ${bet_amount:.2f} | Profit: ${profit:+.2f}")
        
    # --- FINAL REPORT ---
    net_pl = balance - start_balance
    win_count = sum(1 for t in trades if t['result'] == "WIN")
    win_rate = (win_count / len(trades)) * 100 if trades else 0
    
    print("\n" + "="*60)
    print("4-HOUR SIMULATION COMPLETE")
    print("="*60)
    print(f"Initial Balance: ${start_balance:.2f}")
    print(f"Final Balance:   ${balance:.2f}")
    print(f"Net Profit/Loss: ${net_pl:+.2f}")
    print(f"Total Trades:    {len(trades)}")
    print(f"Win Rate:        {win_rate:.1f}%")
    print("="*60)
    
    # Save log
    with open('data/test_runs/sim_4h_results.json', 'w') as f:
        json.dump(trades, f, indent=2)

if __name__ == "__main__":
    run_4h_sim(50.0)
