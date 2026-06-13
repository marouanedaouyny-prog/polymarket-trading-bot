import random
import csv
import time
import json
from datetime import datetime
from data.polymarket_client import PolymarketClient

class LiveTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        self.client = PolymarketClient()
        
        # Optimal config from tests
        self.MAX_POSITION_PCT = 0.15
        self.MIN_POSITION_PCT = 0.02
        self.STOP_LOSS_PCT = 0.05
        self.TAKE_PROFIT_MULT = 2.0
        self.POLYMARKET_FEE = 0.07
        self.MIN_EDGE = 0.05
        self.MIN_CONFIDENCE = 60
    
    def get_live_markets(self, limit=20):
        """Fetch real Polymarket data"""
        markets = self.client.get_markets(limit)
        
        parsed = []
        for m in markets:
            try:
                outcome_prices_str = m.get('outcomePrices', '[]')
                outcome_prices = json.loads(outcome_prices_str)
                
                if not outcome_prices or len(outcome_prices) < 2:
                    continue
                    
                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
                volume = float(m.get('volume', 0) or 0)
                
                parsed.append({
                    'id': m.get('id'),
                    'question': m.get('question', 'N/A')[:50],
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'volume': volume,
                    'liquidity': float(m.get('liquidity', 0) or 0),
                })
            except:
                continue
        
        return parsed
    
    def calculate_confidence(self, market):
        edge = abs(market['yes_price'] - 0.5)
        volume = market['volume']
        
        if edge >= 0.20:
            conf = 95
        elif edge >= 0.12:
            conf = 80
        elif edge >= 0.08:
            conf = 65
        elif edge >= self.MIN_EDGE:
            conf = 50
        else:
            conf = 30
        
        if volume > 50000:
            conf = min(99, conf + 5)
        
        return conf
    
    def run_live_session(self, num_iterations=20):
        print("=" * 60)
        print("LIVE TRADING BOT - Using Real Polymarket Data")
        print("=" * 60)
        
        for iteration in range(num_iterations):
            print(f"\n--- Iteration {iteration+1}/{num_iterations} ---")
            
            # Get live markets
            markets = self.get_live_markets(20)
            
            if not markets:
                print("No markets available, waiting 10s...")
                time.sleep(10)
                continue
            
            print(f"Found {len(markets)} active markets")
            
            # Filter for good opportunities
            good_markets = []
            for m in markets:
                edge = abs(m['yes_price'] - 0.5)
                vol = m['volume']
                if edge >= self.MIN_EDGE and vol > 10000:
                    good_markets.append(m)
                    print(f"  Good: {m['question'][:30]} edge={edge:.1%} vol={vol:.0f}")
            
            print(f"  Good opportunities: {len(good_markets)}")
            
            if not good_markets:
                print("No good opportunities this round")
                time.sleep(5)
                continue
            
            print(f"Good opportunities: {len(good_markets)}")
            
            # Pick random good market
            market = random.choice(good_markets)
            edge = abs(market['yes_price'] - 0.5)
            confidence = self.calculate_confidence(market)
            
            print(f"Selected: {market['question']}")
            print(f"  Yes: ${market['yes_price']:.2f} | Edge: {edge:.1%} | Conf: {confidence}%")
            
            if confidence < self.MIN_CONFIDENCE:
                print(f"  Skipping - confidence too low")
                continue
            
            # Calculate position
            if confidence >= 80:
                position_pct = self.MAX_POSITION_PCT
            elif confidence >= 60:
                position_pct = self.MAX_POSITION_PCT * 0.7
            else:
                position_pct = self.MIN_POSITION_PCT
            
            position_size = self.balance * position_pct
            
            # Simulate trade based on real prices
            win_prob = confidence / 100
            
            if random.random() < win_prob:
                # WIN - exit at take profit
                reward = position_size * self.STOP_LOSS_PCT * self.TAKE_PROFIT_MULT
                net = reward * (1 - self.POLYMARKET_FEE)
                self.balance += net
                self.win_count += 1
                status = "WIN"
            else:
                # LOSE - exit at stop loss
                loss = position_size * self.STOP_LOSS_PCT
                self.balance -= loss
                status = "LOSE"
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            print(f"  Trade: {status} | Size: ${position_size:.2f} | Bal: ${self.balance:.2f}")
            
            # Wait between trades
            time.sleep(3)
            
            if self.balance < 1.0:
                print("\nBANKRUPT!")
                break
        
        return self.trades
    
    def get_stats(self):
        print(f"\n{'='*60}")
        print("=== LIVE TRADING RESULTS ===")
        print(f"{'='*60}")
        print(f"Total Trades:    {self.total_trades}")
        print(f"Win Rate:        {self.win_count/self.total_trades*100:.1f}%" if self.total_trades > 0 else "N/A")
        print(f"Final Balance:   ${self.balance:.2f}")
        print(f"Total Profit:    ${self.balance - self.initial_balance:.2f}")
        print(f"Return:          {(self.balance/self.initial_balance-1)*100:.1f}%")
        print(f"{'='*60}")

if __name__ == "__main__":
    bot = LiveTradingBot(initial_balance=10.0)
    bot.run_live_session(10)
    bot.get_stats()
    
    # Save
    with open("data/results/live_trading.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['trade_id', 'balance', 'profit'])
        for t in bot.trades:
            writer.writerow([t.get('trade_id', 0), t.get('balance', 0), t.get('profit', 0)])
    
    print(f"\nSaved to data/results/live_trading.csv")