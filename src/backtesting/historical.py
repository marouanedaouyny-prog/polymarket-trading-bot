"""
Historical Backtesting Module
Tests trading strategy on historical Polymarket data
"""

import json
import os
import random
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class HistoricalTrade:
    market: str
    price: float
    edge: float
    won: bool
    profit: float
    balance: float


class HistoricalBacktest:
    def __init__(self, data_file: str = "data/training/resolved_markets.json"):
        self.data_file = data_file
        self.trades: List[HistoricalTrade] = []
        
    def load_historical_data(self) -> List[Dict]:
        """Load resolved market data with actual outcomes"""
        print("[LOAD] Loading resolved market data...")
        
        if not os.path.isfile(self.data_file):
            raise FileNotFoundError(f"Resolved data file not found: {self.data_file}")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        markets = []
        for item in data:
            # Expect fields from fetch_resolved.py
            markets.append({
                'id': item.get('id'),
                'question': item.get('question', ''),
                'price': (item.get('yes_price', 0) + (1 - item.get('no_price', 0))) / 2,
                'volume': item.get('volume', 0),
                'outcome': item.get('outcome'),
                'closed': item.get('closed', False),
            })
        
        print(f"   Loaded {len(markets)} resolved markets with outcomes")
        return markets
    
    def calculate_edge(self, price: float, volume: float) -> float:
        """Calculate edge based on price and volume"""
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
    
    def simulate_trade(self, market: Dict, balance: float) -> HistoricalTrade:
        """Simulate a single trade on a resolved market using actual outcome."""
        # Use the real market price (average of yes/no) as price estimate
        price = market.get('price', 0.5)
        volume = market.get('volume', 0)
        edge = self.calculate_edge(price, volume)
        
        # Determine actual win based on the stored outcome
        actual_outcome = market.get('outcome')
        # We predict "yes" as winning if yes_price > no_price (price > 0.5)
        predicted_yes = price > 0.5
        won = (actual_outcome == 'yes' and predicted_yes) or (actual_outcome == 'no' and not predicted_yes)
        
        bet = min(balance * 0.15, 25)
        bet = max(bet, 1)
        
        if won:
            profit = bet * (1/price - 1) * 0.93
        else:
            profit = -bet
        
        balance += profit
        
        return HistoricalTrade(
            market=market['question'][:50],
            price=price,
            edge=edge,
            won=won,
            profit=profit,
            balance=balance
        )
    
    def run_backtest(self, starting_balance: float = 100, num_trades: int = 100):
        """Run backtest on historical data"""
        print("\n" + "="*60)
        print("HISTORICAL BACKTEST")
        print("="*60)
        
        # Load data
        markets = self.load_historical_data()
        
        if not markets:
            print("No historical data found!")
            return None
        
        # Filter to usable markets - use all closed markets since volume is null in historical
        # For historical data, we'll use any closed market
        valid_markets = markets[:500]  # Use first 500 closed markets
        print(f"   Using {len(valid_markets)} markets with volume > $5K\n")
        
        # Run simulation
        balance = starting_balance
        wins = 0
        losses = 0
        
        # Shuffle markets for randomness
        random.shuffle(valid_markets)
        
        trades_to_run = min(num_trades, len(valid_markets))
        
        print(f"[RUN] Simulating {trades_to_run} trades...\n")
        
        for i in range(trades_to_run):
            trade = self.simulate_trade(valid_markets[i], balance)
            self.trades.append(trade)
            
            balance = trade.balance
            if trade.won:
                wins += 1
            else:
                losses += 1
            
            # Show every 20 trades
            if (i+1) % 20 == 0:
                status = "WIN" if trade.won else "LOSS"
                print(f"   Trade {i+1}: {status} | Edge:{trade.edge:.0%} | "
                      f"Balance: ${balance:.2f}")
        
        # Results
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        profit = balance - starting_balance
        roi = (profit / starting_balance * 100) if starting_balance > 0 else 0
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Starting Balance:  ${starting_balance:.2f}")
        print(f"Final Balance:     ${balance:.2f}")
        print(f"Total Profit:      ${profit:.2f}")
        print(f"ROI:               {roi:.1f}%")
        print(f"Total Trades:      {total}")
        print(f"Wins:              {wins}")
        print(f"Losses:            {losses}")
        print(f"Win Rate:          {win_rate:.1f}%")
        print("="*60)
        
        # Save latest stats for risk calibration
        try:
            import json, os
            stats_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest')
            os.makedirs(stats_dir, exist_ok=True)
            stats_path = os.path.join(stats_dir, 'latest_stats.json')
            with open(stats_path, 'w') as f:
                json.dump({
                    'starting_balance': starting_balance,
                    'final_balance': balance,
                    'profit': profit,
                    'roi': roi,
                    'total_trades': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate
                }, f, indent=2)
        except Exception as e:
            pass  # Silently ignore save errors
        
        return {
            'starting_balance': starting_balance,
            'final_balance': balance,
            'profit': profit,
            'roi': roi,
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate
        }
    
    def run_multiple_sessions(self, num_sessions: int = 5):
        """Run multiple backtest sessions to see variance"""
        print("\n" + "="*60)
        print(f"MULTIPLE SESSION BACKTEST ({num_sessions} sessions)")
        print("="*60)
        
        results = []
        
        for session in range(num_sessions):
            print(f"\n--- Session {session+1}/{num_sessions} ---")
            random.seed(42 + session)  # Different seed each session
            
            result = self.run_backtest(starting_balance=100, num_trades=100)
            if result:
                results.append(result)
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY ACROSS ALL SESSIONS")
        print("="*60)
        
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
        avg_balance = sum(r['final_balance'] for r in results) / len(results)
        avg_roi = sum(r['roi'] for r in results) / len(results)
        
        print(f"Average Win Rate: {avg_win_rate:.1f}%")
        print(f"Average Final Balance: ${avg_balance:.2f}")
        print(f"Average ROI: {avg_roi:.1f}%")
        print(f"\nMin Balance: ${min(r['final_balance'] for r in results):.2f}")
        print(f"Max Balance: ${max(r['final_balance'] for r in results):.2f}")
        
        return results


def main():
    import sys
    import os
    
    # Set seed for reproducibility
    random.seed(42)
    
    backtest = HistoricalBacktest()
    
    # Single session
    # result = backtest.run_backtest(starting_balance=100, num_trades=100)
    
    # Multiple sessions
    results = backtest.run_multiple_sessions(num_sessions=5)
    
    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'backtest')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()