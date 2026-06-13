"""
Get REAL resolved markets from Polymarket API
Uses actual outcomes for training
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.polymarket_client import PolymarketClient


def fetch_resolved_markets(target_count=2000):
    """Recursively fetch a massive number of resolved markets from the API."""
    print("=" * 60)
    print(f"🚀 INITIATING MASSIVE REAL-DATA ACQUISITION (Target: {target_count})")
    print("=" * 60)
    
    client = PolymarketClient()
    resolved_data = []
    
    # We use multiple limit calls to bypass the 1000 limit if possible
    # and filter for various tags to get a diverse dataset
    for tag in ["Crypto", "Bitcoin", "Ethereum", "Solana", "Business"]:
        print(f"Fetching {tag} markets...")
        markets = client.get_markets(limit=1000, params={"active": "false", "closed": "true", "tag": tag})
        
        for m in markets:
            try:
                prices = json.loads(m.get('outcomePrices', '[]'))
                if not prices or len(prices) < 2: continue
                
                yes_p = float(prices[0])
                no_p = float(prices[1])
                
                if yes_p < 0.90 and no_p < 0.90: continue 

                resolved_data.append({
                    'id': m.get('id'),
                    'question': m.get('question', ''),
                    'yes_price': yes_p,
                    'no_price': no_p,
                    'volume': float(m.get('volume', 0) or 0),
                    'closed': True,
                    'tag': tag,
                    'outcome': 'yes' if yes_p > 0.5 else 'no'
                })
            except: continue
        
        if len(resolved_data) >= target_count: break
    
    # Final deduplication
    unique_data = {m['id']: m for m in resolved_data}.values()
    resolved_data = list(unique_data)
    
    print(f"\n✅ DATA ACQUISITION COMPLETE: {len(resolved_data)} REAL resolved markets found.")
    
    # Show some examples
    print("\nSample resolved markets:")
    for m in resolved_data[:5]:
        print(f"  - {m['question'][:60]}")
        print(f"    YES: ${m['yes_price']:.2f} | NO: ${m['no_price']:.2f}")
        print(f"    Volume: ${m['volume']:,.0f} | Outcome: {m['outcome']}")
    
    # Save
    output_file = 'data/training/resolved_markets.json'
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(resolved_data, f, indent=2)
    
    print(f"\nSaved to: {output_file}")
    
    return resolved_data


if __name__ == "__main__":
    fetch_resolved_markets()