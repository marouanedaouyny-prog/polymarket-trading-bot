"""
POLYMARKET CRYPTO LIVE BOT (AGENTS & SELF-LEARNING)
==================================================
Hierarchical Agent Architecture with Self-Learning.
"""

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load configuration
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.data.crypto_section import fetch_crypto_section_markets
from src.data.polymarket_client import PolymarketClient
from src.trading.live_trading import PolymarketOrderExecutor, _extract_binary_prices, _extract_volume, _extract_outcome_token_id
from src.risk.dynamic_risk import DynamicRiskManager
from src.ml.market_predictor import MarketPredictor
from src.utils.logger import get_logger

# Configure logging
logger = get_logger('crypto_live_bot')

class ResearchAgent:
    def __init__(self, predictor, mirofish):
        self.predictor = predictor
        self.mirofish = mirofish

    def _bayesian_update(self, prior_p, evidence_p):
        """
        Apply Bayes' Rule to update win probability.
        Prior (P(H)): ML Model prediction based on historical data.
        Evidence (P(E|H)): Swarm Intel signal (MiroFish).
        Posterior (P(H|E)): The mathematically updated win probability.
        """
        # We assume the Swarm Intel (evidence) has a certain 'strength'
        # If both agree, the probability accelerates toward 100% or 0%
        
        # Avoid division by zero/math errors
        prior_p = max(min(prior_p, 0.99), 0.01)
        evidence_p = max(min(evidence_p, 0.99), 0.01)
        
        # Bayes' Rule implementation for binary outcomes
        numerator = (evidence_p * prior_p)
        denominator = (evidence_p * prior_p) + ((1 - evidence_p) * (1 - prior_p))
        
        return numerator / denominator

    def _calculate_physics_metrics(self, price, volume):
        """
        Apply Newtonian Physics and Information Theory to market data.
        1. Momentum (Newton's 1st Law): Price velocity.
        2. Entropy (Shannon): Signal-to-noise ratio in volume/price.
        """
        # Simulate momentum from volume (Mass * Velocity)
        # Higher volume at stable prices = High Inertia (Safe Trend)
        momentum_score = min(max(volume / 50000.0, 0.1), 1.0)
        
        # Calculate Entropy (Chaos)
        # If price is extreme ($0.04 or $0.96), entropy is low (Order)
        # If price is $0.50, entropy is high (Chaos/Coin Flip)
        p = max(min(price, 0.99), 0.01)
        import math
        entropy = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
        
        # Order Score (Inverse of Entropy)
        order_score = 1.0 - (entropy * 0.5) 
        
        return momentum_score, order_score

    def _calculate_game_theory_edge(self, price, win_prob):
        """
        Apply Game Theory and Probability Theory.
        1. Expected Value (EV): P(Win) * Payout - P(Loss) * Stake
        2. Nash Equilibrium: Is this price 'fair' compared to the crowd?
        3. Kelly Criterion: Optimal stake size to avoid ruin.
        """
        # A. PROBABILITY THEORY: Expected Value (EV)
        # Payout is (1/price) - 1. Fee is 7%.
        payout = (1.0 / price) - 1.0
        ev = (win_prob * payout * 0.93) - (1.0 - win_prob)
        
        # B. GAME THEORY: Market Efficiency
        # If EV is positive, we have an advantage over the 'Market Opponent'
        # We only play if EV > 0.05 (5% theoretical ROI per trade)
        is_nash_favorable = ev > 0.05
        
        # C. KELLY CRITERION (Fractional)
        # f* = (p(b+1) - 1) / b
        # where p is win prob, b is decimal odds (payout)
        if win_prob > price:
            kelly_f = (win_prob * (payout + 1) - 1) / payout
            # Use 25% Kelly for extreme safety (Fractional Kelly)
            safe_kelly = max(0, kelly_f * 0.25)
        else:
            safe_kelly = 0
            
        return ev, safe_kelly, is_nash_favorable

    def analyze(self, market):
        """Ultimate Strategist: Physics + Bayes + Game Theory."""
        question = market.get('question', 'N/A')
        prices = _extract_binary_prices(market)
        if not prices: return None
        
        volume = _extract_volume(market)
        if volume < 25000: return None 

        sides = []
        for side in ["yes", "no"]:
            price = prices[side]
            if not (0.04 <= price <= 0.96) or (0.20 <= price <= 0.30): continue

            # 1. AI & Swarm Layers
            ml_prior = 0.50
            if self.predictor.model:
                try: ml_prior = self.predictor.predict_win_probability(price, volume, 0.05, 50, True)
                except: pass

            swarm_evidence = 0.50
            if self.mirofish:
                try:
                    signal = self.mirofish.build_trade_signal(question, market, yes_price=prices['yes'], no_price=prices['no'], volume=volume)
                    if signal and signal.get('selected_side') == side:
                        swarm_evidence = signal.get('predicted_prob', 0.50)
                except: pass

            # 2. Bayesian & Physics Integration
            mom, order = self._calculate_physics_metrics(price, volume)
            win_prob = self._bayesian_update(ml_prior, swarm_evidence)
            
            # Physics Adjustment
            win_prob = min(win_prob + (mom * 0.05) + (order * 0.05), 0.99)

            # 3. GAME THEORY & PROBABILITY THEORY LAYER
            ev, kelly, favorable = self._calculate_game_theory_edge(price, win_prob)

            # STRATEGIC TRIGGER: 
            # Must have positive EV AND favorable Nash position AND high confidence
            if favorable and win_prob > 0.65 and order > 0.60:
                sides.append({
                    'side': side,
                    'price': price,
                    'prob': win_prob,
                    'ev': ev,
                    'kelly': kelly,
                    'q': question,
                    'market': market
                })

        return max(sides, key=lambda x: x['ev']) if sides else None

class RiskAgent:
    def __init__(self, risk_manager):
        self.risk_manager = risk_manager

    def audit(self, opportunity, balance):
        """Safety audit before execution."""
        approved, reason = self.risk_manager.should_trade(opportunity['prob'], 70, balance)
        return approved, reason

class CryptoLiveBot:
    def __init__(self, mode='paper'):
        self.mode = mode.lower()
        self.client = PolymarketClient()
        self.executor = PolymarketOrderExecutor(mode=self.mode)
        self.history_file = Path("data/training/live_trades_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # INSTITUTIONAL SCALPER CONFIG
        self.risk_config = {
            'max_position_pct': 0.04, 
            'max_daily_trades': 150,
            'stop_loss_pct': 0.30,
            'take_profit_pct': 3.0,
            'daily_loss_limit': 0.15,
            'min_edge': 0.55,
            'min_confidence': 40,
        }
        
        self.risk_manager = DynamicRiskManager(self.risk_config)
        self.predictor = MarketPredictor()
        self.predictor.load_model()
        
        self.mirofish = self._init_mirofish()
        
        # Initialize Agents
        self.research_agent = ResearchAgent(self.predictor, self.mirofish)
        self.risk_agent = RiskAgent(self.risk_manager)
        
        self.is_running = False

    def _save_trade_to_history(self, trade_data):
        """Save trade for future AI training."""
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            
            history.append(trade_data)
            
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"History Save Error: {e}")

    def get_account_balance(self):
        if self.mode == 'live':
            try:
                balance = self.client.get_balance()
                if balance is not None and balance > 0: return balance
            except: pass
        return float(os.getenv('STARTING_BALANCE', 100))

    def _init_mirofish(self):
        try:
            from src.prediction import MiroFishIntegrator
            integrator = MiroFishIntegrator(base_url=os.getenv("MIROFISH_URL", "http://localhost:5001"), use_cache=True, simulation_rounds=40)
            if integrator.available: return integrator
        except: pass
        return None

    def run_cycle(self):
        try:
            logger.info(f"--- [LEAD AGENT] STARTING SCAN ({self.mode.upper()}) ---")
            
            # AI RELOAD
            self.predictor.load_model()
            
            markets = fetch_crypto_section_markets(locale="fr")
            if not markets: return

            balance = self.get_account_balance()
            self.risk_manager.start_session(balance)
            
            # 1. RESEARCH PHASE
            opps = []
            for m in markets:
                o = self.research_agent.analyze(m)
                if o:
                    # 2. RISK PHASE
                    approved, reason = self.risk_agent.audit(o, balance)
                    if approved: opps.append(o)

            if not opps:
                logger.info("[RESEARCH] No high-conviction trades found.")
                return

            opps.sort(key=lambda x: x['prob'], reverse=True)
            
            # 3. EXECUTION PHASE
            for top in opps[:3]:
                bet = round(balance * self.risk_config['max_position_pct'], 2)
                bet = max(5.0, min(bet, 25.0)) 
                
                token_id = _extract_outcome_token_id(top['market'], top['side'])
                if not token_id: continue

                logger.info(f"🚀 [TRADER] EXECUTING {top['side'].upper()} on {top['q'][:40]}... (Prob: {top['prob']:.1%})")
                
                result = self.executor.place_order(
                    market_id=top['market'].get('id'),
                    outcome=top['side'],
                    amount=bet,
                    price=top['price'],
                    token_id=token_id
                )
                logger.info(f"RESULT: {json.dumps(result, default=str)}")
                
        except Exception as e:
            logger.error(f"Cycle Skip: {e}")

    def start(self, interval=60, duration=None):
        self.is_running = True
        end = (time.time() + (duration * 60)) if duration else None
        while self.is_running:
            if end and time.time() >= end: break
            self.run_cycle()
            time.sleep(interval)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="live")
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--duration", type=int, default=600)
    args = p.parse_args()
    bot = CryptoLiveBot(mode=args.mode)
    bot.start(interval=args.interval, duration=args.duration)
