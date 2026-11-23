#!/usr/bin/env python3
"""100-trade simulation with $20 starting balance.

Runs the lead agent for 100 trades (will take ~20 days at 5 trades/day).
Uses mocked market data since real API may not have 100 suitable markets.
"""

import sys
import random
import json
sys.path.insert(0, '.')

from agent_trading_system import TradingAgentSystem
from src.utils.config import config

def random_market_data():
    """Generate realistic-ish mock market data based on config ranges."""
    # Price: $0.05-0.50, but mostly in $0.10-0.35 range (per README original, though config says 0.05-0.50)
    price = round(random.uniform(0.05, 0.50), 2)
    
    # Volume: usually > $10K, sometimes lower
    volume_options = [8000, 12000, 15000, 25000, 35000]
    volume = random.choice(volume_options)
    
    # Edge: sometimes good, sometimes bad - based on config 8% min
    edge = round(random.uniform(0.03, 0.20), 3)
    
    # Confidence: based on sentiment, usually 60-95%
    confidence = random.randint(60, 95)
    
    # EV calculation
    fee = 0.07
    edge_pct = edge
    ev = (edge_pct * (1/price - 1) * (1 - fee)) - ((1 - edge_pct))
    
    return {
        'price': price,
        'volume': volume,
        'edge': edge,
        'confidence': confidence,
        'ev': round(ev, 4),
        'canonical_id': f"PM-{random.randint(1000,9999)}"
    }

def run_100_trade_simulation():
    """Run 100-trade simulation."""
    print("=" * 60)
    print("POLYMARKET - 100 TRADE SIMULATION ($20 START)")
    print("=" * 60)
    print(f"Starting Balance: $20.00")
    print(f"Config: MIN_EDGE={config.MIN_EDGE*100:.1f}%, MIN_CONFIDENCE={config.MIN_CONFIDENCE}%")
    print(f"Config: Max position 10%, Stop-loss 15%, Take-profit 50%")
    print(f"Config: Daily loss limit 5%, Max daily trades 5")
    print()
    
    # Initialize system
    sys = TradingAgentSystem(starting_balance=20)
    initial_balance = 20.0
    
    # Track results
    total_trades = 0
    approved_trades = 0
    wins = 0
    losses = 0
    daily_trades = 0
    daily_pnl = 0
    peak_balance = 20.0
    max_drawdown = 0.0
    daily_start = 20.0
    
    # Trade results tracking
    trade_details = []
    
    print("Starting 100-trade simulation (press Ctrl+C to stop early)...\n")
    
    try:
        for trade_num in range(1, 101):
            # Generate mock market data
            market = random_market_data()
            
            # Risk validation
            risk_check = sys.risk_agent(market)
            
            if not risk_check['approved']:
                # Still count as attempted
                trade_details.append({
                    'trade': trade_num,
                    'price': market['price'],
                    'edge': market['edge'],
                    'confidence': market['confidence'],
                    'result': 'BLOCKED',
                    'reason': risk_check['reason']
                })
                # Every 10 trades print status
                if trade_num % 10 == 0:
                    print(f"Trade {trade_num}: {approved_trades} approved, "
                          f"{wins} wins, {losses} losses, "
                          f"Balance: ${sys.balance:.2f}")
                continue
            
            approved_trades += 1
            daily_trades += 1
            
            # Execute trade
            result = sys.trader_agent(market)
            total_trades += 1
            
            won = result['won']
            profit = result['profit']
            
            # Track wins/losses
            if won:
                wins += 1
            else:
                losses += 1
            
            # Track balance
            sys.balance += profit
            daily_pnl += profit
            
            # Track peak and drawdown
            if sys.balance > peak_balance:
                peak_balance = sys.balance
            current_dd = (peak_balance - sys.balance) / peak_balance * 100
            if current_dd > max_drawdown:
                max_drawdown = current_dd
            
            # Daily loss limit check
            if (daily_start - sys.balance) / daily_start * 100 >= config.DAILY_LOSS_LIMIT * 100:
                print(f"Trade {trade_num}: Daily loss limit ({config.DAILY_LOSS_LIMIT*100:.0f}%) reached! Stopping.")
                break
            
            # Record trade detail
            trade_details.append({
                'trade': trade_num,
                'price': market['price'],
                'edge': market['edge']*100,
                'confidence': market['confidence'],
                'won': won,
                'profit': profit,
                'balance': sys.balance
            })
            
            # Print every 10 trades
            if trade_num % 10 == 0:
                win_rate = wins / total_trades * 100 if total_trades > 0 else 0
                print(f"Trade {trade_num}: {wins}/{total_trades} wins ({win_rate:.1f}%), "
                      f"Balance: ${sys.balance:.2f}, "
                      f"Daily P&L: ${daily_pnl:.2f}")
            
            # Simate daily trade limit - every 5 trades reset daily counter
            # (In real system, this would reset at midnight)
            if total_trades % 5 == 0:
                daily_trades = 0  # Reset daily counter simulation
                daily_start = sys.balance  # Reset daily P&L baseline
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    
    # Final summary
    print("\n" + "=" * 60)
    print("100 TRADE SIMULATION - FINAL RESULTS")
    print("=" * 60)
    
    actual_trades = len([t for t in trade_details if t['result'] != 'BLOCKED'])
    actual_wins = len([t for t in trade_details if t['result'] != 'BLOCKED' and t['won']])
    actual_losses = len([t for t in trade_details if t['result'] != 'BLOCKED' and not t['won']])
    
    final_balance = sys.balance
    profit = final_balance - initial_balance
    profit_pct = profit / initial_balance * 100
    win_rate = actual_wins / actual_trades * 100 if actual_trades > 0 else 0
    
    print(f"\nStarting Balance: ${initial_balance:.2f}")
    print(f"Final Balance: ${final_balance:.2f}")
    print(f"Total Profit: ${profit:.2f} ({profit_pct:.1f}%)")
    print(f"\nTrade Statistics:")
    print(f"  Total Trades Attempted: {total_trades}")
    print(f"  Approved Trades: {approved_trades}")
    print(f"  Executed Trades: {actual_trades}")
    print(f"  Wins: {actual_wins}")
    print(f"  Losses: {actual_losses}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"\nRisk Metrics:")
    print(f"  Max Drawdown: {max_drawdown:.1f}%")
    print(f"  Final Balance Change: {profit_pct:.1f}%")
    
    # Expected vs actual
    print(f"\nConfig Parameters Used:")
    print(f"  MIN_EDGE: {config.MIN_EDGE*100:.1f}%")
    print(f"  MIN_CONFIDENCE: {config.MIN_CONFIDENCE}%")
    print(f"  MAX_POSITION_PCT: {config.MAX_POSITION_PCT*100:.0f}%")
    print(f"  STOP_LOSS_PCT: {config.STOP_LOSS_PCT*100:.0f}%")
    print(f"  TAKE_PROFIT_PCT: {config.TAKE_PROFIT_PCT*100:.0f}%")
    
    # Simulation quality note
    print(f"\nNote: This uses mocked market data based on config ranges.")
    print(f"Real results will vary based on actual market conditions.")
    print(f"The system's risk controls (stop-loss, daily limits) are active.")
    
    return {
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'profit': profit,
        'profit_pct': profit_pct,
        'win_rate': win_rate,
        'total_trades': actual_trades,
        'max_drawdown': max_drawdown
    }

if __name__ == "__main__":
    run_100_trade_simulation()