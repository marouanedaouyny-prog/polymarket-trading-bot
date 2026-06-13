#!/usr/bin/env python3
"""
Enhanced demo trading simulator for Polymarket.
Generates LLM training data with strategy-based trades.
"""

import json
import random
from datetime import datetime

# Load historical markets data
with open('public_markets.json', 'r') as f:
    markets_data = json.load(f)

# Initialize demo balance
BALANCE = 10.0
TRADE_LOG = []

# Strategies
STRATEGIES = {
    "high_probability": lambda odds: max(odds, key=odds.get),
    "random": lambda odds: random.choice(list(odds.keys())),
    "underdog": lambda odds: min(odds, key=odds.get),
}

def simulate_trade(market, strategy="random"):
    """Simulate a trade using a strategy."""
    global BALANCE, TRADE_LOG
    
    # Skip markets without a winner
    try:
        winning_token = next(t for t in market['tokens'] if t.get('winner', False))
        winning_outcome = winning_token['outcome']
    except StopIteration:
        return None
    
    # Get odds
    odds = {t['outcome']: t['price'] for t in market['tokens']}
    
    # Choose outcome based on strategy
    outcome = STRATEGIES.get(strategy, STRATEGIES["random"])(odds)
    
    # Calculate bet amount (20% of balance)
    amount = round(BALANCE * 0.2, 2)
    
    # Calculate result
    if outcome == winning_outcome:
        payout = (amount / odds[outcome]) if odds[outcome] > 0 else 0
        profit = payout - amount
        result = "WIN"
    else:
        profit = -amount
        result = "LOSS"
    
    # Update balance
    BALANCE += profit
    
    # Log trade
    trade_log = {
        "timestamp": datetime.now().isoformat(),
        "market_id": market['condition_id'],
        "question": market['question'],
        "strategy": strategy,
        "outcome_chosen": outcome,
        "winning_outcome": winning_outcome,
        "amount": amount,
        "profit": profit,
        "balance": BALANCE,
        "odds": odds,
        "result": result
    }
    TRADE_LOG.append(trade_log)
    
    return trade_log

def save_trade_log():
    """Save trade logs for LLM training."""
    with open('trade_logs.json', 'w') as f:
        json.dump(TRADE_LOG, f, indent=2)
    print(f"🔄 Saved {len(TRADE_LOG)} trades to 'trade_logs.json'")

def main():
    """Run the demo simulator."""
    global BALANCE
    
    print("🎯 Polymarket Demo Trading Simulator (Enhanced)")
    print(f"💰 Starting Balance: ${BALANCE:.2f}")
    print("-" * 50)
    
    # Simulate 100 trades
    for i in range(100):
        market = random.choice(markets_data['data'])
        strategy = random.choice(list(STRATEGIES.keys()))
        
        trade = simulate_trade(market, strategy)
        if trade:
            print(f"📊 Trade {i+1}: {trade['result']} | {trade['question'][:50]}...")
            print(f"   Strategy: {trade['strategy']} | Bet: ${trade['amount']:.2f} on '{trade['outcome_chosen']}'")
            print(f"   Profit: ${trade['profit']:.2f} | Balance: ${trade['balance']:.2f}")
            print("-" * 50)
    
    # Save logs
    save_trade_log()
    print(f"🏁 Final Balance: ${BALANCE:.2f}")
    print(f"📈 Profit/Loss: ${BALANCE - 10.0:.2f}")

if __name__ == "__main__":
    main()