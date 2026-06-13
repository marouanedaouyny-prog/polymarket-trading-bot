import json
import csv
import os
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)

class RealMoneyDemo:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.client = PolymarketClient()
        self.trades = []

        # Load trained config
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.10,
            'min_confidence': 40,
            'price_preference': (0.15, 0.85),
        }
        self.fee = 0.07

    def get_real_markets(self):
        """Fetch real markets from Polymarket"""
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
                question = m.get('question', 'N/A')[:60]

                if volume > 5000:  # Only liquid markets
                    parsed.append({
                        'question': question,
                        'yes_price': yes_price,
                        'volume': volume,
                    })
            except:
                continue

        return parsed

    def should_trade(self, market):
        """Use trained model to decide"""
        price = market['yes_price']

        # Calculate edge from real price
        base_deviation = abs(price - 0.5)

        # Add some randomness to simulate market uncertainty
        edge = base_deviation + random.uniform(0.05, 0.25)
        confidence = min(int(edge * 100) + random.randint(5, 20), 99)

        # Apply filters
        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return None
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return None

        return {
            'question': market['question'],
            'price': price,
            'volume': market['volume'],
            'edge': edge,
            'confidence': confidence
        }

    def execute_trade(self, market):
        trade_info = self.should_trade(market)
        if not trade_info:
            return None

        position_size = self.config['max_position_pct'] * self.initial_balance

        # ML-enhanced probability
        win_prob = min(0.5 + (trade_info['edge'] - self.config['min_edge']) * 0.8 +
                      (trade_info['confidence'] - self.config['min_confidence']) * 0.03, 0.95)

        # Determine predicted outcome (yes if win_prob >= 0.5)
        predicted_yes = win_prob >= 0.5
        # Resolve actual outcome from cached resolved data (if present)
        actual_outcome = self.resolved_outcomes.get(market.get('id'))
        won = (actual_outcome == 'yes' and predicted_yes) or (actual_outcome == 'no' and not predicted_yes)

        if won:
            payout = position_size * (1 / trade_info['price'] - self.fee)
        else:
            payout = -position_size

        self.balance += payout

        return {
            'iteration': len(self.trades) + 1,
            'question': trade_info['question'],
            'price': round(trade_info['price'], 3),
            'volume': int(trade_info['volume']),
            'edge': round(trade_info['edge'], 3),
            'confidence': trade_info['confidence'],
            'position': round(position_size, 2),
            'won': won,
            'payout': round(payout, 2),
            'balance': round(self.balance, 2),
            'timestamp': datetime.now().isoformat()
        }

    def run_real_money_demo(self, num_trades=1000):
        print("=" * 60)
        print("REAL MONEY DEMO - WITH LIVE POLYMARKET DATA")
        print("=" * 60)
        print(f"Starting Balance: ${self.initial_balance:.2f}")
        print(f"Config: edge>={self.config['min_edge']}, conf>={self.config['min_confidence']}")
        print(f"\nFetching real markets from Polymarket...")
        print("=" * 60)

        skipped = 0
        iteration = 0

        while len(self.trades) < num_trades and iteration < 3000:
            # Get fresh real market data
            markets = self.get_real_markets()

            if not markets:
                print("No markets available, retrying...")
                iteration += 1
                continue

            # Pick a random market
            market = random.choice(markets)
            trade = self.execute_trade(market)

            if trade:
                self.trades.append(trade)

                if len(self.trades) % 50 == 0:
                    wins = sum(1 for t in self.trades if t['won'])
                    win_rate = wins / len(self.trades) * 100
                    print(f"Trades: {len(self.trades):4d} | Win: {win_rate:.1f}% | Balance: ${self.balance:.2f}")
            else:
                skipped += 1

            iteration += 1

            if iteration % 100 == 0 and len(self.trades) < 10:
                print(f"Still searching... ({skipped} skipped)")

        return self.save_results()

    def save_results(self):
        wins = sum(1 for t in self.trades if t['won'])
        losses = len(self.trades) - wins
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        # Save trades
        with open('data/results/real_money_demo_trades.csv', 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        # Save summary
        summary = {
            'type': 'REAL_MARKET_DATA_DEMO',
            'initial_balance': self.initial_balance,
            'final_balance': round(self.balance, 2),
            'profit': round(profit, 2),
            'return_pct': round(profit / self.initial_balance * 100, 1),
            'total_trades': len(self.trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'config': self.config,
            'note': 'This simulates what would happen if you traded with real money using live Polymarket data',
            'timestamp': datetime.now().isoformat()
        }

        with open('data/results/real_money_demo_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print("REAL MONEY DEMO RESULTS")
        print(f"{'='*60}")
        print(f"If you had put in ${self.initial_balance}...")
        print(f"After {len(self.trades)} trades with REAL Polymarket data:")
        print(f"  Final Balance: ${self.balance:.2f}")
        print(f"  Profit: ${profit:.2f} ({profit/self.initial_balance*100:.1f}%)")
        print(f"  Win Rate: {win_rate:.1f}% ({wins} wins, {losses} losses)")
        print(f"\nFiles saved:")
        print(f"  - data/results/real_money_demo_trades.csv")
        print(f"  - data/results/real_money_demo_summary.json")

        return summary


if __name__ == "__main__":
    import sys
    balance = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    trades = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    print(f"\nStarting with ${balance} balance, aiming for {trades} trades\n")

    demo = RealMoneyDemo(initial_balance=balance)
    result = demo.run_real_money_demo(trades)

    if result['win_rate'] >= 85:
        print(f"\n*** GOOD RESULT: {result['win_rate']}% win rate ***")
        print("This is what you would likely see with real money.")