"""
Real Polymarket API Order Execution
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / 'config' / '.env')

API_KEY = os.getenv('POLYMARKET_API_KEY', '')
API_SECRET = os.getenv('POLYMARKET_API_SECRET', '')
WALLET = os.getenv('POLYMARKET_WALLET_ADDRESS', '')

class RealPolymarketTrader:
    """Real Polymarket order execution"""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, api_key, wallet):
        self.api_key = api_key
        self.wallet = wallet
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def get_balance(self):
        """Get USDC and ETH balance"""
        url = f"{self.BASE_URL}/balance?address={self.wallet}"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"Balance error: {e}")
        return {'usdc': 0, 'eth': 0}
    
    def get_markets(self, limit=50):
        """Get active markets"""
        url = f"{self.BASE_URL}/markets?limit={limit}&active=true"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"Markets error: {e}")
        return []
    
    def place_order(self, market_id, outcome, amount, side="buy"):
        """
        Place a real order
        """
        # First get the condition ID
        url = f"{self.BASE_URL}/markets/{market_id}"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                market = r.json()
                condition_id = market.get('conditionId')
                
                # Place order
                order_url = f"{self.BASE_URL}/order"
                order_data = {
                    "market": market_id,
                    "conditionId": condition_id,
                    "side": side,  # "buy" or "sell"
                    "outcome": outcome,  # "yes" or "no"
                    "amount": str(amount),
                    "feeTier": "0",  # Standard fee tier
                    "nonce": str(int(time.time() * 1000))
                }
                
                print(f"\nAttempting to place order:")
                print(f"  Market: {market.get('question', '')[:50]}")
                print(f"  Amount: ${amount}")
                print(f"  Outcome: {outcome}")
                
                # Try the order
                order_r = self.session.post(order_url, json=order_data, timeout=15)
                
                print(f"  Response: {order_r.status_code}")
                
                if order_r.status_code in [200, 201]:
                    result = order_r.json()
                    print(f"  Order placed! ID: {result.get('id', 'N/A')}")
                    return result
                else:
                    print(f"  Error: {order_r.text[:200]}")
                    return {'error': order_r.text[:200]}
                    
        except Exception as e:
            print(f"Order error: {e}")
            return {'error': str(e)}
    
    def buy_yes(self, market_id, amount, price):
        """Buy YES on a market"""
        return self.place_order(market_id, "yes", amount, "buy")
    
    def get_positions(self):
        """Get current positions"""
        url = f"{self.BASE_URL}/positions?address={self.wallet}"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return []


def main():
    print("=" * 60)
    print("REAL POLYMARKET TRADER")
    print("=" * 60)
    
    trader = RealPolymarketTrader(API_KEY, WALLET)
    
    # Check balance
    print("\n[1] Checking balance...")
    balance = trader.get_balance()
    print(f"USDC: {balance.get('usdc', 0)}")
    print(f"ETH: {balance.get('eth', 0)}")
    
    # Get markets
    print("\n[2] Getting markets...")
    markets = trader.get_markets(20)
    
    # Find low price, high volume market for test
    print("\n[3] Finding test market...")
    
    test_market = None
    for m in markets:
        try:
            prices = json.loads(m.get('outcomePrices', '[]'))
            if len(prices) >= 2:
                yes_price = float(prices[0])
                volume = float(m.get('volume', 0) or 0)
                
                # Look for $0.01-$0.05 with good volume
                if 0.01 <= yes_price <= 0.05 and volume > 50000:
                    test_market = m
                    print(f"Test market: {m.get('question', '')[:50]}")
                    print(f"  Price: ${yes_price}, Volume: ${volume:,.0f}")
                    break
        except:
            continue
    
    if not test_market:
        # Use first market
        test_market = markets[0]
        print(f"Using: {test_market.get('question', '')[:50]}")
    
    market_id = test_market.get('id')
    question = test_market.get('question', 'Unknown')
    
    # Place a small test order ($1)
    print(f"\n[4] Placing test order...")
    result = trader.buy_yes(market_id, 1.0, 0.05)
    
    print("\n" + "=" * 60)
    if 'error' in result:
        print(f"Order failed: {result.get('error', 'Unknown error')}")
    else:
        print(f"Order placed: {result}")
    print("=" * 60)


if __name__ == "__main__":
    main()