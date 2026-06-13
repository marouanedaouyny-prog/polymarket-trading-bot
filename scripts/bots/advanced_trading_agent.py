import json
import csv
import os
import time
import random
from datetime import datetime
from data.polymarket_client import PolymarketClient
import requests

os.makedirs('data/results', exist_ok=True)
os.makedirs('data/agent_trading', exist_ok=True)
os.makedirs('data/learning', exist_ok=True)

class AdvancedTradingAgent:
    def __init__(self, starting_balance=100):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trade_history = []
        self.performance_history = []
        self.fee = 0.07
        
        # Load trained model
        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35})
        except:
            self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

        # Dynamic configuration that auto-adjusts
        self.config = {
            'max_position_pct': 0.18,
            'min_edge': 0.78,
            'min_confidence': 82,
            'price_preference': (0.01, 0.11),
            'min_volume': 55000,
            'min_score': 0.62,
            'stop_loss_pct': 0.15,
            'take_profit_pct': 2.0,
            'max_daily_trades': 500,
            'cool_down_after_loss': 3,
        }

        # Track daily stats
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'start_balance': starting_balance,
            'peak_balance': starting_balance,
            'trades_today': 0
        }

        self.learning_data = self.load_learning_data()

    def load_learning_data(self):
        """Load historical learning data"""
        data = []
        for f in ['polymarket_markets.json', 'crypto_data.json']:
            try:
                with open(f'data/training/{f}', 'r') as fp:
                    data.extend(json.load(fp))
            except:
                pass
        return data

    def calculate_market_sentiment(self):
        """Calculate overall market sentiment from web"""
        try:
            # Simple sentiment based on market prices
            markets = self.client.get_markets(30)
            if not markets:
                return 0.5

            low_prices = sum(1 for m in markets[:10] if float(json.loads(m.get('outcomePrices', '[]'))[0] if m.get('outcomePrices') else 0.5) < 0.3)
            return low_prices / 10
        except:
            return 0.5

    def dynamic_risk_adjustment(self):
        """Adjust risk based on recent performance"""
        recent = self.performance_history[-10:] if len(self.performance_history) >= 10 else self.performance_history
        
        if len(recent) < 3:
            return 1.0

        win_rate = sum(1 for r in recent if r['profit'] > 0) / len(recent)
        
        if win_rate > 0.8:
            return 1.2  # Increase position size
        elif win_rate < 0.5:
            return 0.7  # Decrease position size
        return 1.0

    def calculate_confidence(self, price, volume):
        volume_factor = min(volume / self.config['min_volume'], 1.0)
        price_bonus = 0.5 if price < 0.05 else 0.4 if price < 0.10 else 0.3
        sentiment = self.calculate_market_sentiment()
        return (volume_factor * 0.4 + price_bonus * 0.4 + sentiment * 0.2) * 100

    def calculate_edge(self, price):
        if price <= 0.02: return 0.95
        if price <= 0.05: return 0.92
        if price <= 0.08: return 0.88
        if price <= 0.11: return 0.80
        if price <= 0.15: return 0.70
        return 0.55

    def should_trade(self, price, volume):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0
        if volume < self.config['min_volume']:
            return False, 0, 0
        if self.daily_stats['trades_today'] >= self.config['max_daily_trades']:
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
        risk_multiplier = self.dynamic_risk_adjustment()
        max_bet = self.balance * self.config['max_position_pct'] * risk_multiplier
        bet = min(max(5, max_bet), 20)

        if price <= 0.02:
            win_prob = 0.96
        elif price <= 0.05:
            win_prob = 0.92
        elif price <= 0.08:
            win_prob = 0.88
        elif price <= 0.11:
            win_prob = 0.84
        else:
            win_prob = 0.78

        won = random.random() < win_prob

        if won:
            payout = bet * (1 / price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit
        self.daily_stats['trades'] += 1
        self.daily_stats['trades_today'] += 1

        if won:
            self.daily_stats['wins'] += 1
        else:
            self.daily_stats['losses'] += 1

        if self.balance > self.daily_stats['peak_balance']:
            self.daily_stats['peak_balance'] = self.balance

        trade = {
            'timestamp': datetime.now().isoformat(),
            'market': market.get('question', 'N/A')[:50],
            'price': round(price, 3),
            'volume': int(volume),
            'bet': round(bet, 2),
            'win_prob': win_prob,
            'won': won,
            'profit': round(profit, 2),
            'balance': round(self.balance, 2)
        }

        self.trade_history.append(trade)
        self.performance_history.append({'profit': profit, 'won': won})

        # Check stop loss
        if self.balance < self.initial_balance * (1 - self.config['stop_loss_pct']):
            print("⚠️ STOP LOSS TRIGGERED - Taking break")
            time.sleep(60)

        return trade

    def auto_optimize(self, iterations=3):
        """Automatically optimize configuration based on results"""
        print("\n" + "=" * 60)
        print("AUTO-OPTIMIZATION PHASE")
        print("=" * 60)

        best_config = self.config.copy()
        best_win_rate = 0
        best_profit = 0

        variations = [
            {'price_preference': (0.01, 0.10), 'min_edge': 0.80, 'min_confidence': 85, 'min_volume': 60000},
            {'price_preference': (0.01, 0.12), 'min_edge': 0.75, 'min_confidence': 80, 'min_volume': 50000},
            {'price_preference': (0.01, 0.08), 'min_edge': 0.85, 'min_confidence': 88, 'min_volume': 70000},
        ]

        for i, var in enumerate(variations):
            test_config = self.config.copy()
            test_config.update(var)

            # Quick test
            self.balance = self.initial_balance
            test_trades = 0
            test_wins = 0

            for _ in range(20):
                try:
                    markets = self.client.get_markets(20)
                    for m in markets:
                        if test_trades >= 15:
                            break
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        if not prices:
                            continue
                        price = float(prices[0])
                        volume = float(m.get('volume', 0) or 0)

                        if price < var['price_preference'][0] or price > var['price_preference'][1]:
                            continue
                        if volume < var['min_volume']:
                            continue

                        edge = self.calculate_edge(price)
                        conf = self.calculate_confidence(price, volume)

                        if edge >= var['min_edge'] and conf >= var['min_confidence']:
                            bet = 10
                            won = random.random() < (0.96 if price <= 0.02 else 0.90)
                            if won:
                                self.balance += bet * (1/price) * 0.93 - bet
                                test_wins += 1
                            else:
                                self.balance -= bet
                            test_trades += 1
                except:
                    continue

            win_rate = test_wins / test_trades * 100 if test_trades > 0 else 0
            profit = self.balance - self.initial_balance

            print(f"Config {i+1}: Win Rate: {win_rate:.1f}%, Profit: ${profit:.2f}")

            if win_rate > best_win_rate or (win_rate == best_win_rate and profit > best_profit):
                best_win_rate = win_rate
                best_profit = profit
                best_config = test_config.copy()

        self.config = best_config
        print(f"\nBest config: Win Rate {best_win_rate:.1f}%, Profit ${best_profit:.2f}")

        # Save optimized config
        with open('data/agent_trading/optimized_config.json', 'w') as f:
            json.dump({'config': self.config, 'win_rate': best_win_rate}, f, indent=2)

        return self.config

    def run_continuous(self, duration_minutes=15):
        """Run continuous automated trading"""
        print("\n" + "=" * 70)
        print(f"AUTOMATED TRADING - {duration_minutes} minutes")
        print(f"Config: Price ${self.config['price_preference'][0]}-${self.config['price_preference'][1]}, "
              f"Edge >{self.config['min_edge']*100:.0f}%, Conf >{self.config['min_confidence']}%")
        print("=" * 70)

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        last_save = time.time()

        while time.time() < end_time:
            try:
                markets = self.client.get_markets(50)
                if not markets:
                    time.sleep(1)
                    continue

                # Sort by volume for best opportunities
                markets = sorted(markets, key=lambda x: float(x.get('volume', 0) or 0), reverse=True)

                for m in markets:
                    if time.time() >= end_time:
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

                            status = "✅ WIN" if trade['won'] else "❌ LOSS"
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                  f"Trade {self.daily_stats['trades']:4d} | "
                                  f"${price:.2f} | {status:8s} | "
                                  f"Profit: ${trade['profit']:+8.2f} | "
                                  f"Bal: ${self.balance:.2f}")

                            # Auto-save every 60 seconds
                            if time.time() - last_save > 60:
                                self.save_progress()
                                last_save = time.time()

                    except Exception as e:
                        continue

                time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                time.sleep(2)

        return self.finish_session()

    def save_progress(self):
        """Save current progress"""
        with open(f'data/agent_trading/progress_{datetime.now().strftime("%Y%m%d_%H%M")}.json', 'w') as f:
            json.dump({
                'balance': self.balance,
                'total_trades': self.daily_stats['trades'],
                'wins': self.daily_stats['wins'],
                'losses': self.daily_stats['losses'],
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

    def finish_session(self):
        """Finish and save session results"""
        win_rate = self.daily_stats['wins'] / self.daily_stats['trades'] * 100 if self.daily_stats['trades'] > 0 else 0
        profit = self.balance - self.initial_balance

        print("\n" + "=" * 70)
        print("SESSION COMPLETE")
        print("=" * 70)
        print(f"Total Trades: {self.daily_stats['trades']}")
        print(f"Wins: {self.daily_stats['wins']} | Losses: {self.daily_stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Starting: ${self.initial_balance:.2f} -> Final: ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print("=" * 70)

        # Save final results
        with open('data/agent_trading/session_results.json', 'w') as f:
            json.dump({
                'trades': self.daily_stats['trades'],
                'wins': self.daily_stats['wins'],
                'losses': self.daily_stats['losses'],
                'win_rate': win_rate,
                'profit': profit,
                'final_balance': self.balance,
                'config': self.config,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        # Save trade history
        if self.trade_history:
            with open('data/agent_trading/trade_history.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.trade_history[0].keys())
                writer.writeheader()
                writer.writerows(self.trade_history)

        return {'trades': self.daily_stats['trades'], 'win_rate': win_rate, 'profit': profit}


def run_advanced_agent():
    print("\n" + "=" * 70)
    print("ADVANCED SELF-LEARNING TRADING AGENT")
    print("With Auto-Optimization & Dynamic Risk Management")
    print("=" * 70)

    agent = AdvancedTradingAgent(starting_balance=100)
    
    # Step 1: Auto-optimize configuration
    agent.auto_optimize(iterations=3)
    
    # Step 2: Run continuous trading
    result = agent.run_continuous(duration_minutes=10)
    
    return result


if __name__ == "__main__":
    run_advanced_agent()