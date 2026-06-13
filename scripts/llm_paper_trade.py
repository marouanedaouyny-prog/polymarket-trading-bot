#!/usr/bin/env python3
"""
LLM-guided paper trading simulator.
Uses trade_logs.json to mimic LLM recommendations.
"""

import json
import random
from datetime import datetime

# Load trade logs (pretend this is your LLM)
with open('trade_logs.json', 'r') as f:
    trade_logs = json.load(f)

# Load markets
with open('public_markets.json', 'r') as f:
    markets_data = json.load(f)

# Initialize
BALANCE = 10.0
TRADE_LOG = []


def llm_recommend_trade(market):
    """Mimic LLM recommendation using historical data."""
    # Get odds
    odds = {t['outcome']: t['price'] for t in market['tokens']}
    
    # Find similar trades in logs
    similar_trades = [
        t for t in trade_logs 
        if set(t['odds'].keys()) == set(odds.keys())
    ]
    
    if similar_trades:
        # Return the most profitable strategy
        top_trade = max(similar_trades, key=lambda x: x['profit'])
        return {
            "outcome": top_trade['outcome_chosen'],
            "strategy": top_trade['strategy'],
            "expected_profit": top_trade['profit']
        }
    else:
        # Fallback: high probability
        return {
            "outcome": max(odds, key=odds.get),
            "strategy": "high_probability",
            "expected_profit": 0.0
        }


def simulate_trade(market):
    """Simulate a trade using LLM recommendation."""
    global BALANCE, TRADE_LOG
    
    # Skip markets without a winner
    try:
        winning_token = next(t for t in market['tokens'] if t.get('winner', False))
        winning_outcome = winning_token['outcome']
    except StopIteration:
        return None
    
    # Get LLM recommendation
    recommendation = llm_recommend_trade(market)
    outcome = recommendation['outcome']
    strategy = recommendation['strategy']
    
    # Calculate bet amount (20% of balance)
    amount = round(BALANCE * 0.2, 2)
    
    # Calculate result
    odds = {t['outcome']: t['price'] for t in market['tokens']}
    if outcome == winning_outcome:
        payout = (amount / odds[outcome]) if odds[outcome] > 0 else 0
        profit = payout - amount
    else:
        profit = -amount
    
    # Update balance
    BALANCE += profit
    
    # Log trade
    trade_log = {
        "timestamp": datetime.now().isoformat(),
        "market_id": market['condition_id'],
        "question": market['question'],
        "llm_strategy": strategy,
        "outcome_chosen": outcome,
        "winning_outcome": winning_outcome,
        "amount": amount,
        "profit": profit,
        "balance": BALANCE,
        "odds": odds,
    }
    TRADE_LOG.append(trade_log)
    
    return trade_log


def save_logs():
    """Save trade logs."""
    with open('llm_trades.json', 'w') as f:
        json.dump(TRADE_LOG, f, indent=2)


def main():
    """Run LLM-guided paper trading."""
    global BALANCE
    
    print("🤖 LLM-Guided Paper Trading Simulator")
    print(f"💰 Starting Balance: ${BALANCE:.2f}")
    print("-" * 50)
    
    # Simulate 20 LLM-guided trades
    for i in range(20):
        market = random.choice(markets_data['data'])
        trade = simulate_trade(market)
        
        if trade:
            print(f"🤖 Trade {i+1}: {trade['question'][:50]}...")
            print(f"   LLM Strategy: {trade['llm_strategy']} | Bet: ${trade['amount']:.2f} on '{trade['outcome_chosen']}'")
            print(f"   Profit: ${trade['profit']:.2f} | Balance: ${trade['balance']:.2f}")
            print("-" * 50)
    
    # Save logs
    save_logs()
    print(f"🏁 Final Balance: ${BALANCE:.2f}")
    print(f"💹 Profit/Loss: ${BALANCE - 10.0:.2f}")


if __name__ == "__main__":
    main()