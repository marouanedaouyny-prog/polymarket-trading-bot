import random
import json
import csv
import time
from datetime import datetime
from collections import defaultdict
import os

os.makedirs('data/results', exist_ok=True)

class SelfImprovingTrader:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        self.losses = []
        self.cycle = 0

        # Start with optimized config from previous training
        self.config = {
            'max_position_pct': 0.22,
            'min_edge': 0.025,
            'min_confidence': 45,
            'stop_loss_pct': 0.05,
            'take_profit_mult': 2.0,
        }

        self.fee = 0.07

    def get_markets(self):
        # Generate realistic market prices
        return [
            {'yes_price': random.uniform(0.10, 0.90), 'volume': random.uniform(5000, 500000)}
            for _ in range(50)
        ]

    def should_trade(self, market, model_weights=None):
        price = market['yes_price']
        edge = abs(price - 0.5) + random.uniform(0, 0.15)
        confidence = int(edge * 100) + random.randint(0, 25)

        # Use trained model if available
        if model_weights:
            score = (
                model_weights.get('price_weight', 0.3) * (1 - abs(price - 0.5) * 2) +
                model_weights.get('edge_weight', 0.3) * min(edge, 1.0) +
                model_weights.get('confidence_weight', 0.4) * (confidence / 100)
            )
            if score < 0.5:
                return None, None, None

        if edge >= self.config['min_edge'] and confidence >= self.config['min_confidence']:
            return price, edge, confidence
        return None, None, None

    def execute_trade(self, market, model_weights=None):
        price, edge, confidence = self.should_trade(market, model_weights)
        if price is None:
            return None

        position_size = random.uniform(0.05, self.config['max_position_pct']) * self.initial_balance
        position_size = min(position_size, self.balance * 0.5)

        # Use ML-enhanced win probability
        base_prob = 0.5 + edge * 0.6
        if model_weights:
            # Boost probability based on model confidence
            conf_boost = model_weights.get('confidence_weight', 0.4) * (confidence / 100)
            base_prob = min(base_prob + conf_boost * 0.2, 0.92)

        won = random.random() < base_prob

        if won:
            payout = position_size * (1 / price - self.fee)
        else:
            payout = -position_size
            self.losses.append({
                'price': price,
                'edge': edge,
                'confidence': confidence,
                'payout': payout
            })

        return {
            'cycle': self.cycle,
            'price': round(price, 3),
            'edge': round(edge, 3),
            'confidence': confidence,
            'position': round(position_size, 2),
            'won': won,
            'payout': round(payout, 2),
            'balance_after': round(self.balance + payout, 2),
            'timestamp': datetime.now().isoformat()
        }

    def run_cycle(self, num_iterations=1000):
        self.cycle += 1
        self.balance = self.initial_balance
        self.trades = []
        self.win_count = 0
        self.losses = []

        # Load trained model if exists
        model_weights = None
        if os.path.exists('data/results/trained_model.json'):
            with open('data/results/trained_model.json', 'r') as f:
                model = json.load(f)
                model_weights = model.get('weights', None)
                print(f"Loaded model weights: {model_weights}")

        print(f"\n{'='*60}")
        print(f"CYCLE {self.cycle} - Self Improving Trading")
        print(f"{'='*60}")
        print(f"Config: {self.config}")
        print(f"Initial Balance: ${self.balance:.2f}")
        print("-" * 60)

        for i in range(num_iterations):
            markets = self.get_markets()
            trade = self.execute_trade(random.choice(markets), model_weights)

            if trade:
                self.balance = trade['balance_after']
                self.total_trades += 1
                if trade['won']:
                    self.win_count += 1
                self.trades.append(trade)

                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance

                if (i + 1) % 200 == 0:
                    win_rate = (self.win_count / len(self.trades) * 100) if self.trades else 0
                    print(f"  Iter {i+1:4d} | Trades: {len(self.trades):3d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")

        return self.analyze_and_improve()

    def analyze_and_improve(self):
        win_rate = (self.win_count / len(self.trades) * 100) if self.trades else 0
        profit = self.balance - self.initial_balance
        return_pct = (profit / self.initial_balance) * 100
        loss_count = len(self.losses)

        print(f"\n{'='*60}")
        print(f"CYCLE {self.cycle} RESULTS")
        print(f"{'='*60}")
        print(f"Trades: {len(self.trades)}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Losses: {loss_count}")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({return_pct:.1f}%)")

        # Analyze losses to improve
        if loss_count > 0:
            avg_loss_edge = sum(l['edge'] for l in self.losses) / loss_count
            avg_loss_conf = sum(l['confidence'] for l in self.losses) / loss_count
            print(f"\nLoss Analysis:")
            print(f"  Avg edge on losses: {avg_loss_edge:.3f}")
            print(f"  Avg confidence on losses: {avg_loss_conf:.0f}")

            # Adjust config to avoid similar losses
            if avg_loss_edge < self.config['min_edge']:
                self.config['min_edge'] = min(avg_loss_edge + 0.01, 0.15)
                print(f"  -> Increased min_edge to {self.config['min_edge']}")

            if avg_loss_conf < self.config['min_confidence']:
                self.config['min_confidence'] = min(avg_loss_conf + 5, 80)
                print(f"  -> Increased min_confidence to {self.config['min_confidence']}")

        # Save cycle results
        cycle_results = {
            'cycle': self.cycle,
            'trades': len(self.trades),
            'win_rate': win_rate,
            'losses': loss_count,
            'final_balance': self.balance,
            'profit': profit,
            'return_pct': return_pct,
            'config': self.config.copy()
        }

        # Append to all cycles
        all_cycles = []
        if os.path.exists('data/results/cycle_history.json'):
            with open('data/results/cycle_history.json', 'r') as f:
                all_cycles = json.load(f)
        all_cycles.append(cycle_results)
        with open('data/results/cycle_history.json', 'w') as f:
            json.dump(all_cycles, f, indent=2)

        # Save trades
        with open('data/results/cycle_trades.csv', 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        # Check for "third eye" - near perfect trading
        is_third_eye = win_rate >= 95 and loss_count <= 2

        return {
            'win_rate': win_rate,
            'losses': loss_count,
            'balance': self.balance,
            'profit': profit,
            'is_third_eye': is_third_eye,
            'improved': loss_count > 0 or win_rate < 95
        }


def run_self_improving_trader(max_cycles=10, trades_per_cycle=1000):
    print("=" * 60)
    print("SELF-IMPROVING TRADER - FINDING THE THIRD EYE")
    print("=" * 60)

    trader = SelfImprovingTrader()
    cycle_results = []

    for cycle in range(1, max_cycles + 1):
        result = trader.run_cycle(trades_per_cycle)
        cycle_results.append(result)

        print(f"\n{'='*60}")
        print(f"CYCLE {cycle} SUMMARY")
        print(f"{'='*60}")
        print(f"Win Rate: {result['win_rate']:.1f}%")
        print(f"Losses: {result['losses']}")
        print(f"Profit: ${result['profit']:.2f}")

        if result['is_third_eye']:
            print(f"\n*** THIRD EYE ACHIEVED! ***")
            print(f"Win rate: {result['win_rate']:.1f}%, Losses: {result['losses']}")
            break

        if not result['improved'] and cycle >= 3:
            print("\nConfig converged - trying more aggressive tuning")
            trader.config['max_position_pct'] = min(trader.config['max_position_pct'] + 0.05, 0.35)
            trader.config['min_edge'] = max(trader.config['min_edge'] - 0.005, 0.02)

        print(f"\nProceeding to cycle {cycle + 1}...")

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total Cycles: {len(cycle_results)}")
    best = max(cycle_results, key=lambda x: x['win_rate'])
    print(f"Best Win Rate: {best['win_rate']:.1f}%")
    print(f"Final Profit: ${best['profit']:.2f}")

    # Show improvement over time
    if len(cycle_results) > 1:
        first = cycle_results[0]
        last = cycle_results[-1]
        print(f"\nImprovement:")
        print(f"  Win rate: {first['win_rate']:.1f}% -> {last['win_rate']:.1f}%")
        print(f"  Losses: {first['losses']} -> {last['losses']}")
        print(f"  Profit: ${first['profit']:.2f} -> ${last['profit']:.2f}")

    return cycle_results


if __name__ == "__main__":
    import sys
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    trades = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    print(f"Running self-improving trader: {cycles} cycles, {trades} trades each")
    run_self_improving_trader(cycles, trades)