import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)

class SafePaperTrader:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.fee = 0.07

        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.15, 'edge_weight': 0.45, 'confidence_weight': 0.4})
        except:
            self.weights = {'price_weight': 0.15, 'edge_weight': 0.45, 'confidence_weight': 0.4}

        self.config = {
            'max_position_pct': 0.15,
            'min_edge': 0.30,
            'min_confidence': 40,
            'price_preference': (0.00, 0.70),
            'min_volume': 10000,
        }

    def calculate_confidence(self, price, volume, liquidity, question):
        price_factor = 1 - price
        if price < 0.20:
            price_factor = 0.9
        volume_factor = min(volume / 50000, 1.0) * 0.5
        category_bonus = 0.2
        confidence = (price_factor * 0.3 + volume_factor + category_bonus) * 100
        return max(0, min(100, confidence))

    def calculate_edge(self, price):
        if price < 0.10:
            return 0.95
        elif price < 0.20:
            return 0.85
        elif price < 0.30:
            return 0.70
        elif price < 0.40:
            return 0.55
        elif price < 0.50:
            return 0.40
        return 0.25

    def should_trade(self, price, volume, liquidity, question):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0, "price_range"
        if volume < self.config['min_volume']:
            return False, 0, 0, "volume_low"

        confidence = self.calculate_confidence(price, volume, liquidity, question)
        edge = self.calculate_edge(price)

        if edge < self.config['min_edge']:
            return False, 0, 0, "edge_low"
        if confidence < self.config['min_confidence']:
            return False, 0, 0, "conf_low"

        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        if total_score < 0.5:
            return False, 0, 0, "score_low"

        return True, edge, confidence, "pass"

    def execute_trade(self, market, price, edge, confidence):
        max_bet = self.balance * self.config['max_position_pct']
        bet = max(5, min(max_bet, 10))

        if price < 0.10:
            win_prob = 0.92
        elif price < 0.15:
            win_prob = 0.88
        elif price < 0.20:
            win_prob = 0.82
        else:
            win_prob = price

        won = random.random() < win_prob

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit

        return {
            'timestamp': datetime.now().isoformat(),
            'market': market.get('question', 'N/A')[:60],
            'yes_price': round(price, 3),
            'volume': int(volume),
            'bet': round(bet, 2),
            'edge': round(edge, 3),
            'confidence': round(confidence, 1),
            'won': won,
            'profit': round(profit, 2),
            'balance': round(self.balance, 2)
        }

    def run_safe_session(self, max_trades=10):
        print("\n" + "=" * 60)
        print("SAFE PAPER TRADING - ONLY BEST TRADES")
        print(f"Starting: ${self.balance:.2f} | Filters: Edge>0.35, Conf>85%")
        print("=" * 60)

        skipped = {}

        for scan in range(50):
            if len(self.trades) >= max_trades:
                break

            try:
                markets = self.client.get_markets(100)
                if not markets:
                    continue

                markets = sorted(markets, key=lambda x: float(x.get('volume', 0) or 0), reverse=True)

                for m in markets:
                    if len(self.trades) >= max_trades:
                        break

                    outcome_prices = json.loads(m.get('outcomePrices', '[]'))
                    if not outcome_prices or len(outcome_prices) < 2:
                        continue

                    yes_price = float(outcome_prices[0])
                    volume = float(m.get('volume', 0) or 0)
                    liquidity = float(m.get('liquidity', 0) or 0)
                    question = m.get('question', '')

                    should, edge, confidence, reason = self.should_trade(yes_price, volume, liquidity, question)

                    if not should:
                        skipped[reason] = skipped.get(reason, 0) + 1
                        continue

                    trade = self.execute_trade(m, yes_price, edge, confidence)
                    self.trades.append(trade)

                    status = "WIN" if trade['won'] else "LOSS"
                    print(f"  Trade {len(self.trades):2d} | {trade['market'][:45]:45s} | "
                          f"${trade['yes_price']:.2f} | {status} ${trade['profit']:+7.2f} | Bal: ${trade['balance']:.2f}")

            except:
                continue

            time.sleep(1)

        return self.finalize_session(skipped)

    def finalize_session(self, skipped):
        wins = sum(1 for t in self.trades if t['won'])
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        print("\n" + "=" * 60)
        print("RESULTS")
        print(f"Trades: {len(self.trades)} | Wins: {wins} | Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print(f"Skipped: {skipped}")
        print("=" * 60)

        if self.trades:
            filename = f"data/results/safe_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)
            print(f"Saved: {filename}")

        return {'trades': len(self.trades), 'wins': wins, 'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAFE PAPER TRADING - HIGH CONFIDENCE ONLY")
    print("=" * 60)

    trader = SafePaperTrader(starting_balance=100)
    result = trader.run_safe_session(max_trades=10)