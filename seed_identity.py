"""
Seed script for MarketIdentityManager
Ingests historical market data and resolves identities.
"""

import json
import os
from src.utils.identity_manager import MarketIdentityManager

def seed():
    manager = MarketIdentityManager()
    manager.batch_mode = True
    
    # 1. Ingest Resolved Markets
    resolved_file = 'data/training/resolved_markets.json'
    if os.path.exists(resolved_file):
        with open(resolved_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Seeding {len(data)} resolved markets...")
            for m in data:
                manager.resolve_market(m)
                
    # 2. Ingest Public Markets (Rich data)
    public_file = 'data/public_markets.json'
    if os.path.exists(public_file):
        with open(public_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            markets = data.get('data', [])
            print(f"Seeding {len(markets)} public markets...")
            for m in markets:
                cid, conf, is_new = manager.resolve_market(m)
                
                # If we found a winner in tokens, update the canonical outcome
                tokens = m.get('tokens', [])
                for t in tokens:
                    if t.get('winner') is True:
                        manager.update_outcome(cid, t.get('outcome').lower())
                        break

    manager.commit()
    print(f"Identity Graph seeded. Total canonical entities: {len(manager.graph)}")

if __name__ == "__main__":
    seed()
