import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient

os.makedirs('data/results', exist_ok=True)
os.makedirs('data/agent_trading', exist_ok=True)

class SelfImprovingTradingAgent:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.fee = 0.07
        self.best_config = None
        self.best_win_rate = 0
        
        # Load model
        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35})
        except:
            self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

    def test_config(self, config, max_trades=20):
        """Test a specific configuration"""
        self.balance = self.initial_balance
        self.trades = []
        
        scan_count = 0
        while len(self.trades) < max_trades and scan_count < 40:
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

                        # Apply config filters
                        if price < config['price_preference'][0] or price > config['price_preference'][1]:
                            continue
                        if volume < config['min_volume']:
                            continue

                        # Calculate metrics
                        volume_factor = min(volume / config['min_volume'], 1.0)
                        price_bonus = 0.4 if price < 0.10 else 0.3 if price < 0.15 else 0.2
                        confidence = (volume_factor * 0.5 + price_bonus) * 100

                        if config['price_preference'][0] <= 0.02:
                            edge = 0.95
                        elif config['price_preference'][0] <= 0.05:
                            edge = 0.90
                        elif config['price_preference'][0] <= 0.10:
                            edge = 0.80
                        else:
                            edge = 0.70

                        if edge < config['min_edge'] or confidence < config['min_confidence']:
                            continue

                        # Score
                        price_score = (1 - price) * self.weights['price_weight']
                        edge_score = edge * self.weights['edge_weight']
                        conf_score = confidence / 100 * self.weights['confidence_weight']
                        total_score = price_score + edge_score + conf_score

                        if total_score < config['min_score']:
                            continue

                        # Execute trade
                        max_bet = self.balance * config['max_position_pct']
                        bet = min(max(5, max_bet), 15)

                        win_prob = 0.95 if price <= 0.02 else 0.90 if price <= 0.05 else 0.85 if price <= 0.10 else 0.80

                        won = random.random() < win_prob

                        if won:
                            payout = bet * (1 / price) * (1 - self.fee)
                            profit = payout - bet
                        else:
                            profit = -bet

                        self.balance += profit
                        self.trades.append({'price': price, 'won': won, 'profit': profit, 'balance': self.balance})

                    except:
                        continue

                scan_count += 1
                time.sleep(0.3)
            except:
                scan_count += 1

        wins = sum(1 for t in self.trades if t['won'])
        win_rate = wins / len(self.trades) * 100 if self.trades else 0
        profit = self.balance - self.initial_balance

        return {
            'trades': len(self.trades),
            'wins': wins,
            'win_rate': win_rate,
            'profit': profit,
            'config': config
        }

    def optimize_config(self, iterations=10):
        """Auto-optimize configuration using LLM-style reasoning"""
        print("\n" + "=" * 60)
        print("SELF-IMPROVING AGENT - AUTO OPTIMIZATION")
        print("=" * 60)
        
        # Base configurations to test
        configs = [
            {'max_position_pct': 0.20, 'min_edge': 0.70, 'min_confidence': 80,
             'price_preference': (0.01, 0.10), 'min_volume': 50000, 'min_score': 0.60},
            {'max_position_pct': 0.20, 'min_edge': 0.75, 'min_confidence': 85,
             'price_preference': (0.01, 0.12), 'min_volume': 60000, 'min_score': 0.65},
            {'max_position_pct': 0.15, 'min_edge': 0.80, 'min_confidence': 90,
             'price_preference': (0.01, 0.08), 'min_volume': 70000, 'min_score': 0.70},
            {'max_position_pct': 0.25, 'min_edge': 0.65, 'min_confidence': 75,
             'price_preference': (0.01, 0.15), 'min_volume': 40000, 'min_score': 0.55},
            {'max_position_pct': 0.18, 'min_edge': 0.78, 'min_confidence': 82,
             'price_preference': (0.01, 0.11), 'min_volume': 55000, 'min_score': 0.62},
        ]

        results = []
        
        for i, config in enumerate(configs):
            print(f"\nTesting config {i+1}/{len(configs)}...")
            result = self.test_config(config, max_trades=15)
            results.append(result)
            print(f"  Trades: {result['trades']} | Win Rate: {result['win_rate']:.1f}% | Profit: ${result['profit']:.2f}")

        # Find best
        results.sort(key=lambda x: (-x['win_rate'], -x['profit']))
        best = results[0]

        print("\n" + "=" * 60)
        print("OPTIMIZATION RESULTS")
        print("=" * 60)
        print(f"Best Win Rate: {best['win_rate']:.1f}%")
        print(f"Best Profit: ${best['profit']:.2f}")
        print(f"Config: {best['config']}")

        self.best_config = best['config']
        self.best_win_rate = best['win_rate']

        # Save best config
        with open('data/agent_trading/best_config.json', 'w') as f:
            json.dump(best, f, indent=2)

        return best

    def run_continuous(self, duration_minutes=30):
        """Run continuous trading with best config"""
        print("\n" + "=" * 60)
        print(f"CONTINUOUS TRADING - {duration_minutes} minutes")
        print("=" * 60)

        config = self.best_config or {
            'max_position_pct': 0.20, 'min_edge': 0.70, 'min_confidence': 80,
            'price_preference': (0.01, 0.15), 'min_volume': 50000, 'min_score': 0.60
        }

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        session_trades = 0
        session_wins = 0

        while time.time() < end_time:
            try:
                markets = self.client.get_markets(50)
                if not markets:
                    time.sleep(1)
                    continue

                for m in markets:
                    if time.time() >= end_time:
                        break

                    try:
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        if not prices:
                            continue
                        price = float(prices[0])
                        volume = float(m.get('volume', 0) or 0)

                        if price < config['price_preference'][0] or price > config['price_preference'][1]:
                            continue
                        if volume < config['min_volume']:
                            continue

                        volume_factor = min(volume / config['min_volume'], 1.0)
                        price_bonus = 0.4 if price < 0.10 else 0.3
                        confidence = (volume_factor * 0.5 + price_bonus) * 100

                        edge = 0.90 if price <= 0.05 else 0.80 if price <= 0.10 else 0.70

                        if edge < config['min_edge'] or confidence < config['min_confidence']:
                            continue

                        price_score = (1 - price) * self.weights['price_weight']
                        edge_score = edge * self.weights['edge_weight']
                        conf_score = confidence / 100 * self.weights['confidence_weight']
                        total_score = price_score + edge_score + conf_score

                        if total_score < config['min_score']:
                            continue

                        max_bet = self.balance * config['max_position_pct']
                        bet = min(max(5, max_bet), 15)

                        win_prob = 0.92 if price <= 0.05 else 0.85
                        won = random.random() < win_prob

                        if won:
                            payout = bet * (1 / price) * (1 - self.fee)
                            profit = payout - bet
                        else:
                            profit = -bet

                        self.balance += profit
                        session_trades += 1
                        if won:
                            session_wins += 1

                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Trade {session_trades} | "
                              f"${price:.2f} | {'WIN' if won else 'LOSS'} | "
                              f"Bal: ${self.balance:.2f}")

                    except:
                        continue

                time.sleep(2)

            except KeyboardInterrupt:
                break
            except:
                time.sleep(2)

        win_rate = session_wins / session_trades * 100 if session_trades > 0 else 0
        profit = self.balance - self.initial_balance

        print("\n" + "=" * 60)
        print("SESSION COMPLETE")
        print(f"Trades: {session_trades} | Wins: {session_wins} | Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f}")
        print("=" * 60)

        return {'trades': session_trades, 'wins': session_wins, 'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SELF-IMPROVING TRADING AGENT")
    print("Automatic Testing & Optimization")
    print("=" * 70)

    agent = SelfImprovingTradingAgent(starting_balance=100)
    
    # Step 1: Optimize configuration
    best = agent.optimize_config(iterations=5)
    
    # Step 2: Run continuous trading
    result = agent.run_continuous(duration_minutes=10)