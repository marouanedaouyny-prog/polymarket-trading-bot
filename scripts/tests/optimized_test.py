import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)

class OptimizedTrader:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.fee = 0.07
        self.stats = {'wins': 0, 'losses': 0}
        
        # Optimized config based on past tests
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.60,
            'min_confidence': 60,
            'price_preference': (0.01, 0.40),
            'min_volume': 15000,
            'min_score': 0.40,
        }
        
        self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

    def should_trade(self, price, volume):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0
        if volume < self.config['min_volume']:
            return False, 0

        volume_factor = min(volume / self.config['min_volume'], 1.0)
        price_bonus = 0.5 if price < 0.10 else 0.4
        confidence = (volume_factor * 0.4 + price_bonus * 0.6) * 100

        edge = 0.95 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88 if price <= 0.10 else 0.82

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return False, 0

        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        if total_score < self.config['min_score']:
            return False, 0

        return True, confidence

    def execute_trade(self, price):
        bet = self.balance * self.config['max_position_pct']
        bet = min(max(5, bet), 20)

        win_prob = 0.96 if price <= 0.02 else 0.93 if price <= 0.05 else 0.90 if price <= 0.10 else 0.85
        won = random.random() < win_prob

        if won:
            profit = bet * (1 / price) * (1 - self.fee) - bet
        else:
            profit = -bet

        self.balance += profit
        
        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1

        return won

    def run(self, max_trades=25):
        print(f"\n{'='*50}")
        print("OPTIMIZED TRADER TEST")
        print(f"{'='*50}\n")

        for i in range(50):
            if len(self.trades) >= max_trades:
                break

            markets = self.client.get_markets(30)
            if not markets:
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

                    should, conf = self.should_trade(price, volume)

                    if should:
                        won = self.execute_trade(price)
                        self.trades.append({'price': price, 'won': won})
                        
                        status = "WIN" if won else "LOSS"
                        print(f"Trade {len(self.trades):2d} | ${price:.2f} | {status} | Bal: ${self.balance:.2f}")

                except:
                    continue

            time.sleep(0.5)

        return self.finish()

    def finish(self):
        wins = self.stats['wins']
        losses = self.stats['losses']
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0
        profit = self.balance - self.initial_balance

        print(f"\n{'='*50}")
        print("RESULTS")
        print(f"{'='*50}")
        print(f"Trades: {total} | Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print(f"{'='*50}")

        return {'trades': total, 'wins': wins, 'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    OptimizedTrader(starting_balance=100).run(max_trades=25)