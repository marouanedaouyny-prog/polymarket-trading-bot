"""
Enhanced Trading Bot with Notifications & Portfolio Tracking
"""

import json
import csv
import os
import time
import random
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.data.polymarket_client import PolymarketClient

os.makedirs('data/notifications', exist_ok=True)
os.makedirs('data/portfolio', exist_ok=True)

class EnhancedTradingBot:
    def __init__(self, starting_balance=100, mode='paper'):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.mode = mode
        self.trades = []
        self.fee = 0.07
        
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.65,
            'min_confidence': 65,
            'price_preference': (0.01, 0.35),
            'min_volume': 15000,
            'min_score': 0.40,
        }

        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35})
        except:
            self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

        self.stats = {'trades': 0, 'wins': 0, 'losses': 0, 'profit': 0}
        self.notifications = []

    def log(self, msg, level='INFO'):
        print(f"[{level}] {msg}")
        self.notifications.append({'time': datetime.now().isoformat(), 'level': level, 'msg': msg})

    def should_trade(self, price, volume):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0
        if volume < self.config['min_volume']:
            return False, 0, 0

        volume_factor = min(volume / self.config['min_volume'], 1.0)
        price_bonus = 0.5 if price < 0.10 else 0.4 if price < 0.20 else 0.3
        confidence = (volume_factor * 0.4 + price_bonus * 0.6) * 100

        edge = 0.95 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88 if price <= 0.10 else 0.80 if price <= 0.15 else 0.70

        if edge < self.config['min_edge'] or confidence < self.config['min_confidence']:
            return False, 0, 0

        price_score = (1 - price) * self.weights['price_weight']
        edge_score = edge * self.weights['edge_weight']
        conf_score = confidence / 100 * self.weights['confidence_weight']
        total_score = price_score + edge_score + conf_score

        if total_score < self.config['min_score']:
            return False, 0, 0

        return True, edge, confidence

    def execute_trade(self, price):
        bet = self.balance * self.config['max_position_pct']
        bet = min(max(5, bet), 25)

        win_prob = 0.96 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88 if price <= 0.10 else 0.82
        won = random.random() < win_prob

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit
        self.stats['trades'] += 1
        self.stats['profit'] += profit
        
        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1

        return won, profit

    def run(self, duration_minutes=10):
        print(f"\n{'='*60}")
        print(f"ENHANCED TRADING BOT - {self.mode.upper()}")
        print(f"Start: ${self.balance:.2f} | Duration: {duration_minutes} min")
        print(f"{'='*60}\n")

        self.log(f"Started with ${self.balance:.2f}")

        start = time.time()
        end = start + duration_minutes * 60

        while time.time() < end:
            try:
                markets = self.client.get_markets(50)
                if not markets:
                    time.sleep(2)
                    continue

                markets = sorted(markets, key=lambda x: float(x.get('volume', 0) or 0), reverse=True)

                for m in markets:
                    if time.time() >= end:
                        break
                    if self.stats['trades'] >= 300:
                        break

                    try:
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        if not prices:
                            continue

                        price = float(prices[0])
                        volume = float(m.get('volume', 0) or 0)

                        should, edge, conf = self.should_trade(price, volume)

                        if should:
                            won, profit = self.execute_trade(price)
                            
                            status = "WIN" if won else "LOSS"
                            print(f"{status} | ${price:.2f} | Bet profit: ${profit:+8.2f} | Bal: ${self.balance:,.2f}")

                            time.sleep(0.5)

                    except:
                        continue

                time.sleep(1)

            except KeyboardInterrupt:
                break
            except:
                time.sleep(2)

        return self.final_report()

    def final_report(self):
        win_rate = self.stats['wins'] / self.stats['trades'] * 100 if self.stats['trades'] > 0 else 0
        profit = self.balance - self.initial_balance

        print(f"\n{'='*60}")
        print(f"FINAL REPORT")
        print(f"{'='*60}")
        print(f"Trades: {self.stats['trades']} | Wins: {self.stats['wins']} | Loss: {self.stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print(f"{'='*60}")

        # Save portfolio
        portfolio = {
            'date': datetime.now().isoformat(),
            'trades': self.stats['trades'],
            'wins': self.stats['wins'],
            'win_rate': win_rate,
            'profit': profit,
            'balance': self.balance
        }
        with open(f'data/portfolio/portfolio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(portfolio, f, indent=2)

        self.log(f"Complete. Profit: ${profit:.2f}")

        return self.stats


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'paper'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    bot = EnhancedTradingBot(starting_balance=100, mode=mode)
    bot.run(duration_minutes=duration)
