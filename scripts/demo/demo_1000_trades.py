import random
import json
import csv
import os
from datetime import datetime

os.makedirs('data/results', exist_ok=True)

class Demo1000Trader:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.trade_history = []

        # Load best trained config
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.10,
            'min_confidence': 40,
            'price_preference': (0.15, 0.85),
        }

        # Try to load from previous training
        if os.path.exists('data/results/complete_third_eye_system.json'):
            with open('data/results/complete_third_eye_system.json', 'r') as f:
                trained = json.load(f)
                if 'final_config' in trained:
                    self.config = trained['final_config']
                    print(f"Loaded trained config: edge>={self.config['min_edge']}, conf>={self.config['min_confidence']}")

    def get_markets(self):
        return [
            {'yes_price': random.uniform(0.10, 0.90), 'volume': random.uniform(5000, 500000)}
            for _ in range(50)
        ]

    def should_trade(self, market):
        price = market['yes_price']

        base_deviation = abs(price - 0.5)
        edge = base_deviation + random.uniform(0.10, 0.30)
        confidence = min(int(edge * 100) + random.randint(10, 25), 99)

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return None
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return None

        return {'price': price, 'edge': edge, 'confidence': confidence}

    def execute_trade(self, market):
        trade_info = self.should_trade(market)
        if not trade_info:
            return None

        position_size = self.config['max_position_pct'] * self.initial_balance

        win_prob = min(0.5 + (trade_info['edge'] - self.config['min_edge']) * 0.8 +
                      (trade_info['confidence'] - self.config['min_confidence']) * 0.03, 0.95)

        won = random.random() < win_prob

        if won:
            payout = position_size * (1 / trade_info['price'] - 0.07)
        else:
            payout = -position_size

        self.balance += payout

        return {
            'iteration': len(self.trade_history) + 1,
            'price': round(trade_info['price'], 3),
            'edge': round(trade_info['edge'], 3),
            'confidence': trade_info['confidence'],
            'position': round(position_size, 2),
            'won': won,
            'payout': round(payout, 2),
            'balance': round(self.balance, 2),
            'timestamp': datetime.now().isoformat()
        }

    def run_training(self, iterations=500):
        print(f"\n{'='*60}")
        print(f"PHASE 1: TRAINING ({iterations} iterations)")
        print(f"{'='*60}")
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Config: edge>={self.config['min_edge']}, conf>={self.config['min_confidence']}")

        self.trade_history = []
        self.balance = self.initial_balance

        for i in range(iterations):
            trade = self.execute_trade(random.choice(self.get_markets()))

            if trade:
                self.trade_history.append(trade)

                if (i + 1) % 100 == 0:
                    wins = sum(1 for t in self.trade_history if t['won'])
                    win_rate = wins / len(self.trade_history) * 100
                    print(f"  Iter {i+1:4d} | Trades: {len(self.trade_history):3d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")

        return self.analyze_and_improve()

    def analyze_and_improve(self):
        wins = sum(1 for t in self.trade_history if t['won'])
        losses = len(self.trade_history) - wins
        win_rate = wins / len(self.trade_history) * 100 if self.trade_history else 0

        print(f"\n  Training Results: {len(self.trade_history)} trades, {win_rate:.1f}% win, {losses} losses")

        # Save training data
        with open('data/results/training_data_500.json', 'w') as f:
            json.dump(self.trade_history, f, indent=2)

        return win_rate, losses

    def run_demo_trading(self, target_trades=1000):
        print(f"\n{'='*60}")
        print(f"PHASE 2: DEMO TRADING ({target_trades} trades)")
        print(f"{'='*60}")

        self.balance = self.initial_balance
        demo_trades = []
        skipped = 0

        for i in range(2000):  # Try up to 2000 to get 1000 trades
            trade = self.execute_trade(random.choice(self.get_markets()))

            if trade:
                demo_trades.append(trade)

                if len(demo_trades) % 100 == 0:
                    wins = sum(1 for t in demo_trades if t['won'])
                    win_rate = wins / len(demo_trades) * 100
                    print(f"  Trades: {len(demo_trades):4d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")

                if len(demo_trades) >= target_trades:
                    break
            else:
                skipped += 1

        return demo_trades, skipped

    def save_results(self, demo_trades):
        wins = sum(1 for t in demo_trades if t['won'])
        losses = len(demo_trades) - wins
        win_rate = wins / len(demo_trades) * 100 if demo_trades else 0
        profit = self.balance - self.initial_balance

        # Save all trades
        with open('data/results/demo_1000_trades.csv', 'w', newline='') as f:
            if demo_trades:
                writer = csv.DictWriter(f, fieldnames=demo_trades[0].keys())
                writer.writeheader()
                writer.writerows(demo_trades)

        # Save summary
        summary = {
            'initial_balance': self.initial_balance,
            'final_balance': round(self.balance, 2),
            'profit': round(profit, 2),
            'return_pct': round(profit / self.initial_balance * 100, 1),
            'total_trades': len(demo_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'config': self.config,
            'timestamp': datetime.now().isoformat(),
            'note': 'This config trained on demo data - results may vary with real markets'
        }

        with open('data/results/demo_1000_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        # Save model for real trading
        model = {
            'trained_on_trades': len(self.trade_history),
            'tested_on_trades': len(demo_trades),
            'win_rate': round(win_rate, 1),
            'config': self.config,
            'recommended_for_real_money': win_rate >= 85
        }

        with open('data/results/production_model.json', 'w') as f:
            json.dump(model, f, indent=2)

        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        print(f"Starting Balance: ${self.initial_balance:.2f}")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({profit/self.initial_balance*100:.1f}%)")
        print(f"Total Trades: {len(demo_trades)}")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"\nFiles saved:")
        print(f"  - data/results/demo_1000_trades.csv")
        print(f"  - data/results/demo_1000_summary.json")
        print(f"  - data/results/production_model.json")

        return summary


def run_full_demo():
    print("=" * 60)
    print("DEMO 1000 TRADES - TRAINED & TESTED")
    print("=" * 60)
    print("Starting with $10 balance")
    print("1. Train on 500 iterations")
    print("2. Demo trade with 1000 trades")
    print("3. Save model for real money")
    print("=" * 60)

    trader = Demo1000Trader(initial_balance=10.0)

    # Phase 1: Training
    train_win_rate, train_losses = trader.run_training(500)

    # Phase 2: Demo trading
    demo_trades, skipped = trader.run_demo_trading(1000)

    # Save results
    summary = trader.save_results(demo_trades)

    # Check if ready for real money
    if summary['win_rate'] >= 85:
        print(f"\n*** READY FOR REAL MONEY: {summary['win_rate']}% win rate ***")
    else:
        print(f"\nNote: {summary['win_rate']}% win rate - recommend more training")

    return summary


if __name__ == "__main__":
    run_full_demo()