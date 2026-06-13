"""
Check Polymarket Account & Run Test Trade
"""

import os
import sys
import json
import requests
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parents[2]

for proxy_var in (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
):
    os.environ.pop(proxy_var, None)

load_dotenv(PROJECT_ROOT / '.env')
load_dotenv(PROJECT_ROOT / 'config' / '.env')

API_KEY = os.getenv('POLYMARKET_API_KEY', '')
API_SECRET = os.getenv('POLYMARKET_API_SECRET', '')
API_PASSPHRASE = os.getenv('POLYMARKET_API_PASSPHRASE', '')
WALLET = os.getenv('POLYMARKET_WALLET_ADDRESS', '')
RELAYER_API_KEY = os.getenv('RELAYER_API_KEY', os.getenv('POLYMARKET_API_KEY_SECONDARY', ''))
RELAYER_API_KEY_ADDRESS = os.getenv('RELAYER_API_KEY_ADDRESS', '')

print("=" * 60)
print("POLYMARKET ACCOUNT CHECK")
print("=" * 60)
print(f"API Key loaded: {bool(API_KEY)}")
print(f"API Secret loaded: {bool(API_SECRET)}")
print(f"API Passphrase loaded: {bool(API_PASSPHRASE)}")
print(f"Relayer key loaded: {bool(RELAYER_API_KEY)}")
print(f"Relayer address loaded: {bool(RELAYER_API_KEY_ADDRESS)}")
print(f"Wallet loaded: {bool(WALLET)}")
print("=" * 60)

# Check relayer authentication via API
def get_relayer_keys():
    """Verify relayer authentication and return the keys owned by the account."""
    url = "https://relayer-v2.polymarket.com/relayer/api/keys"
    
    headers = {
        'Content-Type': 'application/json',
        'RELAYER_API_KEY': RELAYER_API_KEY,
        'RELAYER_API_KEY_ADDRESS': RELAYER_API_KEY_ADDRESS,
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Relayer API Response: {response.status_code}")
            print(response.text[:200])
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Get markets to find a good test trade
def get_markets(limit=10):
    """Get active markets"""
    url = f"https://gamma-api.polymarket.com/markets?limit={limit}&active=true"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

# Check relayer
print("\n[1] Checking relayer auth...")
relayer_keys = get_relayer_keys()

if relayer_keys is not None:
    print("\n--- RELAYER KEYS ---")
    print(f"Count: {len(relayer_keys)}")
    if relayer_keys:
        first = relayer_keys[0]
        print(f"First Key Created: {first.get('createdAt', 'N/A')}")
        print(f"First Key Address: {first.get('address', 'N/A')}")
else:
    print("Relayer auth failed.")

# Get some markets
print("\n[2] Fetching active markets...")
markets = get_markets(20)

if markets:
    print(f"Found {len(markets)} markets")
    print("\n--- TOP MARKETS BY VOLUME ---")
    
    # Sort by volume
    sorted_markets = sorted(markets, key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
    
    for i, m in enumerate(sorted_markets[:5]):
        volume = float(m.get('volume', 0) or 0)
        question = m.get('question', 'N/A')[:60]
        
        try:
            prices = json.loads(m.get('outcomePrices', '[]'))
            if prices:
                yes_price = float(prices[0])
                print(f"{i+1}. {question}")
                print(f"   Volume: ${volume:,.0f} | Yes: ${yes_price:.2f}")
        except:
            pass

print("\n[3] Wallet loaded for trading:")
print(f"Wallet: {WALLET}")

print("\n" + "=" * 60)
print("Relayer auth and market data checks complete.")
print("=" * 60)
