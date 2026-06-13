import random
import json
import csv
import os
from datetime import datetime

os.makedirs('data/results', exist_ok=True)

class CompleteThirdEyeSystem:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.cycle_count = 0

        # Start with basic config
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.10,
            'min_confidence': 40,
            'price_preference': (0.15, 0.85),
        }
        self.target_win_rate = 95
        self.max_losses_per_cycle = 3

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

        return {
            'price': round(trade_info['price'], 3),
            'edge': round(trade_info['edge'], 3),
            'confidence': trade_info['confidence'],
            'won': won,
            'payout': round(payout, 2),
            'balance': round(self.balance + payout, 2),
            'timestamp': datetime.now().isoformat()
        }

    def train_and_trade(self, cycles=5):
        all_results = []

        for cycle in range(1, cycles + 1):
            self.cycle_count += 1
            self.balance = self.initial_balance
            trades = []
            wins = 0
            losses = 0

            print(f"\n{'='*55}")
            print(f"CYCLE {cycle} | Config: edge>={self.config['min_edge']:.2f}, conf>={self.config['min_confidence']}")
            print(f"{'='*55}")

            # Run demo trades
            for i in range(1000):
                trade = self.execute_trade(random.choice(self.get_markets()))
                if trade:
                    self.balance = trade['balance']
                    trades.append(trade)
                    if trade['won']:
                        wins += 1
                    else:
                        losses += 1

                    if len(trades) >= 100:
                        break

            win_rate = wins / len(trades) * 100 if trades else 0
            profit = self.balance - self.initial_balance

            result = {
                'cycle': cycle,
                'trades': len(trades),
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1),
                'profit': round(profit, 2),
                'config': self.config.copy()
            }
            all_results.append(result)

            print(f"  Trades: {len(trades)} | Win: {win_rate:.1f}% | Losses: {losses} | Profit: ${profit:.2f}")

            # Check for third eye
            if win_rate >= self.target_win_rate and losses <= self.max_losses_per_cycle:
                print(f"\n*** THIRD EYE ACHIEVED! Win: {win_rate:.1f}%, Losses: {losses} ***")
                break

            # Learn and adjust
            if losses > wins * 0.25:
                # Too many losses - tighten
                self.config['min_edge'] = min(self.config['min_edge'] + 0.03, 0.45)
                self.config['min_confidence'] = min(self.config['min_confidence'] + 5, 90)
                self.config['max_position_pct'] = max(self.config['max_position_pct'] * 0.9, 0.08)
                print(f"  -> Tightening thresholds")
            elif win_rate > 85 and len(trades) < 30:
                # Good win rate but too few trades - relax slightly
                self.config['min_edge'] = max(self.config['min_edge'] - 0.02, 0.08)
                self.config['min_confidence'] = max(self.config['min_confidence'] - 5, 35)
                print(f"  -> Relaxing for more opportunities")

        return all_results


def run_complete_system(cycles=5, demo_trades=200):
    print("=" * 55)
    print("COMPLETE TRAINING + TRADING CYCLE")
    print("=" * 55)

    system = CompleteThirdEyeSystem()

    # Phase 1: Train until third eye
    print("\n[PHASE 1: TRAINING]")
    results = system.train_and_trade(cycles)

    # Phase 2: Run demo with final config
    print("\n[PHASE 2: DEMO TRADING]")
    print(f"Running {demo_trades} demo trades with trained config...")

    final_config = system.config
    balance = 10.0
    trades = []
    wins = 0
    losses = 0

    for i in range(demo_trades):
        trade = system.execute_trade(random.choice(system.get_markets()))
        if trade:
            balance = trade['balance']
            trades.append(trade)
            if trade['won']:
                wins += 1
            else:
                losses += 1

    win_rate = wins / len(trades) * 100 if trades else 0
    profit = balance - 10.0

    print(f"\nFinal Demo Results:")
    print(f"  Trades: {len(trades)}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Wins: {wins}, Losses: {losses}")
    print(f"  Final Balance: ${balance:.2f}")
    print(f"  Profit: ${profit:.2f} ({profit/10*100:.1f}%)")

    # Save everything
    summary = {
        'training_cycles': len(results),
        'final_config': final_config,
        'demo_trades': len(trades),
        'demo_win_rate': round(win_rate, 1),
        'demo_wins': wins,
        'demo_losses': losses,
        'final_balance': round(balance, 2),
        'profit': round(profit, 2),
        'third_eye_achieved': win_rate >= 90 and losses <= 5
    }

    with open('data/results/complete_third_eye_system.json', 'w') as f:
        json.dump(summary, f, indent=2)

    with open('data/results/third_eye_trades.csv', 'w', newline='') as f:
        if trades:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)

    print(f"\nSaved to data/results/complete_third_eye_system.json")

    return summary


if __name__ == "__main__":
    run_complete_system(5, 200)