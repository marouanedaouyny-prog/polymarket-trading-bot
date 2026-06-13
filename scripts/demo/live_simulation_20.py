
import sys
import os
import json
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.getcwd())

from src.data.polymarket_client import PolymarketClient
from src.risk.dynamic_risk import DynamicRiskManager
from src.ml.market_predictor import MarketPredictor

def run_live_simulation(start_bal=20.0):
    print(f"\n{'='*70}")
    print(f" LIVE MARKET SIMULATION - STARTING BALANCE: ${start_bal:.2f}")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # 1. Initialize Components
    client = PolymarketClient()
    
    config = {
        'max_position_pct': 0.15,
        'min_edge': 0.60,
        'min_confidence': 60,
        'stop_loss_pct': 0.25,
        'take_profit_pct': 2.0,
        'daily_loss_limit': 0.20,
    }
    risk = DynamicRiskManager(config)
    risk.start_session(start_bal)
    
    predictor = MarketPredictor()
    predictor.load_model()
    
    # 2. Fetch Real Data
    print("[1/3] Fetching live markets from Polymarket...")
    markets = client.get_markets(limit=100)
    if not markets:
        print("Error: Could not fetch markets.")
        return

    # 3. Analyze and Filter
    print(f"[2/3] Analyzing {len(markets)} live markets using ML Model...")
    
    found_opportunities = []
    
    for m in markets:
        try:
            # Parse Prices
            prices_str = m.get('outcomePrices', '[]')
            if isinstance(prices_str, str):
                prices = json.loads(prices_str)
            else:
                prices = prices_str
                
            if not prices or len(prices) < 2:
                continue
                
            price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            question = m.get('question', 'Unknown')
            market_id = m.get('id', 'N/A')
            
            # Project Strategy Filters
            # 1. Price Range ($0.01 - $0.35)
            if price < 0.01 or price > 0.35:
                continue
            
            # 2. Volume Check (> $5,000 for this simulation)
            if volume < 5000:
                continue
                
            # 3. Calculate Edge & Win Prob via Model
            # Note: In real life, we don't know 'is_crypto' easily without more parsing, defaulting to False
            is_crypto = 'bitcoin' in question.lower() or 'eth' in question.lower() or 'crypto' in question.lower()
            
            # For simulation, we'll use the price-tier edge as a baseline
            if price <= 0.02: edge = 0.96
            elif price <= 0.05: edge = 0.93
            elif price <= 0.10: edge = 0.89
            elif price <= 0.20: edge = 0.82
            else: edge = 0.75
            
            # Calculate recommendation
            bet_pct = risk.get_recommended_position(start_bal, edge, price, 80)
            bet_amount = start_bal * bet_pct
            
            # Expected Value
            win_prob = edge # Using our model's historical win rate for that tier
            expected_payout = (bet_amount / price) * win_prob * (1 - 0.07)
            profit_if_win = (bet_amount / price) * (1 - price) * (1 - 0.07)
            
            found_opportunities.append({
                'question': question,
                'price': price,
                'volume': volume,
                'edge': edge,
                'bet': bet_amount,
                'pot_profit': profit_if_win,
                'win_prob': win_prob
            })
        except Exception as e:
            continue

    # 4. Show Real Opportunities
    print(f"[3/3] Found {len(found_opportunities)} trades matching the strategy.\n")
    
    if not found_opportunities:
        print("No trades found matching the strict criteria right now.")
        return

    # Sort by Edge
    found_opportunities.sort(key=lambda x: x['edge'], reverse=True)
    
    print(f"{'QUESTION':<45} | {'PRICE':<6} | {'BET':<6} | {'POT. PROFIT'}")
    print("-" * 80)
    
    total_sim_profit = 0
    
    for opp in found_opportunities[:5]: # Top 5
        print(f"{opp['question'][:43]:<45} | ${opp['price']:.2f} | ${opp['bet']:.2f} | +${opp['pot_profit']:.2f}")
        total_sim_profit += (opp['pot_profit'] * opp['win_prob']) - (opp['bet'] * (1-opp['win_prob']))

    print(f"\n{'='*70}")
    print(f" SUMMARY FOR $20 BALANCE")
    print(f" Number of active targets: {len(found_opportunities)}")
    print(f" Avg. Expected Value per trade: +${total_sim_profit/5:.2f}")
    print(f" Projected balance after 5 wins: ${start_bal + sum(o['pot_profit'] for o in found_opportunities[:5]):.2f}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_live_simulation(20.0)
