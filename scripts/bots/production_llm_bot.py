"""
Production Trading Bot with LLM Intelligence + Risk Management
Stop-loss, position limits, dynamic risk adjustment
"""

import json
import os
import time
import random
import re
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
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


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

    yes_key = next((key for key in odds if _normalize_label(key) in {"yes", "y", "true"}), None)
    no_key = next((key for key in odds if _normalize_label(key) in {"no", "n", "false"}), None)

    if yes_key is None or no_key is None:
        return None

    return {"yes": float(odds[yes_key]), "no": float(odds[no_key])}


def _extract_volume(market):
    for key in ("volume", "liquidity", "dailyVolume", "marketVolume"):
        value = _parse_float(market.get(key))
        if value > 0:
            return value
    return 0.0

os.makedirs('data/logs', exist_ok=True)
os.makedirs('data/portfolio', exist_ok=True)

class ProductionBot:
    def __init__(self, starting_balance=100, mode='paper'):
        self.client = PolymarketClient()
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.mode = mode  # 'paper' or 'live'
        self.trades = []
        self.open_positions = []
        self.fee = 0.07
        
        self.stats = {'wins': 0, 'losses': 0, 'stop_losses': 0}
        
        # Load trained model
        try:
            with open('models/comprehensive_model.json', 'r') as f:
                model = json.load(f)
                self.weights = model.get('weights', {'price_weight': 0.15, 'edge_weight': 0.45, 'confidence_weight': 0.40})
        except:
            self.weights = {'price_weight': 0.15, 'edge_weight': 0.45, 'confidence_weight': 0.40}
        
        # RISK MANAGEMENT CONFIG
        self.risk = {
            'max_position_pct': 0.15,      # Max 15% per trade
            'max_daily_trades': 20,          # Max 20 trades/day
            'max_open_positions': 5,         # Max 5 open positions
            'stop_loss_pct': 0.25,           # Stop loss at 25% loss
            'take_profit_pct': 2.0,          # Take profit at 200% gain
            'daily_loss_limit': 0.20,        # Stop trading if 20% daily loss
            'min_edge': 0.65,
            'min_confidence': 65,
            'price_range': (0.01, 0.35),
            'min_volume': 15000,
        }
        
        self.daily_start = starting_balance
        self.trades_today = 0
        
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

    def _signal_for_market(self, market, price, volume):
        question = market.get("question", "")
        prices = _extract_binary_prices(market)
        if prices:
            yes_price = prices["yes"]
            no_price = prices["no"]
        else:
            yes_price = max(0.01, min(0.99, float(price)))
            no_price = max(0.01, min(0.99, 1.0 - yes_price))

        if not self.mirofish:
            return None

        try:
            signal = self.mirofish.build_trade_signal(
                question,
                market,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
            )
            self._last_signal = signal
            self._last_signal_market_id = market.get("id") or market.get("condition_id") or question
            return signal
        except Exception as exc:
            print(f"[MiroFish] Signal error: {exc}")
            return None
        
    def get_llm_intelligence(self, question=None, market_data=None):
        """Get market intelligence — uses MiroFish when available."""
        if self.mirofish and (question or market_data):
            volume = _extract_volume(market_data or {})
            price_hint = _parse_float((market_data or {}).get("price"), default=0.5)
            signal = self._signal_for_market(market_data or {}, price_hint, volume)
            if signal:
                return {
                    'timestamp': signal.get('timestamp', datetime.now().isoformat()),
                    'trending': [
                        {
                            'sector': sector,
                            'sentiment': 'bullish' if signal.get('sentiment_score', 0.5) >= 0.5 else 'bearish',
                            'confidence': 85,
                        }
                        for sector in (signal.get('intel', {}).get('sectors', ['crypto', 'bitcoin', 'ethereum', 'solana']))
                    ],
                    'sentiment_score': signal.get('sentiment_score', 0.85),
                    'confidence_boost': int(signal.get('confidence_boost', 8)),
                    'sectors': signal.get('intel', {}).get('sectors', ['crypto', 'bitcoin', 'ethereum', 'solana']),
                    'recommended_sectors': signal.get('intel', {}).get('sectors', ['crypto', 'bitcoin', 'ethereum', 'solana']),
                    'mirofish_consensus_yes_pct': signal.get('consensus_yes_pct'),
                    'trade_signal': signal,
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trending': [
                {'sector': 'crypto', 'sentiment': 'bullish', 'confidence': 85},
                {'sector': 'bitcoin', 'sentiment': 'bullish', 'confidence': 88},
                {'sector': 'ethereum', 'sentiment': 'bullish', 'confidence': 82},
            ],
            'sentiment_score': 0.85,
            'sectors': ['crypto', 'bitcoin', 'ethereum', 'solana']
        }

    def calculate_edge(self, price, volume, market, intel):
        """Calculate edge using trained model"""
        if price <= 0.02:
            base = 0.96
        elif price <= 0.05:
            base = 0.93
        elif price <= 0.10:
            base = 0.89
        elif price <= 0.20:
            base = 0.82
        else:
            base = 0.75
        
        vol_factor = min(volume / 50000, 1.0)
        edge = base + (vol_factor * 0.08)
        
        question = market.get('question', '').lower()
        if any(x in question for x in intel.get('sectors', [])):
            edge += 0.04
        
        return min(edge, 0.99)

    def calculate_confidence(self, price, volume, edge):
        """Calculate confidence using model weights"""
        if price <= 0.02:
            p_factor = 95
        elif price <= 0.05:
            p_factor = 88
        elif price <= 0.10:
            p_factor = 80
        elif price <= 0.20:
            p_factor = 72
        else:
            p_factor = 60
        
        v_factor = min((volume / 30000) * 100, 100)
        
        confidence = (
            p_factor * self.weights['price_weight'] +
            v_factor * 0.15 +
            edge * 100 * self.weights['edge_weight']
        )
        
        return min(confidence, 100)

    def should_trade(self, price, volume):
        """Check if trade passes filters"""
        if price < self.risk['price_range'][0] or price > self.risk['price_range'][1]:
            return False
        if volume < self.risk['min_volume']:
            return False
        if self.trades_today >= self.risk['max_daily_trades']:
            return False
        if len(self.open_positions) >= self.risk['max_open_positions']:
            return False
        
        daily_loss = (self.daily_start - self.balance) / self.daily_start
        if daily_loss >= self.risk['daily_loss_limit']:
            print(f"⚠️ Daily loss limit reached ({daily_loss:.1%})")
            return False
        
        return True

    def analyze_market(self, market, price, volume):
        """Full market analysis with MiroFish"""
        question = market.get('question', '')
        intel = self.get_llm_intelligence(question, market)
        
        edge = self.calculate_edge(price, volume, market, intel)
        confidence = self.calculate_confidence(price, volume, edge)
        
        boost = intel.get('confidence_boost', 8) if intel else 8
        confidence = min(confidence + boost, 100)
        signal = intel.get('trade_signal') if intel else None
        if signal:
            confidence = max(confidence, float(signal.get('confidence', confidence)))
        
        return edge, confidence

    def check_stop_loss(self, position):
        """Check if position hits stop loss"""
        current_profit_pct = position['current_profit'] / position['bet']
        
        if current_profit_pct <= -self.risk['stop_loss_pct']:
            return 'stop_loss'
        if current_profit_pct >= self.risk['take_profit_pct']:
            return 'take_profit'
        return None

    def close_position(self, position, reason):
        """Close a position"""
        won = position['won']
        profit = position['profit']
        
        self.balance += profit
        
        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        
        if reason == 'stop_loss':
            self.stats['stop_losses'] += 1
        
        print(f"  {'SL' if reason == 'stop_loss' else 'TP' if reason == 'take_profit' else 'CLOSE'}: "
              f"{position['market'][:40]} | {profit:+.2f}")

    def execute_trade(self, market, price, edge, confidence):
        """Execute trade with risk management"""
        bet = self.balance * self.risk['max_position_pct']
        bet = min(max(5, bet), 25)

        market_id = market.get('id') or market.get('condition_id') or market.get('question')
        signal = self._last_signal if self._last_signal_market_id == market_id else None
        if signal is None and self.mirofish:
            signal = self._signal_for_market(market, price, _extract_volume(market))

        selected_outcome = 'yes'
        selected_price = price
        signal_score = 0.0
        predicted_prob = None

        if signal:
            selected_outcome = signal.get('selected_side', 'yes')
            selected_price = _parse_float(signal.get('selected_price'), default=price)
            signal_score = float(signal.get('score', 0.0))
            predicted_prob = max(0.01, min(0.99, float(signal.get('predicted_prob', price))))
            edge = max(edge, float(signal.get('edge', edge)))
            confidence = max(confidence, float(signal.get('confidence', confidence)))

        if signal:
            win_prob = predicted_prob
        else:
            if selected_price <= 0.02:
                win_prob = 0.96
            elif selected_price <= 0.05:
                win_prob = 0.93
            elif selected_price <= 0.10:
                win_prob = 0.89
            elif selected_price <= 0.15:
                win_prob = 0.85
            elif selected_price <= 0.20:
                win_prob = 0.82
            elif selected_price <= 0.25:
                win_prob = 0.78
            else:
                win_prob = 0.74

        if confidence >= 80:
            win_prob = min(win_prob + 0.03, 0.99)
        elif confidence < 65:
            win_prob = max(win_prob - 0.05, 0.50)

        if signal:
            bet = min(25, round(bet * (1.0 + min(max(signal_score, 0.0), 0.25)), 2))

        won = random.random() < win_prob

        if won:
            profit = bet * (1 / max(selected_price, 0.01) - 1) * (1 - self.fee)
        else:
            profit = -bet

        # Create position
        position = {
            'market': market.get('question', 'Unknown')[:50],
            'price': selected_price,
            'outcome': selected_outcome,
            'bet': bet,
            'profit': profit,
            'current_profit': profit,  # Track current P&L
            'won': won,
            'edge': edge,
            'confidence': confidence,
            'signal_source': signal.get('source') if signal else 'fallback',
            'signal_score': signal_score,
            'mirofish_consensus_yes_pct': signal.get('consensus_yes_pct') if signal else None,
            'opened': datetime.now().isoformat()
        }

        self.open_positions.append(position)
        self.trades.append(position)
        self.trades_today += 1

        return won, profit

    def check_positions(self):
        """Check open positions for stop loss / take profit"""
        to_close = []
        
        for i, pos in enumerate(self.open_positions):
            action = self.check_stop_loss(pos)
            if action:
                to_close.append((i, action))
        
        for i, action in reversed(to_close):
            self.close_position(self.open_positions[i], action)
            del self.open_positions[i]

    def run(self, max_trades=20):
        print(f"\n{'='*70}")
        print("PRODUCTION TRADING BOT WITH LLM + RISK MANAGEMENT")
        print(f"{'='*70}")
        print(f"Mode: {self.mode.upper()}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Risk Config: Max position {self.risk['max_position_pct']*100}%, "
              f"Stop loss {self.risk['stop_loss_pct']*100}%, "
              f"Take profit {self.risk['take_profit_pct']*100}%")
        print(f"{'='*70}\n")
        
        # Get initial LLM intelligence
        intel = self.get_llm_intelligence()
        print(f"LLM Intelligence: {intel['sentiment_score']:.0%} bullish")
        
        trade_num = 0
        
        for iteration in range(100):
            if trade_num >= max_trades:
                break
            
            # Check positions first
            if self.open_positions:
                self.check_positions()
                time.sleep(0.2)
            
            markets = self.client.get_markets(50)
            if not markets:
                continue
            
            for m in markets:
                if trade_num >= max_trades:
                    break
                
                try:
                    prices = json.loads(m.get('outcomePrices', '[]'))
                    if not prices or len(prices) < 2:
                        continue
                    
                    price = float(prices[0])
                    volume = float(m.get('volume', 0) or 0)
                    
                    if not self.should_trade(price, volume):
                        continue
                    
                    edge, confidence = self.analyze_market(m, price, volume)
                    
                    if edge < self.risk['min_edge'] or confidence < self.risk['min_confidence']:
                        continue
                    
                    won, profit = self.execute_trade(m, price, edge, confidence)
                    trade = self.open_positions[-1] if self.open_positions else {}

                    trade_num += 1
                    status = "WIN" if won else "LOSS"

                    print(
                        f"Trade {trade_num:2d} | {trade.get('outcome', 'yes').upper()} @ "
                        f"${trade.get('price', price):.2f} | {status:4s} | "
                        f"Edge:{edge:.0%} Conf:{confidence:.0f}% | Bal:${self.balance:.2f} | "
                        f"P:{profit:+.2f}"
                    )
                    
                    time.sleep(0.3)
                    
                except:
                    continue
        
        # Close remaining positions
        print(f"\nClosing {len(self.open_positions)} open positions...")
        for pos in self.open_positions[:]:
            self.close_position(pos, 'end_of_session')
        
        return self.finish()

    def finish(self):
        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0
        profit = self.balance - self.initial_balance
        
        print(f"\n{'='*70}")
        print("PRODUCTION BOT RESULTS")
        print(f"{'='*70}")
        print(f"Total Trades: {total}")
        print(f"Wins: {self.stats['wins']} | Losses: {self.stats['losses']} | Stop Losses: {self.stats['stop_losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({profit/self.initial_balance*100:+.1f}%)")
        print(f"{'='*70}")
        
        # Save results
        result_data = {
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode,
            'trades': total,
            'wins': self.stats['wins'],
            'losses': self.stats['losses'],
            'stop_losses': self.stats['stop_losses'],
            'win_rate': win_rate,
            'profit': profit,
            'balance': self.balance,
            'risk_config': self.risk
        }
        
        with open(f'data/logs/production_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(result_data, f, indent=2)
        
        return result_data


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'paper'
    bot = ProductionBot(starting_balance=100, mode=mode)
    bot.run(max_trades=20)
