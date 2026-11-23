"""
Trading Project Agent System
Hierarchical agent architecture with LLM understanding of the project

Upgrades applied:
- Unified logging (src/utils/logger.py)
- Centralized config (src/utils/config.py)
- sklearn ML model (src/ml/market_predictor.py)
- AutoPredict scoring rules & backtest evaluation (src/prediction/autopredict_bridge.py)
"""

import json
import os
import time
import random
from datetime import datetime

# Use centralized logging
try:
    from src.utils.logger import get_logger
    logger = get_logger('trading_system')
    USE_LOGGING = True
except ImportError:
    USE_LOGGING = False
    def log(msg):
        print(msg)

# AutoPredict bridge for proper scoring evaluation
try:
    from src.prediction.autopredict_bridge import ScoringBridge, build_forecasts, backtest_report
    AUTOPREDICT_AVAILABLE = True
except ImportError:
    AUTOPREDICT_AVAILABLE = False

# Self-improvement pipeline (walk-forward evolution)
try:
    from src.prediction.self_improvement import evolve, load_champion, DEFAULT_GENOME
    SELF_IMPROVEMENT_AVAILABLE = True
except ImportError:
    SELF_IMPROVEMENT_AVAILABLE = False

# MiroFish integration
try:
    from src.prediction import MiroFishIntegrator
    MIROFISH_AVAILABLE = True
except ImportError:
    MIROFISH_AVAILABLE = False

# Grok research integration — advisory only, never authorizes or sizes trades
try:
    from src.agents.research.grok_extractor import GrokExtractor
    from src.agents.research.sanitizer import TextSanitizer
    from src.trading.research_feature_store import hypothesis_to_features
    from src.trading.paper_evaluator import PaperEvaluator
    GROK_RESEARCH_AVAILABLE = True
except ImportError:
    GROK_RESEARCH_AVAILABLE = False

# Use centralized config
try:
    from src.utils.config import config
except ImportError:
    # Fallback config
    class Config:
        STARTING_BALANCE = 100
        MAX_POSITION_PCT = 0.15
        STOP_LOSS_PCT = 0.25
        TAKE_PROFIT_PCT = 2.0
        DAILY_LOSS_LIMIT = 0.20
        MIN_EDGE = 0.65
        MIN_CONFIDENCE = 65
        MIN_VOLUME = 15000
        PRICE_MIN = 0.01
        PRICE_MAX = 0.35
    config = Config()

PROJECT_CONTEXT = """
# POLYMARKET TRADING BOT PROJECT

## Project Goal
Build an LLM-powered trading system that analyzes Polymarket prediction markets
using real-time web intelligence + trained ML model to achieve consistent profitability
with strict risk management.

## Key Components
1. **Data Collection**: Polymarket API (gamma-api.polymarket.com)
2. **Training Data**: Market data with price, volume, outcomes
3. **Model**: Trained weights for win probability prediction
4. **Strategy**: Low prices ($0.05-0.50) + high volume (+$10K) + edge>8%, conf>85%
5. **Risk Management**: Stop-loss 15%, take-profit 50%, max position 10%, daily loss 5%

## Current Results (Paper Trading)
- Win Rate: varies by configuration (target: maintain >70%)
- Average Profit: varies based on configuration and market conditions
- Total test trades: 500+

## Target
- Consistent profitability with win rate above 70%
- 100% compliance with risk limits before considering any parameter changes

## Files
- agent_trading_system.py: Main trading system
- models/comprehensive_model.json: Trained weights
- data/test_runs/: Test results
"""

AGENT_ROLES = {
    "lead": {
        "description": "Project lead - orchestrates all agents",
        "responsibilities": [
            "Coordinate agent workflow",
            "Make final trading decisions",
            "Monitor overall performance",
            "Handle exceptions and edge cases"
        ],
        "prompt": f"""
You are the Lead Agent for the Polymarket Trading Project.

PROJECT CONTEXT:
{PROJECT_CONTEXT}

YOUR ROLE:
- Coordinate Research Agent (market analysis, intelligence)
- Coordinate Trade Agent (execute trades based on signals)
- Coordinate Risk Agent (validate risk parameters)
- Coordinate Monitor Agent (track performance, detect issues)

COMMUNICATION:
- Use SendMessage to coordinate other agents
- Always include project context in messages
- Make final go/no-go decisions on trades

CURRENT TASK: Run trading session with paper money.
"""
    },
    "research": {
        "description": "Research agent - market intelligence & analysis",
        "responsibilities": [
            "Fetch current market data from Polymarket",
            "Get real-time web intelligence on trending markets",
            "Analyze market sentiment and sector performance",
            "Identify high-probability trading opportunities"
        ],
        "prompt": f"""
You are the Research Agent for the Polymarket Trading Project.

PROJECT CONTEXT:
{PROJECT_CONTEXT}

YOUR ROLE:
- Fetch markets from Polymarket API (price, volume, question)
- Get LLM web intelligence on trending markets (crypto, BTC, ETH, SOL)
- Analyze: price range ($0.05-0.50), volume (>$10K), edge, confidence
- Identify opportunities that meet criteria: edge>8%, confidence>85%

OUTPUT FORMAT:
Return list of trade opportunities with:
- market question
- price
- volume
- calculated edge
- calculated confidence
- sector (crypto/other)
- sentiment score
"""
    },
    "trader": {
        "description": "Trade agent - executes trades based on signals",
        "responsibilities": [
            "Receive validated trade opportunities from Risk Agent",
            "Execute paper trades with position sizing",
            "Calculate win probability based on price tier",
            "Track open positions and P&L"
        ],
        "prompt": f"""
You are the Trader Agent for the Polymarket Trading Project.

PROJECT CONTEXT:
{PROJECT_CONTEXT}

YOUR ROLE:
- Receive validated trades from Risk Agent
- Execute paper trades with position sizing (15% max)
- Calculate win probability by price tier:
  * $0.05-0.10: 89%
  * $0.11-0.20: 85%
  * $0.21-0.30: 82%
  * $0.31-0.50: 74%
- Adjust probability by confidence
- Apply 7% Polymarket fee in profit calculation

OUTPUT:
- Trade execution confirmation
- Win/Loss result
- Updated balance
"""
    },
    "risk": {
        "description": "Risk agent - validates risk parameters",
        "responsibilities": [
            "Validate all trades against risk rules",
            "Check stop-loss / take-profit conditions",
            "Enforce position limits and daily limits",
            "Block trades that exceed risk thresholds"
        ],
        "prompt": f"""
You are the Risk Agent for the Polymarket Trading Project.

PROJECT CONTEXT:
{PROJECT_CONTEXT}

YOUR RISK RULES:
- Max position: 15% of balance
- Max daily trades: 20
- Max open positions: 5
- Stop loss: 15% per trade
- Take profit: 50% per trade
- Daily loss limit: 5%
- Min edge: 8%
- Min confidence: 85%
- Price range: $0.05-0.50
- Min volume: $10,000

VALIDATE:
- Each trade opportunity against all rules
- Open positions for stop-loss/take-profit triggers
- Daily P&L against loss limit

OUTPUT:
- APPROVED: Trade passes all checks
- REJECTED: With reason (which rule failed)
- TRIGGER: Stop-loss/take-profit triggered
"""
    },
    "monitor": {
        "description": "Monitor agent - performance tracking & alerts",
        "responsibilities": [
            "Track win rate and profit over time",
            "Detect performance degradation",
            "Generate performance reports",
            "Alert on anomalies or issues"
        ],
        "prompt": f"""
You are the Monitor Agent for the Polymarket Trading Project.

PROJECT CONTEXT:
{PROJECT_CONTEXT}

YOUR ROLE:
- Track: total trades, wins, losses, win rate, profit
- Calculate running averages
- Detect if win rate drops below 70%
- Generate end-of-session summary
- Save results to data/test_runs/

OUTPUT:
- Real-time stats after each trade
- End-of-session summary with metrics
- Warnings if performance degrades
"""
    }
}

import threading

class TradingAgentSystem:
    def __init__(self, starting_balance=None):
        # Use config or default
        if starting_balance is None:
            starting_balance = getattr(config, 'STARTING_BALANCE', 100)

        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.trades = []
        self.stats = {'wins': 0, 'losses': 0, 'stop_losses': 0}
        self.fee = 0.07

        # Thread safety for balance updates
        self.balance_lock = threading.Lock()
        self.stats_lock = threading.Lock()

        # Trained model weights
        # [STRICT CONFIGURATION] Use centralized production config
        from src.utils.config import config
        self.risk = {
            'max_daily_trades': config.MAX_DAILY_TRADES,
            'max_open_positions': 2,
            'stop_loss_pct': config.STOP_LOSS_PCT,
            'take_profit_pct': config.TAKE_PROFIT_PCT,
            'daily_loss_limit': config.DAILY_LOSS_LIMIT,
            'max_position_size': config.MAX_POSITION_PCT,
            'min_edge': config.MIN_EDGE,
            'min_confidence': config.MIN_CONFIDENCE,
            'price_range': (config.PRICE_MIN, config.PRICE_MAX),
            'min_volume': config.MIN_VOLUME,
            'min_ev': config.MIN_EV,
            'min_bet': config.MIN_BET
        }

        # Load resolved outcomes for actual win/loss evaluation
        self.resolved_outcomes = self._load_resolved_outcomes()

        # Load risk manager with calibration if backtest stats exist
        self._initialize_risk_manager()

        # [IDENTITY RESOLUTION] Initialize Identity Manager
        try:
            from src.utils.identity_manager import MarketIdentityManager
            self.identity_manager = MarketIdentityManager()
            if USE_LOGGING:
                logger.info("Market Identity Manager initialized")
        except Exception as e:
            self.identity_manager = None
            if USE_LOGGING:
                logger.warning(f"Identity Manager not available: {e}")

        self.trades_today = 0
        self.daily_start = starting_balance
        self._session_date = datetime.now().date()
        self.killed = False

        # Import client
        from src.data.polymarket_client import PolymarketClient
        self.client = PolymarketClient()

        # Initialize dynamic risk manager
        try:
            from src.risk.dynamic_risk import DynamicRiskManager
            self.risk_manager = DynamicRiskManager(self.risk)
            self.risk_manager.start_session(starting_balance)
            if USE_LOGGING:
                logger.info("Dynamic risk manager initialized")
        except Exception as e:
            self.risk_manager = None
            if USE_LOGGING:
                logger.warning(f"Dynamic risk manager not available: {e}")

        # Initialize SQLite storage
        self.db = None
        try:
            from src.data.sqlite_db import get_db
            self.db = get_db()
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if USE_LOGGING:
                logger.info("SQLite storage initialized")
        except Exception as e:
            self.db = None
            if USE_LOGGING:
                logger.warning(f"SQLite storage not available: {e}")

        # Load sklearn ML model
        self.ml_model = None
        try:
            from src.ml.market_predictor import MarketPredictor
            self.ml_model = MarketPredictor()
            if not self.ml_model.load_model():
                print("[ML] Training new model...")
                from src.ml.market_predictor import train_and_save_model
                train_and_save_model()
                self.ml_model.load_model()
            print("[ML] Model loaded successfully")
        except Exception as e:
            print(f"[ML] Model not available: {e}")

        # Initialize MiroFish integrator
        self.mirofish = None
        if MIROFISH_AVAILABLE:
            try:
                mf_enabled = getattr(config, 'MIROFISH_ENABLED', True)
                if mf_enabled:
                    self.mirofish = MiroFishIntegrator(
                        base_url=getattr(config, 'MIROFISH_URL', 'http://localhost:5001'),
                        use_cache=getattr(config, 'MIROFISH_USE_CACHE', True),
                        cache_ttl=getattr(config, 'MIROFISH_CACHE_TTL', 3600),
                        simulation_rounds=getattr(config, 'MIROFISH_SIMULATION_ROUNDS', 50),
                    )
                    if self.mirofish.available:
                        print("[MiroFish] Swarm intelligence engine connected")
                    else:
                        print("[MiroFish] Engine not available, using fallback intelligence")
                        self.mirofish = None
            except Exception as e:
                print(f"[MiroFish] Init error: {e}")
                self.mirofish = None

        # Grok research extractor — advisory signal only, no execution authority
        self.grok = None
        self.sanitizer = None
        self.paper_evaluator = None
        if GROK_RESEARCH_AVAILABLE:
            try:
                self.grok = GrokExtractor()
                self.sanitizer = TextSanitizer()
                self.paper_evaluator = PaperEvaluator(
                    min_edge=config.MIN_EDGE,
                    min_confidence=float(getattr(config, 'MIN_CONFIDENCE', 85)) / 100.0,
                )
                if USE_LOGGING:
                    logger.info("Grok research extractor initialized (advisory only)")
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"Grok research extractor unavailable: {e}")

        # Initialize Paper Ledger
        try:
            from src.trading.ledger import PaperLedger
            self.ledger = PaperLedger()
            if USE_LOGGING:
                logger.info("Paper Ledger initialized")
        except Exception as e:
            self.ledger = None
            if USE_LOGGING:
                logger.warning(f"Paper Ledger not available: {e}")

        # Use logging
        if USE_LOGGING:
            logger.info(f"TradingAgentSystem initialized with balance ${starting_balance}")

    def _evaluate_and_log(self):
        """Evaluate recent performance using autopredict scoring rules.

        Builds forecasts from recent trades and logs Brier score, log score,
        and calibration gap.  The evaluation is read-only — it does NOT write
        back to training data to avoid the circular feedback loop that was
        present in _sync_to_training_data.
        """
        if not AUTOPREDICT_AVAILABLE or not self.trades:
            return

        forecasts = []
        for t in self.trades[-50:]:  # last 50 trades
            if t.get("won") is None:
                continue
            forecasts.append({
                "market_id": t.get("market_id", ""),
                "probability": t.get("win_probability", 0.5),
                "outcome": 1 if t.get("won") else 0,
            })

        if not forecasts:
            return

        report = ScoringBridge.full_report(forecasts)
        if USE_LOGGING:
            logger.info(
                f"[EVAL] Brier={report['brier_score']:.4f} "
                f"LogScore={report['log_score']:.4f} "
                f"CalGap={report['calibration']['mean_absolute_gap']:.4f} "
                f"(n={report['count']})"
            )

    def _adjust_risk_thresholds(self):
        """[WORKFLOW OPTIMIZATION] Dynamically tighten thresholds based on session win rate."""
        total = self.stats['wins'] + self.stats['losses']
        if total < 5: return # Need some sample size

        win_rate = (self.stats['wins'] / total) * 100

        # If win rate is low, tighten the screws
        if win_rate < 75:
            # Increase min edge and confidence requirements
            self.risk['min_edge'] = min(0.75, self.risk['min_edge'] + 0.01)
            self.risk['min_confidence'] = min(80, self.risk['min_confidence'] + 2)
            if USE_LOGGING:
                logger.info(f"Win rate low ({win_rate:.1f}%). Tightening thresholds: Edge={self.risk['min_edge']:.2f}, Conf={self.risk['min_confidence']}")
        elif win_rate > 90:
            # If doing great, we can slightly relax or maintain
            self.risk['min_edge'] = max(getattr(config, 'MIN_EDGE', 0.65), self.risk['min_edge'] - 0.005)
            self.risk['min_confidence'] = max(getattr(config, 'MIN_CONFIDENCE', 65), self.risk['min_confidence'] - 1)

    def _log_execution(self, opportunity: dict, actual_price: float) -> None:
        """Log execution details including slippage for auditing."""
        expected_price = float(opportunity.get('price', actual_price))
        slippage = actual_price - expected_price
        slippage_pct = (slippage / expected_price * 100) if expected_price else 0.0
        msg = (
            f"[EXECUTION] market={opportunity.get('canonical_id', opportunity.get('market_id', '?'))} "
            f"expected={expected_price:.4f} actual={actual_price:.4f} "
            f"slippage={slippage:+.4f} ({slippage_pct:+.2f}%)"
        )
        print(msg)
        if USE_LOGGING:
            logger.info(msg)

    def learning_agent(self, iterations=1, samples=2000):
        """[WORKFLOW OPTIMIZATION] Evaluate model calibration against resolved markets.

        Instead of retraining on self-reinforcing simulated data, this runs
        the autopredict evaluation pipeline to surface Brier, log score, and
        calibration gaps so the operator can decide whether to retrain on
        real resolved market data.
        """
        print(f"\n[LEARNING AGENT] Running evaluation cycle...")

        # Load resolved markets and evaluate model calibration
        try:
            records = json.load(open(os.path.join('data', 'training', 'resolved_markets.json')))
            if not records:
                print("[LEARNING AGENT] No resolved markets found for evaluation")
                return False

            if self.ml_model and self.ml_model.is_trained:
                def predict_fn(price, volume, is_crypto):
                    return self.ml_model.predict_win_probability(
                        price=price, volume=volume, is_crypto=bool(is_crypto)
                    )
            else:
                print("[LEARNING AGENT] No trained model — using market-price baseline")
                def predict_fn(price, volume, is_crypto):
                    return min(max(price, 0.02), 0.70)

            bt = backtest_report(records, predict_fn, min_volume=1000)
            report = bt["scoring"]
            summary = bt["summary"]

            print(f"[LEARNING] Brier={report['brier_score']:.4f} "
                  f"LogScore={report['log_score']:.4f} "
                  f"CalGap={report['calibration']['mean_absolute_gap']:.4f}")
            print(f"[LEARNING] {summary['total_trades']} trades, "
                  f"WR={summary['win_rate']:.1%}, ROI={summary['roi_pct']:.1f}%")

            # If calibration gap is bad, suggest retraining
            if report["calibration"]["mean_absolute_gap"] > 0.10 and self.ml_model:
                print("[LEARNING] WARNING: Calibration gap > 10%. Consider retraining on resolved data.")
            return True

        except Exception as e:
            print(f"[LEARNING AGENT] Evaluation failed: {e}")
            return False

    def get_llm_intelligence(self, question=None, market_data=None):
        """Get market intelligence from MiroFish if available, local fallback otherwise."""
        if self.mirofish:
            intel = self.mirofish.get_market_intelligence(question or "", market_data)
            if intel:
                return intel

        # Local fallback — basic data-driven intelligence, no external API needed
        price = float((market_data or {}).get('price', 0.15))
        volume = float((market_data or {}).get('volume', 0))
        q_lower = (question or "").lower()

        sectors = []
        for kw in ['crypto', 'bitcoin', 'ethereum', 'solana', 'politics', 'sports',
                   'election', 'world cup', 'economy', 'fed', 'rate']:
            if kw in q_lower:
                sectors.append(kw)

        return {
            "sentiment_score": 0.5,
            "confidence_boost": 0,
            "sectors": sectors,
            "reasoning": "Local fallback intelligence (MiroFish not configured)",
            "volume_signal": "high" if volume > 500_000 else "normal",
        }

    def _grok_research_signal(self, question: str, market_id: str) -> dict:
        """
        Advisory research signal from Grok/X. Never authorizes or sizes a trade.

        Returns a dict with research_direction (1/-1/0), research_confidence (0-1),
        research_uncertainty (0-1), and research_passed (paper-eval result).
        All external text is sanitized before reaching the model.
        """
        result = {
            "research_direction": 0.0,
            "research_confidence": 0.0,
            "research_uncertainty": 1.0,
            "research_passed": False,
        }
        if not (self.grok and self.sanitizer and self.paper_evaluator):
            return result

        # Sanitize the question before it leaves this process (prompt-injection guard).
        clean = self.sanitizer.sanitize(question)
        if not clean.safe:
            if USE_LOGGING:
                logger.warning(f"Grok input rejected for {market_id}: {clean.reasons}")
            return result

        hypothesis = self.grok.extract_hypothesis(market_id, clean.text)
        if hypothesis is None:
            return result

        features = hypothesis_to_features(hypothesis)
        eval_result = self.paper_evaluator.evaluate(
            market_id=market_id,
            hypothesis=hypothesis,
        )

        result["research_direction"] = features.research_direction
        result["research_confidence"] = features.research_confidence
        result["research_uncertainty"] = features.research_uncertainty
        result["research_passed"] = bool(eval_result.passed)
        return result

    def _load_resolved_outcomes(self):
        """Load resolved market outcomes using Identity Manager for canonical resolution."""
        resolved_file = os.path.join('data', 'training', 'resolved_markets.json')
        if not os.path.isfile(resolved_file):
            return {}

        try:
            from src.utils.identity_manager import MarketIdentityManager
            im = MarketIdentityManager()
            outcomes = {}

            with open(resolved_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                # Resolve each historical market to a canonical ID
                cid, _, _ = im.resolve_market(item)
                if 'outcome' in item:
                    outcomes[cid] = item['outcome']

            if USE_LOGGING:
                logger.info(f"Loaded {len(outcomes)} canonical resolved outcomes")
            return outcomes
        except Exception as e:
            if USE_LOGGING:
                logger.error(f"Failed to load resolved outcomes: {e}")
            return {}

    def _initialize_risk_manager(self):
        """Instantiate DynamicRiskManager and optionally calibrate from backtest stats.
        If a backtest result file exists, use its statistics to adjust risk parameters.
        """
        try:
            from src.risk.dynamic_risk import DynamicRiskManager
            from src.risk.state_storage import load_state
            self.risk_manager = DynamicRiskManager(self.risk)
            # Load persisted state if any
            persisted = load_state()
            if persisted:
                for k, v in persisted.items():
                    setattr(self.risk_manager, k, v)
            # Attempt to calibrate from latest backtest stats
            stats_file = os.path.join('src', 'backtesting', 'historical', 'data', 'backtest', 'latest_stats.json')
            if os.path.isfile(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                self.risk_manager.configure_from_history(stats)
                if USE_LOGGING:
                    logger.info("Risk manager calibrated from backtest stats")
            self.risk_manager.start_session(self.balance)
            if USE_LOGGING:
                logger.info("Dynamic risk manager initialized")
        except Exception as e:
            self.risk_manager = None
            if USE_LOGGING:
                logger.warning(f"Dynamic risk manager not available: {e}")

    def kill(self):
        """Emergency kill switch"""
        self.killed = True
        if USE_LOGGING:
            logger.warning("TRADING SYSTEM KILLED BY EXTERNAL SIGNAL")

    def research_agent(self):
        """[OPTIMIZED] Research Agent - Find trading opportunities with real intelligence."""
        from src.agents.sentiment_agent import SentimentAgent
        print("\n[RESEARCH AGENT] Fetching market data and analyzing sentiment...")

        markets = self.client.get_markets(50)
        if not markets:
            logger.warning("No markets received from API")
            return []

        # Input validation for market data
        validated_markets = []
        for market in markets:
            try:
                # Validate required fields
                if not all(key in market for key in ['question', 'outcomePrices']):
                    logger.warning(f"Invalid market data structure: {market}")
                    continue

                # Validate question format
                question = market.get('question', '').strip()
                if not question or len(question) > 500:  # Reasonable length limit
                    logger.warning(f"Invalid question format: {question}")
                    continue

                # Validate outcome prices
                try:
                    prices = json.loads(market.get('outcomePrices', '[]'))
                    if not isinstance(prices, list) or len(prices) < 2:
                        logger.warning(f"Invalid outcome prices: {market.get('outcomePrices')}")
                        continue

                    # Validate price values (API may return strings or floats)
                    valid_prices = []
                    for price in prices:
                        try:
                            p = float(price)
                            if 0 <= p <= 1:
                                valid_prices.append(p)
                        except (TypeError, ValueError):
                            logger.warning(f"Invalid price value: {price}")

                    if len(valid_prices) < 2:
                        continue

                    market['validated_prices'] = valid_prices
                    validated_markets.append(market)

                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Invalid price data in market {question[:30]}...: {e}")
                    continue

            except Exception as e:
                logger.error(f"Error validating market data: {e}")
                continue

        if not validated_markets:
            logger.warning("No valid markets after validation")
            return []

        markets = validated_markets

        sentiment_agent = SentimentAgent()
        opportunities = []

        for m in markets:
            try:
                question = m.get('question', '')

                sentiment = sentiment_agent.analyze_sentiment(question)
                sentiment_score = sentiment.get('score', -1.0)
                confidence = min(max(sentiment_score * 100, 0), 100)

                if "Analysis failed" in sentiment.get('reasoning', '') or sentiment_score < 0.1:
                    logger.warning(f"Sentiment analysis failed for {question[:30]}... Skipping.")
                    continue

                prices = json.loads(m.get('outcomePrices', '[]'))
                if not prices or len(prices) < 2:
                    continue

                price = float(prices[0])
                volume = float(m.get('volume', 0) or 0)
                market_id = m.get('id')

                market_intel = self.get_llm_intelligence(question, {
                    'price': price,
                    'volume': volume
                })
                if not market_intel or "Analysis failed" in market_intel.get('reasoning', ''):
                    logger.warning(f"Market intelligence unavailable for {question[:30]}... Skipping.")
                    continue

                # Grok research signal — advisory only, never authorizes or sizes a trade.
                grok_signal = self._grok_research_signal(question, market_id)
                research_modifier = 1.0
                if grok_signal['research_passed'] and grok_signal['research_confidence'] > 0:
                    # Blend Grok confidence into sentiment confidence; cannot raise floor above risk gate.
                    research_modifier = grok_signal['research_confidence']

                confidence = min(max(sentiment_score * 100 * research_modifier, 0), 100)

                if price < self.risk['price_range'][0] or price > self.risk['price_range'][1]:
                    continue
                if volume < self.risk['min_volume']:
                    continue

                if not self.ml_model or not self.ml_model.is_trained:
                    logger.warning("Trained ML model unavailable. Skipping research.")
                    continue

                q_lower = question.lower()
                sector = 'other'
                sectors = market_intel.get('sectors', [])
                for s in sectors:
                    if s in q_lower:
                        sector = s
                        break

                is_crypto = sector in ['crypto', 'bitcoin', 'ethereum', 'solana']
                model_prob = self.ml_model.predict_win_probability(
                    price=price,
                    volume=volume,
                    edge=0.0,
                    confidence=confidence,
                    is_crypto=is_crypto,
                    question=question,
                )

                ev = (model_prob * ((1 / price - 1) * (1 - self.fee))) - (1 - model_prob)
                edge = model_prob - price

                if ev < self.risk['min_ev'] or edge < self.risk['min_edge'] or confidence < self.risk['min_confidence']:
                    continue

                if self.identity_manager:
                    canonical_id, _, _ = self.identity_manager.resolve_market(m)
                else:
                    canonical_id = f"PM-{market_id}"

                opportunities.append({
                    'market_id': market_id,
                    'canonical_id': canonical_id,
                    'question': question,
                    'price': price,
                    'volume': volume,
                    'edge': edge,
                    'confidence': confidence,
                    'sector': sector,
                    'sentiment_score': sentiment_score,
                    'ev': ev
                })

            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"Research agent skipped market: {e}")
                continue

        print(f"[RESEARCH AGENT] Found {len(opportunities)} opportunities")
        return opportunities

    def _roll_daily_state(self):
        """Reset daily counters on a new calendar day.

        Without this, trades_today and daily_start never move after __init__,
        so the daily trade cap and daily loss limit apply to the whole process
        lifetime instead of to one day.
        """
        today = datetime.now().date()
        if today == self._session_date:
            return
        self._session_date = today
        self.trades_today = 0
        self.daily_start = self.balance
        if self.risk_manager:
            self.risk_manager.reset_daily(self.balance)

    def risk_agent(self, opportunity):
        """Risk Agent - validate trade using centralized hard rules."""
        self._roll_daily_state()
        if opportunity['price'] < self.risk['price_range'][0]:
            return {'approved': False, 'reason': 'Price below min'}
        if opportunity['price'] > self.risk['price_range'][1]:
            return {'approved': False, 'reason': 'Price above max'}
        if opportunity['volume'] < self.risk['min_volume']:
            return {'approved': False, 'reason': 'Volume below min'}
        if opportunity.get('ev', 0) < self.risk['min_ev']:
            return {'approved': False, 'reason': 'EV below min'}
        if opportunity['edge'] < self.risk['min_edge']:
            return {'approved': False, 'reason': 'Edge below min'}
        if opportunity['confidence'] < self.risk['min_confidence']:
            return {'approved': False, 'reason': 'Confidence below min'}
        if self.balance < (self.risk['min_bet'] / self.risk['max_position_size']):
            return {'approved': False, 'reason': 'Balance too low to maintain 2% risk'}
        if self.trades_today >= self.risk['max_daily_trades']:
            return {'approved': False, 'reason': 'Daily trade limit reached'}
        daily_loss = (self.daily_start - self.balance) / self.daily_start
        if daily_loss >= self.risk['daily_loss_limit']:
            return {'approved': False, 'reason': 'Daily loss limit reached'}

        if self.risk_manager:
            approved, reason = self.risk_manager.should_trade(
                edge=opportunity['edge'],
                confidence=opportunity['confidence'],
                balance=self.balance
            )
            if not approved:
                return {'approved': False, 'reason': reason}
        return {'approved': True, 'reason': 'Approved'}

    def _rule_based_prob(self, price, confidence):
        """Calculate win probability based on price tier and confidence"""
        if price <= 0.02:
            win_prob = 0.96
        elif price <= 0.05:
            win_prob = 0.93
        elif price <= 0.10:
            win_prob = 0.89
        elif price <= 0.15:
            win_prob = 0.85
        elif price <= 0.20:
            win_prob = 0.82
        else:
            win_prob = 0.74

        if confidence >= 80:
            win_prob = min(win_prob + 0.03, 0.99)
        elif confidence < 65:
            win_prob = max(win_prob - 0.05, 0.50)

        return win_prob

    def trader_agent(self, opportunity):
        """Trader Agent - Execute the trade with strict 2% risk."""

        # [STRICT RISK ENFORCEMENT] 2% Position Size
        # If balance too small to risk 2% at min_bet, trade is blocked
        position_pct = self.risk['max_position_size']
        min_bet = self.risk['min_bet']

        required_bet = self.balance * position_pct

        if required_bet < min_bet:
            # Check if we can afford the min_bet while respecting max risk
            # Strict mode: If balance < min_bet/position_pct, block trade
            if self.balance < (min_bet / position_pct):
                 if USE_LOGGING:
                     logger.warning("Trade blocked: Balance too low to maintain risk limits.")
                 return {'won': None, 'profit': 0, 'blocked': True}
            bet = min_bet
        else:
            bet = required_bet

        price = opportunity['price']
        volume = opportunity['volume']
        confidence = opportunity['confidence']
        edge = opportunity['edge']
        is_crypto = opportunity.get('sector', 'other') in ['crypto', 'bitcoin', 'ethereum', 'solana']

        # [HARDENING] Per-trade Intelligence analysis
        question = opportunity.get('question', '')
        market_intel = self.get_llm_intelligence(question, {'price': price, 'volume': volume})

        # [HARDENING] Circuit Breaker: If intelligence fails/offline, do not trade.
        if not market_intel or "Analysis failed" in market_intel.get('reasoning', ''):
             if USE_LOGGING:
                 logger.warning(f"Market {opportunity.get('canonical_id')} intelligence failed. Circuit breaker triggered.")
             return {'won': None, 'profit': 0, 'blocked': True}

        confidence = min(confidence + market_intel.get('confidence_boost', 0), 100)

        # Use ML model if available, otherwise reject trade
        if self.ml_model and self.ml_model.is_trained:
            try:
                win_prob = self.ml_model.predict_win_probability(
                    price=price,
                    volume=volume,
                    edge=edge,
                    confidence=confidence,
                    is_crypto=is_crypto,
                    question=question,
                )
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"ML prediction failed: {e}")
                return {'won': None, 'profit': 0, 'blocked': True}
        else:
            # [HARDENING] Refuse to trade without trained ML model
            return {'won': None, 'profit': 0, 'blocked': True}

        if USE_LOGGING:
            logger.info(f"Trade: price=${price:.2f}, win_prob={win_prob:.2%}")

        # [EXECUTION LOGGING] Log Expected vs Actual
        expected_price = float(opportunity['price'])
        actual_price = float(price) # This is the price obtained
        slippage = actual_price - expected_price

        if USE_LOGGING:
            logger.info(f"EXECUTION_LOG: market={opportunity['canonical_id']}, "
                        f"expected={expected_price:.4f}, "
                        f"actual={actual_price:.4f}, "
                        f"slippage={slippage:.4f}, "
                        f"volume={opportunity['volume']:.2f}")

        # Buy the side the model thinks is underpriced relative to the market.
        # A win_prob below the YES price means NO is the value side.
        predicted_yes = win_prob >= price
        side_price = price if predicted_yes else (1.0 - price)

        # [LEDGER] Record trade entry
        if self.ledger:
            self.ledger.record_entry({
                "market_id": opportunity.get('market_id'),
                "canonical_id": opportunity.get('canonical_id'),
                "selected_outcome": "yes" if predicted_yes else "no",
                "entry_price": side_price,
                "model_probability": win_prob,
                "ev": opportunity.get('ev', 0),
                "edge": edge,
                "bet_size": bet,
                "fees": bet * self.fee,
                "slippage": slippage
            })

        # [HARDENING] Only resolve outcomes from verified data
        actual_outcome = self.resolved_outcomes.get(opportunity.get('canonical_id'))

        if actual_outcome is None:
            if USE_LOGGING:
                logger.info(f"Market {opportunity.get('canonical_id')} outcome pending. Trade untracked.")
            return {'won': None, 'profit': 0, 'blocked': False}

        won = (actual_outcome == 'yes' and predicted_yes) or (actual_outcome == 'no' and not predicted_yes)

        # Evaluate scoring periodically (no circular training-data feedback)
        if (self.stats['wins'] + self.stats['losses']) % 10 == 0:
            self._evaluate_and_log()

        if USE_LOGGING:
            logger.info(f"Trade: price=${price:.2f}, win_prob={win_prob:.2%}, predicted_yes={predicted_yes}, actual_outcome={actual_outcome}, won={won}")

        if won:
            # Payout is on the side actually bought, not always the YES price.
            profit = bet * (1 / side_price - 1) * (1 - self.fee)
        else:
            profit = -bet

        # [LEDGER] Record trade resolution
        if self.ledger:
            self.ledger.record_resolution(
                canonical_id=opportunity.get('canonical_id'),
                actual_outcome=actual_outcome,
                realized_pnl=profit
            )

        # Thread-safe balance update
        with self.balance_lock:
            self.balance += profit
        self.trades_today += 1

        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1

        # [SIGNAL ACCURACY] Log outcome so accuracy tracker can compute per-strategy win rates
        try:
            from src.trading.signal_accuracy import get_tracker
            get_tracker().log_outcome(
                market_id=opportunity.get('canonical_id', opportunity.get('market_id', '')),
                won=won,
            )
        except Exception:
            pass

        # [PROMETHEUS] Push live trading state after every trade
        try:
            from src.monitoring.metrics import update_trading_metrics
            from src.api.state import push_trading_state
            total = self.stats['wins'] + self.stats['losses']
            _wr = (self.stats['wins'] / total) if total > 0 else 0.0
            _dd = getattr(self.risk_manager, 'current_drawdown', 0.0) if self.risk_manager else 0.0
            _op = len(getattr(self.risk_manager, 'positions', {}))
            _pnl = self.balance - self.daily_start
            update_trading_metrics(
                balance=self.balance,
                drawdown=_dd,
                win_rate=_wr,
                open_positions=_op,
                daily_pnl=_pnl,
            )
            push_trading_state(
                balance=self.balance,
                drawdown=_dd,
                win_rate=_wr,
                open_positions=_op,
                daily_pnl=_pnl,
            )
        except Exception:
            pass

        # [WORKFLOW OPTIMIZATION] Dynamic Threshold Tightening
        self._adjust_risk_thresholds()

        # Update dynamic risk manager
        if self.risk_manager:
            self.risk_manager.update_after_trade(won, profit, self.balance)
            if USE_LOGGING:
                metrics = self.risk_manager.get_risk_metrics()
                logger.info(f"Risk: DD={metrics['drawdown']:.1%}, Streak={metrics['winning_streak']}/{metrics['losing_streak']}")
            # Persist risk manager state after each trade
            try:
                from src.risk.state_storage import save_state
                state = {
                    'peak_balance': self.risk_manager.peak_balance,
                    'current_drawdown': self.risk_manager.current_drawdown,
                    'max_drawdown': self.risk_manager.max_drawdown,
                    'winning_streak': self.risk_manager.winning_streak,
                    'losing_streak': self.risk_manager.losing_streak,
                    'consecutive_losses': self.risk_manager.consecutive_losses,
                    'daily_start_balance': self.risk_manager.daily_start_balance,
                }
                save_state(state)
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"Failed to persist risk state: {e}")

        # Save to SQLite
        if self.db:
            try:
                trade_record = {
                    'market': opportunity.get('market', 'Unknown'),
                    'price': price,
                    'bet': bet,
                    'won': won,
                    'profit': profit,
                    'edge': opportunity['edge'],
                    'confidence': confidence,
                    'win_prob': win_prob,
                    'opened': datetime.now().isoformat()
                }
                self.db.save_trade(trade_record, self.session_id)
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"Failed to save trade: {e}")

        # Record trade for scoring evaluation
        self.trades.append({
            "market_id": opportunity.get('market_id', ''),
            "won": won,
            "profit": profit,
            "win_probability": win_prob,
            "price": price,
            "bet": bet,
            "edge": opportunity.get('edge', 0),
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        })

        return {
            'won': won,
            'profit': profit,
            'win_probability': win_prob,
            'new_balance': self.balance
        }

    def monitor_agent(self, trade_result, opportunity):
        """Monitor Agent - Track and report"""
        # [MONITORING] Automated status report
        if self.trades_today % 10 == 0:
            print(f"\n[MONITOR] Trades: {self.trades_today} | Balance: ${self.balance:.2f} | Win Rate: {(self.stats['wins']/(self.trades_today or 1))*100:.1f}%")

        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0

        # [HARDENING] Handle pending trades
        if trade_result['won'] is None:
            status = "PENDING"
        else:
            status = "WIN" if trade_result['won'] else "LOSS"

        print(f"  [{self.stats['wins'] + self.stats['losses']}] {status} | "
              f"${opportunity['price']:.2f} | "
              f"Edge:{opportunity['edge']:.0%} Conf:{opportunity['confidence']:.0f}% | "
              f"Bal:${self.balance:.2f}")

        # Warning if win rate drops
        if total >= 10 and win_rate < 70:
            print(f"   WARNING: Win rate dropped to {win_rate:.1f}%")

        return {
            'total_trades': total,
            'wins': self.stats['wins'],
            'losses': self.stats['losses'],
            'win_rate': win_rate,
            'profit': self.balance - self.initial_balance
        }

    def lead_agent(self, max_trades=20, retrain_every=0):
        """Lead Agent - Orchestrate the trading session"""
        print(f"\n{'='*70}")
        print("LEAD AGENT - POLYMARKET TRADING SYSTEM")
        print(f"{'='*70}")
        print(f"Mode: PAPER TRADING")
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Risk Config: Max Pos 15%, Stop-Loss 25%, Take-Profit 200%")
        print(f"Target: maintain win rate above 70%")
        print(f"{'='*70}\n")

        # Get initial intelligence
        intel = self.get_llm_intelligence()
        if intel:
            print(f"[LEAD] Market Intelligence: {intel.get('sentiment_score', 0):.0%} bullish\n")
        else:
            print("[LEAD] Market Intelligence unavailable. No-trade circuit breaker enabled.\n")

        from concurrent.futures import ThreadPoolExecutor

        for trade_num in range(1, max_trades + 1):
            if self.killed:
                print("[LEAD] Emergency kill switch activated. Stopping session.")
                break
            # [WORKFLOW OPTIMIZATION] Periodic retraining
            if retrain_every > 0 and trade_num > 1 and (trade_num - 1) % retrain_every == 0:
                self.learning_agent()
            # [SELF-IMPROVEMENT] Periodic evolution every 50 trades
            if SELF_IMPROVEMENT_AVAILABLE and trade_num > 1 and trade_num % 50 == 0:
                try:
                    import json
                    records_file = os.path.join('data', 'training', 'resolved_markets.json')
                    if os.path.isfile(records_file):
                        records = json.load(open(records_file))
                        if len(records) >= 10:
                            print(f"\n[SELF-IMPROVEMENT] Evolution checkpoint...")
                            evolve(records, population=5, children=3, min_trades=3)
                except Exception as e:
                    print(f"[SELF-IMPROVEMENT] Evolution checkpoint failed: {e}")

            # Step 1: Research
            opportunities = self.research_agent()

            if not opportunities:
                print(f"[LEAD] No opportunities found, continuing...")
                time.sleep(1)
                continue

            # Sort by edge (best first)
            opportunities.sort(key=lambda x: x['edge'], reverse=True)

            # [WORKFLOW OPTIMIZATION] Parallel Intelligence Gathering
            # Fetch intel for top candidates in parallel to pre-warm cache and refine edge/conf
            top_candidates = opportunities[:5]

            def process_candidate(opp):
                # This pre-warms the cache and allows trader_agent to be faster
                intel = self.get_llm_intelligence(opp['question'], opp)
                if not intel or "Analysis failed" in intel.get('reasoning', ''):
                    opp['confidence'] = -1
                    return opp
                # Update opportunity with intelligence results
                opp['confidence'] = min(opp['confidence'] + intel.get('confidence_boost', 0), 100)
                if 'edge' in intel:
                    opp['edge'] = (opp['edge'] + intel['edge']) / 2
                return opp

            with ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(process_candidate, top_candidates))

            # Step 2: Risk validation (check top opportunities)
            approved = None
            for opp in top_candidates:
                risk_check = self.risk_agent(opp)
                if risk_check['approved']:
                    approved = opp
                    break

            if not approved:
                continue

            # Step 3: Execute trade
            result = self.trader_agent(approved)

            # Step 4: Monitor
            self.monitor_agent(result, approved)

            time.sleep(0.3)

        # [WORKFLOW OPTIMIZATION] Trigger learning after session
        if total_trades := (self.stats['wins'] + self.stats['losses']):
            if total_trades >= 5:
                self.learning_agent()

            # [SELF-IMPROVEMENT] Run evolution if enough trades resolved
            if SELF_IMPROVEMENT_AVAILABLE and total_trades >= 10:
                try:
                    records_file = os.path.join('data', 'training', 'resolved_markets.json')
                    if os.path.isfile(records_file):
                        import json
                        records = json.load(open(records_file))
                        if len(records) >= 10:
                            print(f"\n[SELF-IMPROVEMENT] Running evolution on {len(records)} resolved markets...")
                            result = evolve(records, population=5, children=3, min_trades=3)
                            if result.get('generation', {}).get('kept', 0) > 0:
                                print(f"[SELF-IMPROVEMENT] Champion improved! Brier={result['fitness'].get('brier', '?'):.4f}")
                except Exception as e:
                    print(f"[SELF-IMPROVEMENT] Evolution failed: {e}")

        return self.finish()

    def finish(self):
        """Generate final report"""
        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0
        profit = self.balance - self.initial_balance

        # Brier score over session trades
        session_forecasts = []
        for t in self.trades[-200:]:
            if t.get("won") is None:
                continue
            session_forecasts.append({
                "market_id": t.get("market_id", ""),
                "probability": t.get("win_probability", 0.5),
                "outcome": 1 if t.get("won") else 0,
            })
        if session_forecasts and AUTOPREDICT_AVAILABLE:
            report = ScoringBridge.full_report(session_forecasts)

        print(f"\n{'='*70}")
        print("SESSION COMPLETE")
        print(f"{'='*70}")
        print(f"Total Trades: {total}")
        print(f"Wins: {self.stats['wins']} | Losses: {self.stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({profit/self.initial_balance*100:+.1f}%)")
        if session_forecasts and AUTOPREDICT_AVAILABLE:
            print(f"Scoring — Brier: {report['brier_score']:.4f} | "
                  f"LogScore: {report['log_score']:.4f} | "
                  f"CalGap: {report['calibration']['mean_absolute_gap']:.4f}")
        print(f"{'=':>70}\n")

        # Save to SQLite
        if self.db:
            try:
                session_record = {
                    'id': self.session_id,
                    'start_time': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'trades': total,
                    'wins': self.stats['wins'],
                    'losses': self.stats['losses'],
                    'win_rate': win_rate,
                    'starting_balance': self.initial_balance,
                    'ending_balance': self.balance,
                    'profit': profit
                }
                self.db.save_session(session_record)
                if USE_LOGGING:
                    logger.info(f"Session saved to SQLite: {self.session_id}")
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"Failed to save session: {e}")

        # Save results
        os.makedirs('data/test_runs', exist_ok=True)
        with open(f'data/test_runs/agent_session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump({
                'total_trades': total,
                'wins': self.stats['wins'],
                'losses': self.stats['losses'],
                'win_rate': win_rate,
                'profit': profit,
                'balance': self.balance
            }, f, indent=2)

        return {'win_rate': win_rate, 'profit': profit}


if __name__ == "__main__":
    TradingAgentSystem(starting_balance=100).lead_agent(max_trades=20)
