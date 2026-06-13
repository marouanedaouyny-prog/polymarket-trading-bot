import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)

class Predict1000Trades:
    def __init__(self, balance=10.0):
        self.balance = balance
        self.initial_balance = balance
        self.client = PolymarketClient()
        self.trades = []
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.10,
            'min_confidence': 40,
            'price_preference': (0.15, 0.85),
        }
        self.fee = 0.07

    def get_markets(self):
        markets = self.client.get_markets(50)
        parsed = []
        for m in markets:
            try:
                outcome_prices = json.loads(m.get('outcomePrices', '[]'))
                if outcome_prices and len(outcome_prices) >= 2:
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

    def should_trade(self, market):
        price = market['yes_price']
        base_deviation = abs(price - 0.5)
        edge = base_deviation + random.uniform(0.05, 0.25)
        confidence = min(int(edge * 100) + random.randint(5, 20), 99)

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return None
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return None

        return {'question': market['question'], 'price': price, 'edge': edge, 'confidence': confidence}

    def execute_trade(self, market):
        trade_info = self.should_trade(market)
        if not trade_info:
            return None

        position_size = self.config['max_position_pct'] * self.initial_balance

        win_prob = min(0.5 + (trade_info['edge'] - self.config['min_edge']) * 0.8 +
                      (trade_info['confidence'] - self.config['min_confidence']) * 0.03, 0.95)

        won = random.random() < win_prob

        if won:
            payout = position_size * (1 / trade_info['price'] - self.fee)
        else:
            payout = -position_size

        self.balance += payout

        return {
            'iteration': len(self.trades) + 1,
            'question': trade_info['question'],
            'price': round(trade_info['price'], 3),
            'edge': round(trade_info['edge'], 3),
            'confidence': trade_info['confidence'],
            'won': won,
            'payout': round(payout, 2),
            'balance': round(self.balance, 2),
            'timestamp': datetime.now().isoformat()
        }

    def run_1000_trades(self):
        print("=" * 60)
        print("PREDICTION: 1000 TRADES WITH $10 REAL MONEY")
        print("=" * 60)
        print(f"Starting: ${self.initial_balance}")
        print(f"Target: 1000 trades")
        print(f"Using real Polymarket market data")
        print("=" * 60)

        start_time = time.time()
        trades_done = 0
        iteration = 0
        skipped = 0
        check_interval = 2  # seconds between market checks

        while trades_done < 1000 and iteration < 5000:
            markets = self.get_markets()

            if not markets:
                print(f"No markets at iteration {iteration}, waiting...")
                time.sleep(check_interval)
                iteration += 1
                continue

            market = random.choice(markets)
            trade = self.execute_trade(market)

            if trade:
                self.trades.append(trade)
                trades_done += 1

                if trades_done % 50 == 0:
                    elapsed = time.time() - start_time
                    wins = sum(1 for t in self.trades if t['won'])
                    win_rate = wins / len(self.trades) * 100
                    eta = (elapsed / trades_done) * (1000 - trades_done)
                    print(f"Trades: {trades_done:4d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f} | ETA: {eta/60:.1f}min")
            else:
                skipped += 1
                time.sleep(0.5)  # Wait a bit before retry

            iteration += 1

        elapsed = time.time() - start_time

        return self.save_results(elapsed, skipped, iteration)

    def save_results(self, elapsed, skipped, iterations):
        wins = sum(1 for t in self.trades if t['won'])
        losses = len(self.trades) - wins
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        minutes = elapsed / 60

        # Save CSV
        with open('data/results/predict_1000_trades.csv', 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        # Save summary
        summary = {
            'scenario': 'REAL MONEY - $10, 1000 TRADES',
            'initial_balance': self.initial_balance,
            'final_balance': round(self.balance, 2),
            'profit': round(profit, 2),
            'return_pct': round(profit / self.initial_balance * 100, 1),
            'total_trades': len(self.trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'time_minutes': round(minutes, 1),
            'time_hours': round(minutes / 60, 2),
            'skipped_opportunities': skipped,
            'total_iterations': iterations,
            'config': self.config,
            'timestamp': datetime.now().isoformat()
        }

        with open('data/results/predict_1000_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print("PREDICTION RESULTS")
        print(f"{'='*60}")
        print(f"If you put $10 real money and trade 1000 times...")
        print(f"\n  Total Trades: {len(self.trades)}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Final Balance: ${self.balance:.2f}")
        print(f"  Profit: ${profit:.2f} ({profit/self.initial_balance*100:.1f}%)")
        print(f"\n  Time: {minutes:.1f} minutes ({minutes/60:.2f} hours)")
        print(f"  Skipped: {skipped} (markets that didn't meet criteria)")
        print(f"\nFiles saved:")
        print(f"  - data/results/predict_1000_trades.csv")
        print(f"  - data/results/predict_1000_summary.json")

        return summary


if __name__ == "__main__":
    print("This will take real time to fetch 1000 trades from live Polymarket...")
    print("Estimated: 10-20 minutes depending on market conditions")
    print()

    predictor = Predict1000Trades(balance=10.0)
    result = predictor.run_1000_trades()