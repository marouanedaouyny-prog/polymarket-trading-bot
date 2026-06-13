import random
import json
import csv
import time
from datetime import datetime
from data.polymarket_client import PolymarketClient

class ContinuousTrainingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        self.client = PolymarketClient()
        self.training_history = []

        # Best performing config from analysis
        self.MAX_POSITION_PCT = 0.20
        self.STOP_LOSS_PCT = 0.05
        self.TAKE_PROFIT_MULT = 2.0
        self.POLYMARKET_FEE = 0.07
        self.MIN_EDGE = 0.03
        self.MIN_CONFIDENCE = 50

    def get_markets(self):
        markets = self.client.get_markets(50)
        parsed = []

        for m in markets:
            try:
                outcome_prices_str = m.get('outcomePrices', '[]')
                outcome_prices = json.loads(outcome_prices_str)

                if not outcome_prices or len(outcome_prices) < 2:
                    continue

                yes_price = float(outcome_prices[0])
                volume = float(m.get('volume', 0) or 0)

                if volume > 5000:
                    parsed.append({
                        'question': m.get('question', 'N/A')[:60],
                        'yes_price': yes_price,
                        'volume': volume,
                    })
            except:
                continue

        return parsed

    def simulate_trade(self, market):
        price = market['yes_price']
        edge = abs(price - 0.5) + random.uniform(0, 0.15)
        confidence = int(edge * 100) + random.randint(0, 25)

        if edge >= self.MIN_EDGE and confidence >= self.MIN_CONFIDENCE:
            position_size = random.uniform(0.05, self.MAX_POSITION_PCT) * self.balance
            won = random.random() < min(0.5 + edge * 0.6, 0.85)

            if won:
                payout = position_size * (1 / price - self.POLYMARKET_FEE)
            else:
                payout = -position_size

            return {
                'market': market['question'],
                'price': price,
                'position': position_size,
                'edge': edge,
                'confidence': confidence,
                'won': won,
                'payout': payout,
                'balance_after': self.balance + payout
            }

        return None

    def run_training(self, num_iterations=1000, delay=1):
        print(f"Starting CONTINUOUS TRAINING - {num_iterations} iterations")
        print(f"Initial Balance: ${self.balance:.2f}")
        print(f"Config: max_pos={self.MAX_POSITION_PCT}, min_edge={self.MIN_EDGE}, min_conf={self.MIN_CONFIDENCE}")
        print("=" * 70)

        start_time = time.time()
        iteration = 0
        no_trade_count = 0

        while iteration < num_iterations and no_trade_count < 20:
            markets = self.get_markets()

            if not markets:
                print(f"Iteration {iteration + 1}: No markets available")
                time.sleep(delay)
                continue

            trade = self.simulate_trade(random.choice(markets))

            if trade:
                self.balance = trade['balance_after']
                self.total_trades += 1

                if trade['won']:
                    self.win_count += 1

                self.trades.append(trade)
                self.training_history.append({
                    'iteration': iteration + 1,
                    'market': trade['market'],
                    'price': trade['price'],
                    'edge': trade['edge'],
                    'confidence': trade['confidence'],
                    'won': trade['won'],
                    'payout': trade['payout'],
                    'balance': self.balance,
                    'timestamp': datetime.now().isoformat()
                })

                if self.balance > self.peak_balance:
                    self.peak_balance = self.balance

                if (iteration + 1) % 100 == 0:
                    win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
                    print(f"Iter {iteration + 1:4d} | Trades: {self.total_trades:3d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")

                no_trade_count = 0
            else:
                no_trade_count += 1

            iteration += 1
            time.sleep(delay)

        elapsed = time.time() - start_time
        return self.save_results(elapsed)

    def save_results(self, elapsed):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        profit = self.balance - self.initial_balance
        return_pct = (profit / self.initial_balance) * 100
        max_drawdown = ((self.peak_balance - self.balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0

        # Save trades CSV
        with open('data/results/training_trades.csv', 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        # Save training history with iterations
        with open('data/results/training_history.json', 'w') as f:
            json.dump(self.training_history, f, indent=2)

        # Save summary
        summary = {
            'total_trades': self.total_trades,
            'win_rate': win_rate,
            'final_balance': self.balance,
            'profit': profit,
            'return_pct': return_pct,
            'max_drawdown': max_drawdown,
            'elapsed_seconds': elapsed,
            'config': {
                'max_position_pct': self.MAX_POSITION_PCT,
                'stop_loss_pct': self.STOP_LOSS_PCT,
                'min_edge': self.MIN_EDGE,
                'min_confidence': self.MIN_CONFIDENCE,
            }
        }

        with open('data/results/training_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 70)
        print("TRAINING COMPLETE")
        print("=" * 70)
        print(f"Total Trades: {self.total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({return_pct:.1f}%)")
        print(f"Max Drawdown: {max_drawdown:.1f}%")
        print(f"Time: {elapsed:.1f}s")
        print("\nFiles saved:")
        print("  - data/results/training_trades.csv")
        print("  - data/results/training_history.json")
        print("  - data/results/training_summary.json")

        return summary


def train_and_retrain(cycles=3, trades_per_cycle=1000):
    for cycle in range(1, cycles + 1):
        print(f"\n{'='*70}")
        print(f"TRAINING CYCLE {cycle}/{cycles}")
        print(f"{'='*70}\n")

        bot = ContinuousTrainingBot(initial_balance=10.0)

        # Adjust config based on previous results
        if cycle > 1:
            with open('data/results/training_summary.json', 'r') as f:
                prev = json.load(f)
                print(f"Previous cycle win rate: {prev['win_rate']:.1f}%")

                # Tune based on performance
                if prev['win_rate'] > 70:
                    bot.MIN_EDGE = 0.025
                    bot.MIN_CONFIDENCE = 45
                    bot.MAX_POSITION_PCT = 0.22
                elif prev['win_rate'] < 60:
                    bot.MIN_EDGE = 0.04
                    bot.MIN_CONFIDENCE = 55
                    bot.MAX_POSITION_PCT = 0.15

        result = bot.run_training(trades_per_cycle, delay=0.5)

    print(f"\n{'='*70}")
    print("ALL TRAINING CYCLES COMPLETE")
    print(f"{'='*70}")

    # Final summary
    with open('data/results/training_summary.json', 'r') as f:
        final = json.load(f)
    print(f"\nFinal Results:")
    print(f"  Total trades across all cycles: {final['total_trades']}")
    print(f"  Win rate: {final['win_rate']:.1f}%")
    print(f"  Final balance: ${final['final_balance']:.2f}")
    print(f"  Return: {final['return_pct']:.1f}%")


if __name__ == "__main__":
    import sys

    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    trades = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    print(f"Running {cycles} cycles with {trades} trades each")
    train_and_retrain(cycles, trades)