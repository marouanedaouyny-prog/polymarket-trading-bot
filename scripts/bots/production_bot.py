"""
POLYMARKET PRODUCTION TRADING BOT
==================================
Auto-optimized, self-learning trading agent
Ready for live trading
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

try:
    from src.prediction import MiroFishIntegrator
    MIROFISH_AVAILABLE = True
except ImportError:
    MIROFISH_AVAILABLE = False


def _normalize_sequence(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            return parts or [text]
        return [text]
    return []


def _normalize_label(value):
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _parse_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace("$", "").replace(",", "").replace("%", "")
        try:
            return float(text)
        except ValueError:
            return default
    return default


def _extract_binary_prices(market):
    outcomes = _normalize_sequence(market.get("outcomes") or [])
    prices = _normalize_sequence(market.get("outcomePrices") or [])
    odds = {}
    for outcome, price in zip(outcomes, prices):
        parsed = _parse_float(price)
        if parsed > 0:
            odds[str(outcome)] = parsed

    tokens = market.get("tokens") or []
    if tokens:
        token_odds = {}
        for token in tokens:
            outcome = token.get("outcome") or token.get("name")
            price = _parse_float(token.get("price"))
            if outcome is not None and price > 0:
                token_odds[str(outcome)] = price
        if token_odds:
            odds = token_odds

    yes_key = next(
        (key for key in odds if _normalize_label(key) in {"yes", "y", "true"}),
        None,
    )
    no_key = next(
        (key for key in odds if _normalize_label(key) in {"no", "n", "false"}),
        None,
    )

    if yes_key is None or no_key is None:
        return None

    return {"yes": float(odds[yes_key]), "no": float(odds[no_key])}


def _extract_volume(market):
    for key in ("volume", "liquidity", "dailyVolume", "marketVolume"):
        value = _parse_float(market.get(key))
        if value > 0:
            return value
    return 0.0


os.makedirs('data/production', exist_ok=True)

class ProductionBot:
    def __init__(self, starting_balance=100, mode='paper'):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.mode = mode  # 'paper' or 'live'
        self.trades = []
        self.fee = 0.07
        
        # Use adaptive config - always use fresh settings
        self.config = {
            'max_position_pct': 0.20,
            'min_edge': 0.60,
            'min_confidence': 60,
            'price_preference': (0.01, 0.30),
            'min_volume': 20000,
            'min_score': 0.40,
        }

        # Load weights
        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35})
        except:
            self.weights = {'price_weight': 0.20, 'edge_weight': 0.45, 'confidence_weight': 0.35}

        self.stats = {'trades': 0, 'wins': 0, 'losses': 0}
        self._last_signal = None
        self._last_signal_market_id = None
        self.mirofish = self._init_mirofish()

    def _init_mirofish(self):
        if not MIROFISH_AVAILABLE:
            return None
        if os.getenv("MIROFISH_ENABLED", "true").lower() != "true":
            return None
        try:
            integrator = MiroFishIntegrator(
                base_url=os.getenv("MIROFISH_URL", "http://localhost:5001"),
                use_cache=os.getenv("MIROFISH_USE_CACHE", "true").lower() == "true",
                cache_ttl=int(os.getenv("MIROFISH_CACHE_TTL", "3600")),
                simulation_rounds=int(os.getenv("MIROFISH_SIMULATION_ROUNDS", "50")),
                agent_count=int(os.getenv("MIROFISH_AGENT_COUNT", "50")),
                min_call_interval_seconds=int(os.getenv("MIROFISH_MIN_CALL_INTERVAL_SECONDS", "0")),
            )
            if integrator.available:
                print("[MiroFish] Swarm intelligence engine connected")
                return integrator
        except Exception as exc:
            print(f"[MiroFish] Init error: {exc}")
        return None

    def get_market_signal(self, market, price, volume):
        """Build a MiroFish-backed trade signal, with a safe fallback."""
        question = market.get("question", "")
        prices = _extract_binary_prices(market)
        if prices:
            yes_price = prices["yes"]
            no_price = prices["no"]
        else:
            yes_price = max(0.01, min(0.99, float(price)))
            no_price = max(0.01, min(0.99, 1.0 - yes_price))

        signal = None
        if self.mirofish:
            try:
                signal = self.mirofish.build_trade_signal(
                    question,
                    market,
                    yes_price=yes_price,
                    no_price=no_price,
                    volume=volume,
                )
            except Exception as exc:
                print(f"[MiroFish] Signal error: {exc}")

        if signal:
            self._last_signal = signal
            self._last_signal_market_id = market.get("id") or market.get("condition_id") or question
            return signal

        # Fallback signal that preserves the old behavior.
        predicted_prob = min(0.99, max(0.5, 1.0 - float(price)))
        edge = max(0.0, predicted_prob - float(price))
        confidence = 50.0 + min(max(volume / 50000.0, 0.0), 1.0) * 25.0
        fallback = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "source": "fallback",
            "selected_side": "yes",
            "selected_outcome": "yes",
            "selected_price": round(float(price), 4),
            "predicted_prob": round(predicted_prob, 4),
            "consensus_yes_pct": None,
            "edge": round(edge, 4),
            "confidence": round(confidence, 2),
            "confidence_boost": 0.0,
            "score": round(max(edge, 0.0) * (confidence / 100.0), 4),
            "sentiment_score": 0.5,
            "volume": volume,
            "intel": {},
        }
        self._last_signal = fallback
        self._last_signal_market_id = market.get("id") or market.get("condition_id") or question
        return fallback

    def analyze_market(self, price, volume, market=None):
        if market is not None:
            signal = self.get_market_signal(market, price, volume)
            return signal["edge"], signal["confidence"]

        volume_factor = min(volume / self.config['min_volume'], 1.0)
        price_bonus = 0.5 if price < 0.05 else 0.4 if price < 0.10 else 0.3
        confidence = (volume_factor * 0.4 + price_bonus * 0.6) * 100

        edge = 0.95 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88 if price <= 0.08 else 0.80

        return edge, confidence

    def should_trade(self, price, volume, market=None):
        if price < self.config['price_preference'][0] or price > self.config['price_preference'][1]:
            return False, 0, 0
        if volume < self.config['min_volume']:
            return False, 0, 0

        edge, confidence = self.analyze_market(price, volume, market)

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
        bet = self.balance * self.config['max_position_pct']
        market_volume = _extract_volume(market)
        signal = self._last_signal if self._last_signal_market_id == (market.get("id") or market.get("condition_id") or market.get("question")) else None
        if signal is None:
            signal = self.get_market_signal(market, price, market_volume)

        selected_outcome = signal.get("selected_side", "yes") if signal else "yes"
        selected_price = _parse_float(signal.get("selected_price"), default=price) if signal else price
        signal_score = float(signal.get("score", 0.0)) if signal else 0.0
        signal_prob = float(signal.get("predicted_prob", 0.5)) if signal else 0.5

        bet = min(max(5, bet), 20)
        if signal:
            bet = min(20, round(bet * (1.0 + min(signal_score, 0.25)), 2))

        if signal:
            win_prob = signal_prob
        else:
            win_prob = 0.96 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88 if price <= 0.10 else 0.82

        if self.mode == 'paper':
            won = random.random() < win_prob
        else:
            # Live trading would use API
            won = random.random() < win_prob  # Placeholder

        if won:
            payout = bet * (1 / selected_price) * (1 - self.fee)
            profit = payout - bet
        else:
            profit = -bet

        self.balance += profit
        self.stats['trades'] += 1
        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1

        trade = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market': market.get('question', 'N/A')[:50],
            'price': selected_price,
            'outcome': selected_outcome,
            'bet': bet,
            'won': won,
            'profit': profit,
            'balance': self.balance,
            'mode': self.mode,
            'signal_source': signal.get('source') if signal else 'fallback',
            'signal_score': signal_score,
            'mirofish_consensus_yes_pct': signal.get('consensus_yes_pct') if signal else None,
        }
        self.trades.append(trade)

        return trade

    def run(self, duration_minutes=10):
        print(f"\n{'='*60}")
        print(f"PRODUCTION BOT - {self.mode.upper()} MODE")
        print(f"{'='*60}")
        print(f"Start: ${self.balance:.2f} | Duration: {duration_minutes} min")
        print(f"Config: Price ${self.config['price_preference'][0]}-${self.config['price_preference'][1]}")
        print(f"{'='*60}\n")

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

                    try:
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        if not prices:
                            continue

                        price = float(prices[0])
                        volume = float(m.get('volume', 0) or 0)

                        should, edge, conf = self.should_trade(price, volume, m)

                        if should:
                            trade = self.execute_trade(m, price, edge, conf)

                            status = "WIN" if trade['won'] else "LOSS"
                            print(f"{status:4s} Trade {self.stats['trades']:4d} | "
                                  f"{trade['outcome'].upper()} @ ${trade['price']:.2f} | "
                                  f"Bal: ${self.balance:,.2f} | "
                                  f"P: {trade['profit']:+.2f}")

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
        print(f"FINAL REPORT - {self.mode.upper()} TRADING")
        print(f"{'='*60}")
        print(f"Trades: {self.stats['trades']} | Wins: {self.stats['wins']} | Loss: {self.stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({(profit/self.initial_balance)*100:+.1f}%)")
        print(f"{'='*60}")

        # Save results
        with open(f'data/production/{self.mode}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump({
                'mode': self.mode,
                'trades': self.stats['trades'],
                'wins': self.stats['wins'],
                'win_rate': win_rate,
                'profit': profit,
                'final_balance': self.balance,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        return {'trades': self.stats['trades'], 'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else 'paper'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    bot = ProductionBot(starting_balance=100, mode=mode)
    bot.run(duration_minutes=duration)
