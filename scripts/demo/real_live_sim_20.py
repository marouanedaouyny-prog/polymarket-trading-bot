
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.getcwd())

from src.data.polymarket_client import PolymarketClient
from src.risk.dynamic_risk import DynamicRiskManager

def run_real_time_simulation(start_bal=20.0):
    print(f"\n{'='*90}")
    print(f" REAL-TIME MARKET SCAN: PROJECTING $20.00 GROWTH")
    print(f" Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*90}\n")

    client = PolymarketClient()
    risk = DynamicRiskManager({'max_position_pct': 0.15}) # 15% risk limit
    
    print("[Step 1] Fetching live prediction markets...")
    raw_markets = client.get_markets(limit=100)
    
    opportunities = []
    
    for m in raw_markets:
        try:
            # Parse Prices
            prices = m.get('outcomePrices')
            if isinstance(prices, str):
                prices = json.loads(prices)
            
            if not prices or len(prices) < 2: continue
            
            price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            question = m.get('question', 'Unknown')
            
            # Use endDate or createdDate as a proxy for time
            end_date_str = m.get('endDate') or m.get('closed') or "2024-12-31T00:00:00Z"
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except:
                end_dt = datetime.now()
            
            days_to_resolution = (end_dt.replace(tzinfo=None) - datetime.now()).days
            
            # Apply Project Filters:
            # 1. Price Sweet Spot: $0.05 - $0.25 (High growth)
            # 2. Volume Check: > $10,000 (Liquidity)
            if 0.05 <= price <= 0.25 and volume > 10000 and days_to_resolution > 0:
                
                # Calculate Win Probability based on project's Price Tier Model
                if price <= 0.10: win_prob = 0.89
                else: win_prob = 0.82
                
                bet_amount = start_bal * 0.15 # $3.00
                potential_payout = (bet_amount / price) * (1 - 0.07) # After 7% fee
                potential_profit = potential_payout - bet_amount
                
                opportunities.append({
                    'question': question,
                    'price': price,
                    'bet': bet_amount,
                    'profit': potential_profit,
                    'days': days_to_resolution,
                    'prob': win_prob
                })
        except:
            continue

    print(f"[Step 2] Found {len(opportunities)} high-edge opportunities available RIGHT NOW.\n")
    
    if not opportunities:
        print("No live markets currently meet the strict $20 'Sweet Spot' criteria.")
        return

    # Sort by profit potential
    opportunities.sort(key=lambda x: x['profit'], reverse=True)

    print(f"{'MARKET QUESTION':<50} | {'PRICE':<6} | {'BET':<5} | {'POT. PROFIT':<12} | {'TIME'}")
    print("-" * 105)
    
    current_balance = start_bal
    total_time_days = 0
    
    # We simulate a sequence of 4 trades (re-investing profits)
    for i, opp in enumerate(opportunities[:4]):
        # Calculate bet size based on GROWING balance (15%)
        bet = current_balance * 0.15
        if bet < 1.0: bet = 1.0 # Min bet
        
        payout_multiplier = (1 / opp['price']) * 0.93 # 7% fee adjustment
        trade_profit = (bet * payout_multiplier) - bet
        
        print(f"{opp['question'][:48]:<50} | ${opp['price']:.2f} | ${bet:>4.2f} | +${trade_profit:>9.2f} | {opp['days']} Days")
        
        # Hypothetical sequence assuming wins
        current_balance += trade_profit
        total_time_days = max(total_time_days, opp['days'])

    print(f"\n{'='*90}")
    print(f" HYPOTHETICAL GROWTH PATH (Based on Live Markets Found)")
    print(f" Start Balance: ${start_bal:.2f}")
    print(f" End Balance:   ${current_balance:.2f}")
    print(f" Total Trades:  4 Sequence Wins")
    print(f" Est. Time:     {total_time_days} Days (based on furthest market resolution)")
    print(f" ROI:           {((current_balance - start_bal)/start_bal)*100:.1f}%")
    print(f"{'='*90}")
    print("\nNote: This simulation uses real prices from Polymarket taken in the last 10 seconds.")

if __name__ == "__main__":
    run_real_time_simulation(20.0)
