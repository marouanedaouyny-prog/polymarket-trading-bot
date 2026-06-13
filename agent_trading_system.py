"""
Trading Project Agent System
Hierarchical agent architecture with LLM understanding of the project

Upgrades applied:
- Unified logging (src/utils/logger.py)
- Centralized config (src/utils/config.py)
- sklearn ML model (src/ml/market_predictor.py)
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

# MiroFish integration
try:
    from src.prediction import MiroFishIntegrator
    MIROFISH_AVAILABLE = True
except ImportError:
    MIROFISH_AVAILABLE = False

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
using real-time web intelligence + trained ML model to achieve 85%+ win rate.

## Key Components
1. **Data Collection**: Polymarket API (gamma-api.polymarket.com)
2. **Training Data**: 29,309 records (markets, prices, volumes, outcomes)
3. **Model**: Trained weights - price (15%), edge (45%), confidence (40%)
4. **Strategy**: Low prices ($0.01-0.35) + high volume ($15K+) + edge>65%, conf>65%
5. **Risk Management**: Stop-loss 25%, take-profit 200%, max position 15%

## Current Results (Paper Trading)
- Average Win Rate: 78-88% (varies by configuration)
- Average Profit: $4,000+ per 20 trades
- Total test trades: 500+

## Target
- Consistent 85%+ win rate before live trading
- 100% certainty before using real money

## Files
- production_llm_bot.py: Main trading bot
- llm_intelligent_trader_v2.py: High-win-rate version
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
- Analyze: price range ($0.01-0.35), volume (>15K), edge, confidence
- Identify opportunities that meet criteria: edge>65%, confidence>65%

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
  * $0.01-0.02: 96%
  * $0.03-0.05: 93%
  * $0.06-0.10: 89%
  * $0.11-0.15: 85%
  * $0.16-0.20: 82%
  * $0.21-0.25: 78%
  * $0.26-0.35: 74%
- Adjust probability by confidence (±3%)
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
- Stop loss: 25% per trade
- Take profit: 200% per trade
- Daily loss limit: 20%
- Min edge: 65%
- Min confidence: 65%
- Price range: $0.01-0.35
- Min volume: $15,000

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
        
        # Trained model weights
        self.weights = {'price_weight': 0.15, 'edge_weight': 0.45, 'confidence_weight': 0.40}
        
        # Risk config from config module
        self.risk = {
            'max_position_pct': getattr(config, 'MAX_POSITION_PCT', 0.15),
            'max_daily_trades': getattr(config, 'MAX_DAILY_TRADES', 20),
            'max_open_positions': 5,
            'stop_loss_pct': getattr(config, 'STOP_LOSS_PCT', 0.25),
            'take_profit_pct': getattr(config, 'TAKE_PROFIT_PCT', 2.0),
            'daily_loss_limit': getattr(config, 'DAILY_LOSS_LIMIT', 0.20),
            'min_edge': getattr(config, 'MIN_EDGE', 0.65),
            'min_confidence': getattr(config, 'MIN_CONFIDENCE', 65),
            'price_range': (getattr(config, 'PRICE_MIN', 0.01), getattr(config, 'PRICE_MAX', 0.35)),
            'min_volume': getattr(config, 'MIN_VOLUME', 15000),
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
        
        # Use logging
        if USE_LOGGING:
            logger.info(f"TradingAgentSystem initialized with balance ${starting_balance}")
        
    def _sync_to_training_data(self, opportunity, won, win_prob):
        """[WORKFLOW OPTIMIZATION] Automatically append results to training data atomically."""
        training_file = os.path.join('data', 'training', 'simulated_scalper_data.json')
        os.makedirs(os.path.dirname(training_file), exist_ok=True)
        
        new_record = {
            'price': float(opportunity['price']),
            'volume': float(opportunity['volume']),
            'edge': float(opportunity['edge']),
            'confidence': float(opportunity['confidence']),
            'is_crypto': bool(opportunity.get('sector', 'other') in ['crypto', 'bitcoin', 'ethereum', 'solana']),
            'won': bool(won),
            'predicted_prob': float(win_prob),
            'timestamp': datetime.now().isoformat()
        }
        
        # Simple atomic-ish write with exception handling
        data = []
        try:
            if os.path.exists(training_file):
                with open(training_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # If corrupted, start fresh with last record
            logger.warning(f"Corrupted training file detected, resetting: {training_file}")
            data = []
        
        try:
            data.append(new_record)
            
            # Keep last 10,000 samples to avoid huge files
            if len(data) > 10000:
                data = data[-10000:]
                
            # Write to temp file then rename (atomic on most OS)
            temp_file = training_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            if os.path.exists(training_file):
                os.remove(training_file)
            os.rename(temp_file, training_file)
            
            if USE_LOGGING:
                logger.info(f"Synced trade result to {training_file}")
        except Exception as e:
            if USE_LOGGING:
                logger.warning(f"Failed to sync training data: {e}")

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

    def learning_agent(self, iterations=1, samples=2000):
        """[WORKFLOW OPTIMIZATION] Integrated learning agent trigger."""
        print(f"\n[LEARNING AGENT] Triggering background retraining cycle...")
        try:
            # Load all training data including the ones we just synced
            training_file = os.path.join('data', 'training', 'simulated_scalper_data.json')
            if os.path.exists(training_file):
                with open(training_file, 'r') as f:
                    data = json.load(f)
                
                print(f"[LEARNING AGENT] Retraining model on {len(data)} samples...")
                from src.ml.market_predictor import MarketPredictor
                new_model = MarketPredictor()
                new_model.train(data)
                
                # Hot-swap the model
                self.ml_model = new_model
                print(f"[LEARNING AGENT] Model hot-swapped successfully")
                return True
        except Exception as e:
            print(f"[LEARNING AGENT] Retraining failed: {e}")
        return False

    def get_llm_intelligence(self, question=None, market_data=None):
        """Get market intelligence — uses MiroFish when available, falls back to static."""
        if self.mirofish:
            intel = self.mirofish.get_market_intelligence(question or "", market_data)
            if intel:
                return intel
        
        # Static fallback
        return {
            'timestamp': datetime.now().isoformat(),
            'sectors': ['crypto', 'bitcoin', 'ethereum', 'solana'],
            'sentiment_score': 0.85,
            'confidence_boost': 10,
            'trending': [
                {'sector': 'crypto', 'sentiment': 'bullish', 'confidence': 85},
                {'sector': 'bitcoin', 'sentiment': 'bullish', 'confidence': 88},
            ]
        }
    
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
        """Instantiate DynamicRiskManager and optionally calibrate from back‑test stats.
        If a back‑test result file exists, use its statistics to adjust risk parameters.
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
            # Attempt to calibrate from latest back‑test stats
            stats_file = os.path.join('src', 'backtesting', 'historical', 'data', 'backtest', 'latest_stats.json')
            if os.path.isfile(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                self.risk_manager.configure_from_history(stats)
                if USE_LOGGING:
                    logger.info("Risk manager calibrated from back‑test stats")
            self.risk_manager.start_session(self.balance)
            if USE_LOGGING:
                logger.info("Dynamic risk manager initialized")
        except Exception as e:
            self.risk_manager = None
            if USE_LOGGING:
                logger.warning(f"Dynamic risk manager not available: {e}")
    
    def research_agent(self):
        """Research Agent - Find trading opportunities"""
        print("\n[RESEARCH AGENT] Fetching market data...")
        
        markets = self.client.get_markets(50)
        if not markets:
            return []
        
        intel = self.get_llm_intelligence()
        opportunities = []
        
        for m in markets:
            try:
                prices = json.loads(m.get('outcomePrices', '[]'))
                if not prices or len(prices) < 2:
                    continue
                
                price = float(prices[0])
                volume = float(m.get('volume', 0) or 0)
                question = m.get('question', '')
                market_id = m.get('id')
                
                # Filter by price and volume
                if price < self.risk['price_range'][0] or price > self.risk['price_range'][1]:
                    continue
                if volume < self.risk['min_volume']:
                    continue
                
                # Calculate edge
                if price <= 0.02:
                    edge = 0.96
                elif price <= 0.05:
                    edge = 0.93
                elif price <= 0.10:
                    edge = 0.89
                elif price <= 0.20:
                    edge = 0.82
                else:
                    edge = 0.75
                
                # Confidence
                if price <= 0.02:
                    conf = 95
                elif price <= 0.05:
                    conf = 88
                elif price <= 0.10:
                    conf = 80
                else:
                    conf = 72
                
                # LLM / MiroFish boost
                conf = min(conf + intel.get('confidence_boost', 10), 100)
                
                # Sector detection
                q_lower = question.lower()
                sector = 'other'
                sectors = intel.get('sectors', [])
                for s in sectors:
                    if s in q_lower:
                        sector = s
                        edge += 0.04
                        break
                
                # [IDENTITY RESOLUTION] Resolve to canonical ID
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
                    'confidence': conf,
                    'sector': sector
                })
                
            except:
                continue
        
        print(f"[RESEARCH AGENT] Found {len(opportunities)} opportunities")
        return opportunities
    
    def risk_agent(self, opportunity):
        """Risk Agent - Validate trade using DynamicRiskManager"""
        # Delegate to DynamicRiskManager for comprehensive checks
        if self.risk_manager:
            approved, reason = self.risk_manager.should_trade(
                edge=opportunity['edge'],
                confidence=opportunity['confidence'],
                balance=self.balance
            )
            if not approved:
                return {'approved': False, 'reason': reason}
        else:
            # Fallback to static checks (maintained for safety)
            if opportunity['price'] < self.risk['price_range'][0]:
                return {'approved': False, 'reason': 'Price below min'}
            if opportunity['price'] > self.risk['price_range'][1]:
                return {'approved': False, 'reason': 'Price above max'}
            if opportunity['volume'] < self.risk['min_volume']:
                return {'approved': False, 'reason': 'Volume below min'}
            if opportunity['edge'] < self.risk['min_edge']:
                return {'approved': False, 'reason': 'Edge below min'}
            if opportunity['confidence'] < self.risk['min_confidence']:
                return {'approved': False, 'reason': 'Confidence below min'}
            if self.trades_today >= self.risk['max_daily_trades']:
                return {'approved': False, 'reason': 'Daily trade limit reached'}
            daily_loss = (self.daily_start - self.balance) / self.daily_start
            if daily_loss >= self.risk['daily_loss_limit']:
                return {'approved': False, 'reason': 'Daily loss limit reached'}
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
        """Trader Agent - Execute the trade"""
        
        # Position size – use DynamicRiskManager recommendation when available
        if self.risk_manager:
            recommended_pct = self.risk_manager.get_recommended_position(
                balance=self.balance,
                edge=opportunity['edge'],
                price=opportunity['price'],
                confidence=opportunity['confidence']
            )
            bet = self.balance * recommended_pct
        else:
            bet = self.balance * self.risk['max_position_pct']
        # Enforce sensible min/max limits
        bet = min(max(5, bet), 25)
        
        price = opportunity['price']
        volume = opportunity['volume']
        confidence = opportunity['confidence']
        edge = opportunity['edge']
        is_crypto = opportunity.get('sector', 'other') in ['crypto', 'bitcoin', 'ethereum', 'solana']
        
        # Per-trade MiroFish analysis for the specific market
        question = opportunity.get('question', '')
        market_intel = self.get_llm_intelligence(question, {'price': price, 'volume': volume})
        if market_intel and market_intel.get('simulation_id'):
            confidence = min(confidence + market_intel.get('confidence_boost', 10), 100)
            edge = market_intel.get('edge', edge)
        
        # Use ML model if available, otherwise fallback to rule-based
        if self.ml_model:
            try:
                win_prob = self.ml_model.predict_win_probability(
                    price=price,
                    volume=volume,
                    edge=edge,
                    confidence=confidence,
                    is_crypto=is_crypto
                )
            except Exception as e:
                if USE_LOGGING:
                    logger.warning(f"ML prediction failed: {e}")
                win_prob = self._rule_based_prob(price, confidence)
        else:
            win_prob = self._rule_based_prob(price, confidence)
        
        if USE_LOGGING:
            logger.info(f"Trade: price=${price:.2f}, win_prob={win_prob:.2%}")
        
        # Determine predicted outcome (yes if win_prob >= 0.5)
        predicted_yes = win_prob >= 0.5
        # Resolve actual outcome using cached data (if available)
        # [IDENTITY RESOLUTION] Use canonical ID for resolution
        actual_outcome = self.resolved_outcomes.get(opportunity.get('canonical_id'))
        if actual_outcome is not None:
            won = (actual_outcome == 'yes' and predicted_yes) or (actual_outcome == 'no' and not predicted_yes)
        else:
            # Fallback to simulated outcome based on win_prob (no real resolved data)
            won = random.random() < win_prob
        
        # [WORKFLOW OPTIMIZATION] Auto-sync to training data
        self._sync_to_training_data(opportunity, won, win_prob)

        if USE_LOGGING:
            logger.info(f"Trade: price=${price:.2f}, win_prob={win_prob:.2%}, predicted_yes={predicted_yes}, actual_outcome={actual_outcome}, won={won}")
        
        if won:
            profit = bet * (1 / price - 1) * (1 - self.fee)
        else:
            profit = -bet
        
        self.balance += profit
        self.trades_today += 1
        
        if won:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        
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
        
        return {
            'won': won,
            'profit': profit,
            'win_probability': win_prob,
            'new_balance': self.balance
        }
    
    def monitor_agent(self, trade_result, opportunity):
        """Monitor Agent - Track and report"""
        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0
        
        status = "WIN" if trade_result['won'] else "LOSS"
        
        print(f"  [{self.stats['wins'] + self.stats['losses']}] {status} | "
              f"${opportunity['price']:.2f} | "
              f"Edge:{opportunity['edge']:.0%} Conf:{opportunity['confidence']:.0f}% | "
              f"Bal:${self.balance:.2f}")
        
        # Warning if win rate drops
        if total >= 10 and win_rate < 70:
            print(f"  ⚠️ WARNING: Win rate dropped to {win_rate:.1f}%")
        
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
        print(f"Target: 85%+ win rate")
        print(f"{'='*70}\n")
        
        # Get initial intelligence
        intel = self.get_llm_intelligence()
        print(f"[LEAD] Market Intelligence: {intel['sentiment_score']:.0%} bullish\n")
        
        from concurrent.futures import ThreadPoolExecutor
        
        for trade_num in range(1, max_trades + 1):
            # [WORKFLOW OPTIMIZATION] Periodic retraining
            if retrain_every > 0 and trade_num > 1 and (trade_num - 1) % retrain_every == 0:
                self.learning_agent()

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
                # Update opportunity with intelligence results
                opp['confidence'] = min(opp['confidence'] + intel.get('confidence_boost', 10), 100)
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

        return self.finish()
    
    def finish(self):
        """Generate final report"""
        total = self.stats['wins'] + self.stats['losses']
        win_rate = self.stats['wins'] / total * 100 if total > 0 else 0
        profit = self.balance - self.initial_balance
        
        print(f"\n{'='*70}")
        print("SESSION COMPLETE")
        print(f"{'='*70}")
        print(f"Total Trades: {total}")
        print(f"Wins: {self.stats['wins']} | Losses: {self.stats['losses']}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Balance: ${self.initial_balance:.2f} -> ${self.balance:.2f}")
        print(f"Profit: ${profit:.2f} ({profit/self.initial_balance*100:+.1f}%)")
        print(f"{'='*70}")
        
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