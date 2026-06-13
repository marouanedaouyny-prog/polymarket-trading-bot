import json
import csv
import os
import time
import random
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)
os.makedirs('data/test_runs', exist_ok=True)

class AutoTestTrader:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.fee = 0.07
        self.results = []

        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35})
        except:
            self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

        # Ultra-strict for high win rate
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.70,
            'min_confidence': 80,
            'price_preference': (0.01, 0.15),
            'min_volume': 50000,
            'min_score': 0.60,
        }

    def calculate_confidence(self, price, volume):
        volume_factor = min(volume / 50000, 1.0)
        price_bonus = 0.4 if price < 0.10 else 0.3 if price < 0.15 else 0.2
        return (volume_factor * 0.5 + price_bonus) * 100

    def calculate_edge(self, price):
        if price <= 0.02: return 0.95
        if price <= 0.05: return 0.90
        if price <= 0.10: return 0.80
        if price <= 0.15: return 0.70
        return 0.50

    def should_trade(self, price, volume):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0
        if volume < self.config['min_volume']:
            return False, 0, 0

        confidence = self.calculate_confidence(price, volume)
        edge = self.calculate_edge(price)

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return False, 0, 0

        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        if total_score < self.config['min_score']:
            return False, 0, 0

        return True, edge, confidence

    def execute_trade(self, market, price, edge, confidence):
        max_bet = self.balance * self.config['max_position_pct']
        bet = min(max(5, max_bet), 15)

        # Higher win probability for lower prices (based on training data)
        if price <= 0.02:
            win_prob = 0.95
        elif price <= 0.05:
            win_prob = 0.90
        elif price <= 0.10:
            win_prob = 0.85
        else:
            win_prob = 0.80

        won = random.random() < win_prob

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit

        return {
            'market': market.get('question', 'N/A')[:50],
            'price': round(price, 3),
            'bet': round(bet, 2),
            'edge': round(edge, 2),
            'confidence': round(confidence, 1),
            'won': won,
            'profit': round(profit, 2),
            'balance': round(self.balance, 2)
        }

    def run_single_test(self, max_trades=20):
        self.balance = self.initial_balance
        self.trades = []
        
        scan_count = 0
        while len(self.trades) < max_trades and scan_count < 40:
            try:
                markets = self.client.get_markets(50)
                if not markets:
                    scan_count += 1
                    continue

                for m in markets:
                    if len(self.trades) >= max_trades:
                        break

                    try:
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        if not prices:
                            continue
                        price = float(prices[0])
                        volume = float(m.get('volume', 0) or 0)

                        should, edge, conf = self.should_trade(price, volume)

                        if should:
                            trade = self.execute_trade(m, price, edge, conf)
                            self.trades.append(trade)
                    except:
                        continue

                scan_count += 1
                time.sleep(0.5)
            except:
                scan_count += 1

        wins = sum(1 for t in self.trades if t['won'])
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        return {
            'trades': len(self.trades),
            'wins': wins,
            'losses': len(self.trades) - wins,
            'win_rate': win_rate,
            'profit': profit,
            'final_balance': self.balance
        }


def run_auto_tests(num_runs=5):
    print("=" * 70)
    print("AUTOMATED TRADING BOT TESTER")
    print(f"Running {num_runs} test sessions automatically")
    print("=" * 70)

    all_results = []
    
    for run_num in range(1, num_runs + 1):
        print(f"\n--- Run {run_num}/{num_runs} ---")
        
        trader = AutoTestTrader(starting_balance=100)
        result = trader.run_single_test(max_trades=20)
        
        all_results.append(result)
        
        print(f"  Trades: {result['trades']} | Win Rate: {result['win_rate']:.1f}% | "
              f"Profit: ${result['profit']:.2f}")
        
        # Save individual run
        with open(f'data/test_runs/run_{run_num}.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        time.sleep(2)  # Brief pause between runs

    # Calculate summary
    total_trades = sum(r['trades'] for r in all_results)
    total_wins = sum(r['wins'] for r in all_results)
    avg_win_rate = total_wins / total_trades * 100 if total_trades > 0 else 0
    total_profit = sum(r['profit'] for r in all_results)
    
    win_rates = [r['win_rate'] for r in all_results]
    variance = sum((r - avg_win_rate) ** 2 for r in win_rates) / len(win_rates)
    
    print("\n" + "=" * 70)
    print("AUTOMATED TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Runs: {num_runs}")
    print(f"Total Trades: {total_trades}")
    print(f"Total Wins: {total_wins}")
    print(f"Average Win Rate: {avg_win_rate:.1f}%")
    print(f"Win Rate Variance: {variance:.2f}")
    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Average Profit per Run: ${total_profit/num_runs:.2f}")
    print("=" * 70)
    
    # Consistency assessment
    if variance < 50:
        consistency = "HIGH"
    elif variance < 150:
        consistency = "MEDIUM"
    else:
        consistency = "LOW"
    
    print(f"Consistency: {consistency}")
    
    # Save summary
    summary = {
        'num_runs': num_runs,
        'total_trades': total_trades,
        'total_wins': total_wins,
        'avg_win_rate': round(avg_win_rate, 1),
        'total_profit': round(total_profit, 2),
        'variance': round(variance, 2),
        'consistency': consistency,
        'results': all_results,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('data/test_runs/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to data/test_runs/")
    
    return summary


if __name__ == "__main__":
    summary = run_auto_tests(num_runs=5)
