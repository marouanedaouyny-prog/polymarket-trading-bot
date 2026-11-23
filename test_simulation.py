#!/usr/bin/env python3
"""Test simulation running the polymarket trading system with $20 starting balance."""

import sys
sys.path.insert(0, '.')

from agent_trading_system import TradingAgentSystem

def main():
    print("=" * 60)
    print("POLYMARKET TRADING SYSTEM - $20 PAPER TRADING SIMULATION")
    print("=" * 60)
    print(f"Starting Balance: $20.00")
    print(f"Config MIN_EDGE: {20 * 0.08:.2f} (8% of balance for min bet calculation)")
    print(f"Config MIN_CONFIDENCE: 85%")
    print(f"Config MAX_POSITION_PCT: 10%")
    print()
    
    # Initialize system with $20
    sys = TradingAgentSystem(starting_balance=20)
    
    print(f"\nSystem initialized with balance: ${sys.balance:.2f}")
    print(f"Initial balance: ${sys.initial_balance:.2f}")
    print(f"Risk config: {sys.risk}")
    print()
    
    # Run a short session (just a few trades to test)
    result = sys.lead_agent(max_trades=5, retrain_every=0)
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    if result:
        win_rate = result.get('win_rate', 0)
        profit = result.get('profit', 0)
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit: ${profit:.2f}")
        print(f"Final Balance: ${20 + profit:.2f}")
    else:
        print("Session ended early or failed.")

if __name__ == "__main__":
    main()