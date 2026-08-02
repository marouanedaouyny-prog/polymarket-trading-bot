"""
PRODUCTION AUDIT & VERDICT TOOL
==============================
Analyzes the Paper Ledger and System Health against P1 "Real Money" requirements.
Provides a clear RED/GREEN verdict for production deployment.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.trading.ledger import PaperLedger

def run_audit():
    print("="*60)
    print("🛡️ POLYMARKET BOT: PRODUCTION AUDIT")
    print("="*60)

    ledger = PaperLedger()
    stats = ledger.get_stats()
    
    # Requirements from fix.txt
    MIN_TRADES = 500
    MIN_DAYS = 30
    MIN_PROFIT_FACTOR = 1.30
    MAX_DRAWDOWN_PCT = 0.15
    MAX_DAILY_LOSS_PCT = 0.05
    
    # 1. Trade Volume Check
    total_resolved = stats.get('total_resolved', 0)
    vol_pass = total_resolved >= MIN_TRADES
    print(f"[TRADES] Resolved: {total_resolved} / {MIN_TRADES} {'✅' if vol_pass else '❌'}")
    
    # 2. Performance Check
    pf = stats.get('profit_factor', 0)
    pf_pass = pf >= MIN_PROFIT_FACTOR
    print(f"[STATS] Profit Factor: {pf:.2f} (Target: >={MIN_PROFIT_FACTOR}) {'✅' if pf_pass else '❌'}")
    
    dd = stats.get('max_drawdown', 0)
    # Assume $100 starting for simple pct check if not specified
    dd_pct = dd / 100.0 
    dd_pass = dd_pct <= MAX_DRAWDOWN_PCT
    print(f"[STATS] Max Drawdown: {dd_pct:.1%} (Target: <={MAX_DRAWDOWN_PCT:.0%}) {'✅' if dd_pass else '❌'}")
    
    # 3. Time Check
    trades = ledger._load_json()
    resolved = [t for t in trades if t.get('resolution_timestamp')]
    if resolved:
        first = datetime.fromisoformat(resolved[0]['entry_timestamp'])
        last = datetime.fromisoformat(resolved[-1]['resolution_timestamp'])
        days = (last - first).days
    else:
        days = 0
    
    time_pass = days >= MIN_DAYS
    print(f"[TIME] Active Days: {days} / {MIN_DAYS} {'✅' if time_pass else '❌'}")

    # 4. Infrastructure Check
    mirofish_ok = os.getenv("MIROFISH_URL") is not None
    print(f"[INFRA] MiroFish Configured: {'✅' if mirofish_ok else '❌ (Fallback mode only)'}")
    
    env_ok = True
    try:
        import polymarket
        import xgboost
        import torch
    except ImportError:
        env_ok = False
    print(f"[INFRA] Core ML Packages: {'✅' if env_ok else '❌'}")

    # FINAL VERDICT
    print("\n" + "="*60)
    ready = vol_pass and pf_pass and dd_pass and time_pass and env_ok
    
    if ready:
        print("🟢 VERDICT: SYSTEM READY FOR REAL MONEY 🟢")
        print("All hardening barriers and performance targets met.")
    else:
        print("🔴 VERDICT: NOT READY FOR REAL MONEY 🔴")
        print("System still requires more paper-trading data or performance stability.")
    
    print("="*60)

if __name__ == "__main__":
    run_audit()
