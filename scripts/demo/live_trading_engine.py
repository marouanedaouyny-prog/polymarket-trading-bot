"""
Live Trading Integration with Polymarket SDK
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / 'config' / '.env')

# Try SDK import
try:
    from Polymarket import PolymarketDataFetcher
    SDK_AVAILABLE = True
except:
    SDK_AVAILABLE = False
    print("Note: Polymarket SDK (PolymarketDataFetcher) available for data only")

# Import our existing modules
from data.polymarket_client import PolymarketClient
from src.risk.dynamic_risk import DynamicRiskManager
from src.data.sqlite_db import get_db


class LiveTradingEngine:
    """Live trading engine with real Polymarket execution"""
    
    def __init__(self, api_key, api_secret, wallet, starting_balance=100, mode='paper'):
        self.api_key = api_key
        self.api_secret = api_secret
        self.wallet = wallet
        self.balance = starting_balance
        self.mode = mode
        self.initial_balance = starting_balance
        
        # Market data client
        self.client = PolymarketClient(api_key=api_key)
        
        # Risk manager
        self.risk_manager = DynamicRiskManager()
        self.risk_manager.start_session(starting_balance)
        
        # Database
        self.db = get_db()
        self.session_id = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Trade tracking
        self.trades = []
        self.stats = {'wins': 0, 'losses': 0}
        self.fee = 0.07
        
        print(f"Live Trading Engine initialized")
        print(f"  Mode: {mode.upper()}")
        print(f"  Starting Balance: ${starting_balance}")
        print(f"  API Key: {api_key[:15]}...")
    
    def get_market_info(self, limit=20):
        """Get active markets with details"""
        markets = self.client.get_markets(limit)
        
        result = []
        for m in markets:
            try:
                prices = json.loads(m.get('outcomePrices', '[]'))
                if prices:
                    result.append({
                        'id': m.get('id'),
                        'question': m.get('question', '')[:80],
                        'yes_price': float(prices[0]),
                        'no_price': float(prices[1]) if len(prices) > 1 else 0,
                        'volume': float(m.get('volume', 0) or 0),
                        'liquidity': float(m.get('liquidity', 0) or 0),
                    })
            except:
                continue
        
        return result
    
    def calculate_edge(self, price, volume):
        """Calculate trading edge"""
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
    
    def execute_live_trade(self, market, price, win_prob):
        """Execute a trade (simulated for now, SDK ready for real)"""
        
        # Position size
        bet = min(self.balance * 0.15, 25)
        bet = max(bet, 5)
        
        if self.mode == 'paper':
            # Simulate outcome
            import random
            won = random.random() < win_prob
            
            if won:
                profit = bet * (1 / price - 1) * (1 - self.fee)
            else:
                profit = -bet
            
            self.balance += profit
            
            if won:
                self.stats['wins'] += 1
            else:
                self.stats['losses'] += 1
            
            return {
                'market': market['question'],
                'price': price,
                'bet': bet,
                'won': won,
                'profit': profit,
                'mode': 'paper'
            }
        
        else:
            # Live mode - would call SDK
            print(f"[LIVE] Would place order: {market['question'][:50]}")
            print(f"  Amount: ${bet}, Price: ${price}")
            print(f"  Note: SDK order execution requires additional auth setup")
            
            return {
                'market': market['question'],
                'price': price,
                'bet': bet,
                'won': None,
                'profit': 0,
                'mode': 'live_pending'
            }
    
    def run_session(self, num_trades=10):
        """Run a trading session"""
        print(f"\n{'='*60}")
        print(f"LIVE TRADING SESSION ({self.mode.upper()})")
        print(f"{'='*60}\n")
        
        # Get markets
        markets = self.get_market_info(50)
        
        # Filter for good opportunities
        opportunities = []
        for m in markets:
            price = m['yes_price']
            volume = m['volume']
            
            if 0.01 <= price <= 0.35 and volume > 15000:
                edge = self.calculate_edge(price, volume)
                if edge >= 0.65:
                    opportunities.append({
                        **m,
                        'edge': edge,
                        'win_prob': edge  # Simplified
                    })
        
        # Sort by edge
        opportunities.sort(key=lambda x: x['edge'], reverse=True)
        
        print(f"Found {len(opportunities)} opportunities\n")
        
        # Execute trades
        for i in range(min(num_trades, len(opportunities))):
            opp = opportunities[i]
            
            result = self.execute_live_trade(opp, opp['yes_price'], opp['win_prob'])
            
            status = "WIN" if result['won'] else "LOSS" if result['won'] is not None else "PENDING"
            
            print(f"Trade {i+1}: {status} | ${opp['yes_price']:.2f} | "
                  f"Edge:{opp['edge']:.0%} | Bal:${self.balance:.2f}")
            
            self.trades.append(result)
            
            # Update risk manager
            if result['won'] is not None:
                self.risk_manager.update_after_trade(
                    result['won'], 
                    result['profit'], 
                    self.balance
                )
            
            time.sleep(0.5)
        
        return self.finish()
    
    def finish(self):
        """Session summary"""
        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0
        profit = self.balance - self.initial_balance
        
        print(f"\n{'='*60}")
        print("SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"Mode: {self.mode.upper()}")
        print(f"Trades: {total} | Wins: {self.stats['wins']} | Losses: {self.stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f}")
        print(f"{'='*60}")
        
        return {'win_rate': win_rate, 'profit': profit}


def main():
    # Load credentials
    api_key = os.getenv('POLYMARKET_API_KEY', '')
    api_secret = os.getenv('POLYMARKET_API_SECRET', '')
    wallet = os.getenv('POLYMARKET_WALLET_ADDRESS', '')
    
    print("=" * 60)
    print("POLYMARKET LIVE TRADING")
    print("=" * 60)
    print(f"API Key: {api_key[:15]}...")
    print(f"Wallet: {wallet[:20]}...")
    print(f"SDK Available: {SDK_AVAILABLE}")
    print("=" * 60)
    
    # Create engine
    engine = LiveTradingEngine(
        api_key=api_key,
        api_secret=api_secret,
        wallet=wallet,
        starting_balance=100,
        mode='paper'  # Change to 'live' when ready
    )
    
    # Run session
    engine.run_session(num_trades=10)


if __name__ == "__main__":
    main()