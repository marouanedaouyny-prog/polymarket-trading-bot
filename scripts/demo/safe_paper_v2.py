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
            'max_position_pct': 0.20,
            'min_edge': 0.70,
            'min_confidence': 80,
            'price_preference': (0.01, 0.15),
            'min_volume': 50000,
            'min_score': 0.60,
        }

    def calculate_confidence(self, price, volume):
        volume_factor = min(volume / 30000, 1.0)
        if price < 0.15:
            price_bonus = 0.3
        elif price < 0.25:
            price_bonus = 0.2
        else:
            price_bonus = 0.0
        return (volume_factor * 0.5 + price_bonus) * 100

    def calculate_edge(self, price):
        if price < 0.10: return 0.90
        if price < 0.20: return 0.75
        if price < 0.30: return 0.60
        if price < 0.40: return 0.45
        if price < 0.50: return 0.35
        return 0.25

    def should_trade(self, price, volume):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0
        if volume < self.config['min_volume']:
            return False, 0, 0

        confidence = self.calculate_confidence(price, volume)
        edge = self.calculate_edge(price)

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return False, 0, 0

        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        if total_score < self.config['min_score']:
            return False, 0, 0

        return True, edge, confidence

    def execute_trade(self, market, price, edge, confidence):
        max_bet = self.balance * self.config['max_position_pct']
        bet = min(max(5, max_bet), 15)

        if price < 0.10:
            win_prob = 0.90
        elif price < 0.20:
            win_prob = 0.80
        elif price < 0.30:
            win_prob = 0.70
        else:
            win_prob = price

        won = random.random() < win_prob

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit
        
        print(f">>> EXECUTED TRADE: won={won}, bet={bet}, profit={profit}, new_balance={self.balance}")

        return {
            'timestamp': datetime.now().isoformat(),
            'market': market.get('question', 'N/A')[:50],
            'price': round(price, 3),
            'bet': round(bet, 2),
            'edge': round(edge, 2),
            'confidence': round(confidence, 1),
            'won': won,
            'profit': round(profit, 2),
            'balance': round(self.balance, 2)
        }

    def run(self, max_trades=15):
        print(f"\nSAFE TRADING | Start: ${self.balance:.2f} | Max: {max_trades} trades")
        print("=" * 60)

        scan_count = 0
        while len(self.trades) < max_trades and scan_count < 30:
            try:
                markets = self.client.get_markets(50)
                if not markets:
                    scan_count += 1
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

                        should, edge, conf = self.should_trade(price, volume)

                        if should:
                            trade = self.execute_trade(m, price, edge, conf)
                            self.trades.append(trade)
                            status = "WIN" if trade['won'] else "LOSS"
                            print(f"  {len(self.trades):2d}. {trade['market'][:40]:40s} "
                                  f"| ${price:.2f} | {status} ${trade['profit']:+6.2f} | Bal: ${trade['balance']:.2f}")
                    except:
                        continue

                scan_count += 1
                time.sleep(1)
            except:
                scan_count += 1

        return self.finish()

    def finish(self):
        wins = sum(1 for t in self.trades if t['won'])
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        print("\n" + "=" * 60)
        print(f"TRADES: {len(self.trades)} | WINS: {wins} | WIN RATE: {win_rate:.1f}%")
        print(f"BALANCE: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"PROFIT: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print("=" * 60)

        if self.trades:
            with open(f"data/results/safe_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                w.writeheader()
                w.writerows(self.trades)
            print(f"Saved to data/results/")

        return {'trades': len(self.trades), 'wins': wins, 'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    SafePaperTrader(starting_balance=100).run(max_trades=15)