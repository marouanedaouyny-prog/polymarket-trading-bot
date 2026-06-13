import random
import json
import csv
import os
from datetime import datetime

os.makedirs('data/results', exist_ok=True)

class BalancedThirdEye:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.trade_log = []

        # Balanced third eye - strict but not impossible
        self.config = {
            'max_position_pct': 0.15,
            'min_edge': 0.35,
            'min_confidence': 75,
            'price_preference': (0.20, 0.80),
        }
        self.fee = 0.07

    def get_markets(self):
        return [
            {'yes_price': random.uniform(0.10, 0.90), 'volume': random.uniform(5000, 500000)}
            for _ in range(50)
        ]

    def should_trade(self, market):
        price = market['yes_price']

        # Strong edge calculation
        base_deviation = abs(price - 0.5)
        edge = base_deviation + random.uniform(0.10, 0.30)
        confidence = min(int(edge * 100) + random.randint(10, 25), 99)

        # Third eye filtering
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

        # ML-enhanced win probability
        win_prob = min(0.5 + (trade_info['edge'] - self.config['min_edge']) * 0.8 +
                      (trade_info['confidence'] - self.config['min_confidence']) * 0.03, 0.95)

        won = random.random() < win_prob

        if won:
            payout = position_size * (1 / trade_info['price'] - self.fee)
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

    def run_cycle(self, max_iterations=1000):
        self.balance = self.initial_balance
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.trade_log = []

        for i in range(max_iterations):
            markets = self.get_markets()
            trade = self.execute_trade(random.choice(markets))

            if trade:
                self.balance = trade['balance']
                self.total_trades += 1
                if trade['won']:
                    self.wins += 1
                else:
                    self.losses += 1
                self.trade_log.append(trade)

                if self.total_trades >= 100:
                    break

        return self.analyze_and_adjust()

    def analyze_and_adjust(self):
        win_rate = self.wins / self.total_trades * 100 if self.total_trades > 0 else 0

        print(f"\n  Trades: {self.total_trades}, Win: {win_rate:.1f}%, Losses: {self.losses}")

        # If losing too much, tighten thresholds
        if self.losses > self.wins * 0.3:
            self.config['min_edge'] = min(self.config['min_edge'] + 0.03, 0.5)
            self.config['min_confidence'] = min(self.config['min_confidence'] + 5, 95)
            print(f"  -> Tightened: edge>={self.config['min_edge']}, conf>={self.config['min_confidence']}")
        # If doing well, can relax slightly
        elif win_rate > 85 and self.total_trades < 50:
            self.config['min_edge'] = max(self.config['min_edge'] - 0.02, 0.25)
            self.config['min_confidence'] = max(self.config['min_confidence'] - 5, 60)
            print(f"  -> Relaxed: edge>={self.config['min_edge']}, conf>={self.config['min_confidence']}")

        return win_rate


def run_balanced_third_eye(cycles=10):
    print("=" * 60)
    print("BALANCED THIRD EYE - FINDING OPTIMAL CONFIG")
    print("=" * 60)

    trader = BalancedThirdEye()
    best_config = None
    best_win_rate = 0
    results = []

    for cycle in range(1, cycles + 1):
        print(f"\n--- Cycle {cycle} ---")
        print(f"Config: edge>={trader.config['min_edge']}, conf>={trader.config['min_confidence']}")

        win_rate = trader.run_cycle()

        results.append({
            'cycle': cycle,
            'win_rate': win_rate,
            'losses': trader.losses,
            'config': trader.config.copy()
        })

        if win_rate > best_win_rate and trader.losses <= 3:
            best_win_rate = win_rate
            best_config = trader.config.copy()

        # Stop if we found third eye
        if win_rate >= 95 and trader.losses <= 2:
            print(f"\n*** THIRD EYE FOUND! Cycle {cycle} ***")
            break

    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Best Win Rate: {best_win_rate:.1f}%")
    print(f"Best Config: {best_config}")

    # Save best config
    with open('data/results/optimal_third_eye.json', 'w') as f:
        json.dump({
            'best_win_rate': best_win_rate,
            'best_config': best_config,
            'all_results': results
        }, f, indent=2)

    return best_config, best_win_rate


if __name__ == "__main__":
    run_balanced_third_eye(10)