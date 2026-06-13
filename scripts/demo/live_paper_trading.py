import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)

class LivePaperTrader:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.fee = 0.07

        # Load trained model
        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {
                    'price_weight': 0.25, 'edge_weight': 0.40, 'confidence_weight': 0.35
                })
                print(f"Loaded model weights: {self.weights}")
        except:
            self.weights = {'price_weight': 0.25, 'edge_weight': 0.40, 'confidence_weight': 0.35}
            print("Using default weights")

        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.10,
            'min_confidence': 40,
            'price_preference': (0.15, 0.85),
        }

    def calculate_confidence(self, price, volume, liquidity):
        """Calculate trade confidence score"""
        price_factor = 1 - abs(0.5 - price) * 2
        volume_factor = min(volume / 100000, 1.0) * 0.4
        liquidity_factor = min(liquidity / 50000, 1.0) * 0.3
        confidence = (price_factor * 0.3 + volume_factor + liquidity_factor) * 100
        return max(0, min(100, confidence))

    def calculate_edge(self, price):
        """Calculate edge based on price deviation from 0.5"""
        edge = abs(price - 0.5) * 2
        if price < 0.5:
            edge = edge * 0.8
        return edge

    def should_trade(self, price, volume, liquidity):
        """Decide if we should trade"""
        confidence = self.calculate_confidence(price, volume, liquidity)
        edge = self.calculate_edge(price)

        # Check price preference
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0

        # Check min edge and confidence
        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return False, 0, 0

        # Calculate overall score
        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        return total_score > 0.3, edge, confidence

    def execute_trade(self, market, price, edge, confidence):
        """Execute a paper trade"""
        max_bet = self.balance * self.config['max_position_pct']
        bet = random.uniform(5, max_bet) if max_bet > 5 else max_bet

        # Simulate outcome based on price (higher price = higher prob of Yes winning)
        prob_yes = price
        won = random.random() < prob_yes

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit

        trade = {
            'timestamp': datetime.now().isoformat(),
            'market': market.get('question', 'N/A')[:60],
            'yes_price': round(price, 3),
            'bet': round(bet, 2),
            'edge': round(edge, 3),
            'confidence': round(confidence, 1),
            'won': won,
            'profit': round(profit, 2),
            'balance': round(self.balance, 2)
        }

        return trade

    def run_live_session(self, duration_minutes=30, max_trades=50):
        """Run live paper trading session"""
        print("\n" + "=" * 60)
        print("LIVE PAPER TRADING SESSION")
        print("=" * 60)
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Max Trades: {max_trades}")
        print("=" * 60)

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        iteration = 0

        while len(self.trades) < max_trades and time.time() < end_time:
            try:
                # Get live markets
                markets = self.client.get_markets(50)
                if not markets:
                    iteration += 1
                    continue

                # Shuffle for variety
                random.shuffle(markets)

                # Check each market
                for m in markets:
                    if len(self.trades) >= max_trades or time.time() >= end_time:
                        break

                    try:
                        outcome_prices = json.loads(m.get('outcomePrices', '[]'))
                        if not outcome_prices or len(outcome_prices) < 2:
                            continue

                        yes_price = float(outcome_prices[0])
                        volume = float(m.get('volume', 0) or 0)
                        liquidity = float(m.get('liquidity', 0) or 0)

                        if volume < 5000:
                            continue

                        # Check if should trade
                        should_trade, edge, confidence = self.should_trade(yes_price, volume, liquidity)

                        if should_trade:
                            trade = self.execute_trade(m, yes_price, edge, confidence)
                            self.trades.append(trade)

                            print(f"  Trade {len(self.trades):2d} | {trade['market'][:40]:40s} | "
                                  f"Price: {trade['yes_price']:.2f} | "
                                  f"{'WIN' if trade['won'] else 'LOSS':4s} | "
                                  f"Profit: ${trade['profit']:+.2f} | "
                                  f"Balance: ${trade['balance']:.2f}")

                    except Exception as e:
                        continue

                iteration += 1
                time.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                iteration += 1
                time.sleep(2)

        return self.finalize_session()

    def finalize_session(self):
        """Finalize and save session results"""
        wins = sum(1 for t in self.trades if t['won'])
        losses = len(self.trades) - wins
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        print("\n" + "=" * 60)
        print("SESSION RESULTS")
        print("=" * 60)
        print(f"Total Trades: {len(self.trades)}")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Starting Balance: ${self.initial_balance:.2f}")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f}")
        print(f"Return: {(profit / self.initial_balance) * 100:.1f}%")
        print("=" * 60)

        # Save to CSV
        if self.trades:
            filename = f"data/results/live_paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)
            print(f"Trades saved to: {filename}")

        return {
            'total_trades': len(self.trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'final_balance': round(self.balance, 2),
            'profit': round(profit, 2)
        }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("POLYMARKET LIVE PAPER TRADING")
    print("Using Trained Model Weights")
    print("=" * 60)

    trader = LivePaperTrader(starting_balance=100)
    result = trader.run_live_session(duration_minutes=30, max_trades=50)