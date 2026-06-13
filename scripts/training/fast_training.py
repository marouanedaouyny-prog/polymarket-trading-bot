import random
import json
import csv
import time
from datetime import datetime
import os

class FastTrainingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0

        # Best performing config
        self.MAX_POSITION_PCT = 0.20
        self.MIN_EDGE = 0.03
        self.MIN_CONFIDENCE = 50
        self.POLYMARKET_FEE = 0.07

    def get_fake_markets(self):
        # Generate realistic market prices for training
        return [{'yes_price': random.uniform(0.15, 0.85), 'volume': random.uniform(5000, 100000)} for _ in range(50)]

    def simulate_trade(self, market):
        price = market['yes_price']
        edge = abs(price - 0.5) + random.uniform(0, 0.15)
        confidence = int(edge * 100) + random.randint(0, 25)

        if edge >= self.MIN_EDGE and confidence >= self.MIN_CONFIDENCE:
            # Fixed position size based on INITIAL balance, not current balance
            position_size = random.uniform(0.05, self.MAX_POSITION_PCT) * self.initial_balance
            # Cap position to avoid extreme gains
            position_size = min(position_size, self.balance * 0.5)

            won = random.random() < min(0.5 + edge * 0.6, 0.85)

            if won:
                payout = position_size * (1 / price - self.POLYMARKET_FEE)
            else:
                payout = -position_size

            return {
                'market': f"Market_{self.total_trades + 1}",
                'price': round(price, 3),
                'position': round(position_size, 2),
                'edge': round(edge, 3),
                'confidence': confidence,
                'won': won,
                'payout': round(payout, 2),
                'balance_after': round(self.balance + payout, 2),
                'timestamp': datetime.now().isoformat()
            }
        return None

    def run_training(self, num_trades=1000):
        print(f"Starting FAST TRAINING - {num_trades} trades")
        print(f"Initial Balance: ${self.balance:.2f}")
        print(f"Config: max_pos={self.MAX_POSITION_PCT}, min_edge={self.MIN_EDGE}, min_conf={self.MIN_CONFIDENCE}")
        print("=" * 60)

        start_time = time.time()

        for i in range(num_trades):
            markets = self.get_fake_markets()
            trade = self.simulate_trade(random.choice(markets))

            if trade:
                self.balance = trade['balance_after']
                self.total_trades += 1

                if trade['won']:
                    self.win_count += 1

                self.trades.append(trade)

                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance

                if (i + 1) % 100 == 0:
                    win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
                    print(f"Trades: {self.total_trades:4d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")

        elapsed = time.time() - start_time
        return self.save_results(elapsed)

    def save_results(self, elapsed):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        profit = self.balance - self.initial_balance
        return_pct = (profit / self.initial_balance) * 100
        max_drawdown = ((self.peak_balance - self.balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0

        os.makedirs('data/results', exist_ok=True)

        with open('data/results/training_trades.csv', 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        with open('data/results/training_history.json', 'w') as f:
            json.dump(self.trades, f, indent=2)

        summary = {
            'total_trades': self.total_trades,
            'win_rate': round(win_rate, 1),
            'final_balance': round(self.balance, 2),
            'profit': round(profit, 2),
            'return_pct': round(return_pct, 1),
            'max_drawdown': round(max_drawdown, 1),
            'elapsed_seconds': round(elapsed, 1),
            'config': {
                'max_position_pct': self.MAX_POSITION_PCT,
                'min_edge': self.MIN_EDGE,
                'min_confidence': self.MIN_CONFIDENCE,
            }
        }

        with open('data/results/training_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)
        print(f"Total Trades: {self.total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({return_pct:.1f}%)")
        print(f"Time: {elapsed:.1f}s")
        print("\nSaved to data/results/")

        return summary


def train_with_retraining(cycles=3, trades_per_cycle=1000):
    all_results = []

    for cycle in range(1, cycles + 1):
        print(f"\n{'='*60}")
        print(f"TRAINING CYCLE {cycle}/{cycles}")
        print(f"{'='*60}\n")

        # Use consistent starting balance each cycle for fair comparison
        bot = FastTrainingBot(initial_balance=10.0)

        # Auto-tune based on previous cycle
        if cycle > 1 and all_results:
            prev = all_results[-1]
            print(f"Previous: win_rate={prev['win_rate']:.1f}%, balance=${prev['final_balance']:.2f}")

            if prev['win_rate'] > 70:
                bot.MIN_EDGE = 0.025
                bot.MIN_CONFIDENCE = 45
                bot.MAX_POSITION_PCT = 0.22
                print(" -> Tuning: More aggressive")
            elif prev['win_rate'] < 60:
                bot.MIN_EDGE = 0.04
                bot.MIN_CONFIDENCE = 55
                bot.MAX_POSITION_PCT = 0.15
                print(" -> Tuning: More conservative")

        result = bot.run_training(trades_per_cycle)
        result['cycle'] = cycle
        all_results.append(result)

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL RESULTS ACROSS ALL CYCLES")
    print(f"{'='*60}")

    total_trades = sum(r['total_trades'] for r in all_results)
    avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
    final_balance = all_results[-1]['final_balance']
    total_profit = final_balance - 10.0
    total_return = (total_profit / 10.0) * 100

    print(f"Total Trades: {total_trades}")
    print(f"Average Win Rate: {avg_win_rate:.1f}%")
    print(f"Final Balance: ${final_balance:.2f}")
    print(f"Total Profit: ${total_profit:.2f} ({total_return:.1f}%)")

    # Save final model config
    final_config = {
        'total_trades': total_trades,
        'avg_win_rate': round(avg_win_rate, 1),
        'final_balance': final_balance,
        'total_profit': round(total_profit, 2),
        'total_return_pct': round(total_return, 1),
        'cycles': cycles,
        'trades_per_cycle': trades_per_cycle,
        'best_config': all_results[-1]['config']
    }

    with open('data/results/final_model.json', 'w') as f:
        json.dump(final_config, f, indent=2)

    print("\nModel saved to data/results/final_model.json")

    return all_results


if __name__ == "__main__":
    import sys
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    trades = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    print(f"Running {cycles} cycles of {trades} trades each")
    train_with_retraining(cycles, trades)