"""
Live Trading Integration
Real Polymarket order execution
"""

import json
import os
import re
from datetime import datetime
from importlib.util import find_spec
from typing import Any, Dict, Optional

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

    return {
        "yes": float(odds[yes_key]),
        "no": float(odds[no_key]),
    }


def _extract_volume(market):
    for key in ("volume", "liquidity", "dailyVolume", "marketVolume"):
        value = _parse_float(market.get(key))
        if value > 0:
            return value
    return 0.0


def _env_enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _clear_proxy_env() -> None:
    for proxy_var in (
        "ALL_PROXY",
        "all_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
        "GIT_HTTP_PROXY",
        "GIT_HTTPS_PROXY",
    ):
        os.environ.pop(proxy_var, None)


def _extract_outcome_token_id(market: Dict, outcome: str) -> Optional[str]:
    """Return the CLOB token id for the selected YES/NO outcome."""
    wanted = _normalize_label(outcome)
    aliases = {
        "yes": {"yes", "y", "true"},
        "no": {"no", "n", "false"},
    }
    wanted_aliases = aliases.get(wanted, {wanted})
    token_map = {}

    outcomes = _normalize_sequence(market.get("outcomes") or [])
    clob_tokens = _normalize_sequence(
        market.get("clobTokenIds")
        or market.get("clob_token_ids")
        or market.get("clobTokenID")
        or []
    )

    for outcome_name, token_id in zip(outcomes, clob_tokens):
        token_map[_normalize_label(outcome_name)] = str(token_id)

    if len(clob_tokens) >= 2 and not token_map:
        token_map["yes"] = str(clob_tokens[0])
        token_map["no"] = str(clob_tokens[1])

    tokens = market.get("tokens") or market.get("outcomeTokens") or []
    if isinstance(tokens, str):
        try:
            tokens = json.loads(tokens)
        except json.JSONDecodeError:
            tokens = []

    if isinstance(tokens, list):
        for token in tokens:
            if not isinstance(token, dict):
                continue
            token_id = (
                token.get("token_id")
                or token.get("tokenId")
                or token.get("clobTokenId")
                or token.get("asset_id")
                or token.get("id")
            )
            token_outcome = token.get("outcome") or token.get("name")
            if token_id and token_outcome:
                token_map[_normalize_label(token_outcome)] = str(token_id)

    for label, token_id in token_map.items():
        if label in wanted_aliases:
            return token_id

    return None


def _serialize_sdk_response(response: Any) -> Dict:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "__dict__"):
        return dict(response.__dict__)
    return {"raw": str(response)}


# API configuration
class LiveTradingConfig:
    """Live trading configuration"""
    
    # Get from polymarket.com/settings/api
    API_KEY = os.getenv('POLYMARKET_API_KEY', '')
    API_SECRET = os.getenv('POLYMARKET_API_SECRET', '')
    API_PASSPHRASE = os.getenv('POLYMARKET_API_PASSPHRASE', '')
    
    # API endpoints
    BASE_URL = 'https://gamma-api.polymarket.com'
    ORDER_URL = f'{BASE_URL}/order'
    POSITIONS_URL = f'{BASE_URL}/positions'
    BALANCE_URL = f'{BASE_URL}/account'
    
    # Trading settings
    MIN_ORDER_SIZE = _parse_float(os.getenv('MIN_ORDER_SIZE'), 1.0)
    MAX_ORDER_SIZE = _parse_float(os.getenv('MAX_ORDER_SIZE'), 100.0)
    LIVE_TEST_ORDER_AMOUNT = _parse_float(os.getenv('LIVE_TEST_ORDER_AMOUNT'), 0.0)
    DEFAULT_SLIPPAGE = _parse_float(os.getenv('DEFAULT_SLIPPAGE'), 0.02)
    
    # Mode
    MODE = os.getenv('TRADING_MODE', 'paper')  # 'paper' or 'live'


class PolymarketOrderExecutor:
    """
    Execute real orders on Polymarket
    Supports both paper and live trading
    """
    
    def __init__(
        self,
        api_key: str = '',
        api_secret: str = '',
        api_passphrase: str = '',
        private_key: str = '',
        mode: str = 'paper',
    ):
        self.config = LiveTradingConfig()
        self.api_key = api_key or self.config.API_KEY
        self.api_secret = api_secret or self.config.API_SECRET
        self.api_passphrase = api_passphrase or self.config.API_PASSPHRASE
        self.private_key = private_key or os.getenv('PRIVATE_KEY', '')
        self.wallet_address = _first_env(
            "POLYMARKET_WALLET_ADDRESS",
            "POLYMARKET_DEPOSIT_WALLET",
            "DEPOSIT_WALLET_ADDRESS",
        )
        self.relayer_api_key = _first_env("POLYMARKET_RELAYER_API_KEY", "RELAYER_API_KEY")
        self.relayer_api_key_address = _first_env(
            "POLYMARKET_RELAYER_API_KEY_ADDRESS",
            "RELAYER_API_KEY_ADDRESS",
            "POLYMARKET_SIGNER_ADDRESS",
        )
        self.builder_code = _first_env("POLYMARKET_BUILDER_CODE", "POLYMARKET_DEVELOPER_CODE")
        self.allow_real_orders = _env_enabled("POLYMARKET_ALLOW_REAL_ORDERS")
        self.mode = mode
        self._sdk_client = None
        
        # Track orders
        self.order_history = []
        self.total_volume = 0
    
    def is_live_mode(self) -> bool:
        return self.mode == 'live'

    def sdk_installed(self) -> bool:
        return find_spec("polymarket") is not None

    def _create_sdk_client(self):
        """Create the official Polymarket SDK secure client on demand."""
        if self._sdk_client is not None:
            return self._sdk_client

        _clear_proxy_env()

        if not self.sdk_installed():
            raise RuntimeError(
                "polymarket-client is not installed. Install it with: "
                "pip install --pre polymarket-client"
            )

        if not self.private_key:
            raise RuntimeError("PRIVATE_KEY is required for live order signing")

        from polymarket import ApiKeyCreds, RelayerApiKey, SecureClient

        credentials = None
        if self.api_key and self.api_secret and self.api_passphrase:
            credentials = ApiKeyCreds.model_validate(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "passphrase": self.api_passphrase,
                }
            )

        relayer_key = None
        if self.relayer_api_key and self.relayer_api_key_address:
            relayer_key = RelayerApiKey(
                key=self.relayer_api_key,
                address=self.relayer_api_key_address,
            )

        self._sdk_client = SecureClient.create(
            private_key=self.private_key,
            wallet=self.wallet_address or None,
            credentials=credentials,
            api_key=relayer_key,
        )
        return self._sdk_client
    
    def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.is_live_mode():
            return {'balance': 0, 'mode': 'paper'}

        return {
            'balance': None,
            'mode': 'live',
            'connected': bool(self.private_key and self.wallet_address),
            'sdk_installed': self.sdk_installed(),
            'wallet': self.wallet_address,
            'real_orders_enabled': self.allow_real_orders,
        }
    
    def place_order(self, market_id: str, outcome: str, amount: float, 
                    price: float, side: str = 'buy',
                    token_id: Optional[str] = None) -> Dict:
        """
        Place an order on Polymarket
        
        Args:
            market_id: The market condition ID
            outcome: 'yes' or 'no'
            amount: Amount in dollars
            price: Current price of outcome
            side: 'buy' or 'sell'
            
        Returns:
            Order result with status, filled amount, etc.
        """
        # Paper trading simulation
        if not self.is_live_mode():
            return self._simulate_order(market_id, outcome, amount, price, side)
        
        return self._execute_live_order(market_id, outcome, amount, price, side, token_id)
    
    def _simulate_order(self, market_id: str, outcome: str, amount: float,
                        price: float, side: str) -> Dict:
        """Simulate order for paper trading"""
        # Calculate expected payout
        if side == 'buy':
            shares = amount / price
            payout = shares * (1 - price)  # Net payout if YES wins
            cost = amount
        else:
            shares = amount / price
            payout = shares * price  # If NO wins
            cost = amount
        
        order = {
            'order_id': f"paper_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'market_id': market_id,
            'outcome': outcome,
            'side': side,
            'amount': amount,
            'price': price,
            'shares': shares,
            'mode': 'paper',
            'status': 'filled',
            'timestamp': datetime.now().isoformat(),
            'payout': payout if side == 'buy' else cost
        }
        
        self.order_history.append(order)
        self.total_volume += amount
        
        return order
    
    def _execute_live_order(self, market_id: str, outcome: str, amount: float,
                           price: float, side: str,
                           token_id: Optional[str] = None) -> Dict:
        """Execute real order via API"""
        timestamp = datetime.now().isoformat()
        order_id = f"live_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        base_order = {
            'order_id': order_id,
            'market_id': market_id,
            'token_id': token_id,
            'outcome': outcome,
            'side': side,
            'amount': amount,
            'price': price,
            'mode': 'live',
            'timestamp': timestamp,
        }

        if not self.allow_real_orders:
            return {
                **base_order,
                'status': 'blocked',
                'error': 'Set POLYMARKET_ALLOW_REAL_ORDERS=true to allow real order submission',
            }

        if side.lower() != 'buy':
            return {
                **base_order,
                'status': 'error',
                'error': 'Only buy orders are supported by this live adapter',
            }

        if not token_id:
            return {
                **base_order,
                'status': 'error',
                'error': 'CLOB token_id is required for live order submission',
            }

        if amount < self.config.MIN_ORDER_SIZE:
            return {
                **base_order,
                'status': 'error',
                'error': f'Order amount must be at least ${self.config.MIN_ORDER_SIZE:.2f}',
            }

        if amount > self.config.MAX_ORDER_SIZE:
            return {
                **base_order,
                'status': 'error',
                'error': f'Order amount exceeds MAX_ORDER_SIZE=${self.config.MAX_ORDER_SIZE:.2f}',
            }

        try:
            client = self._create_sdk_client()
            response = client.place_market_order(
                token_id=str(token_id),
                side='BUY',
                amount=str(round(float(amount), 2)),
                order_type=os.getenv('POLYMARKET_MARKET_ORDER_TYPE', 'FOK'),
                builder_code=self.builder_code or None,
            )
            payload = _serialize_sdk_response(response)
            accepted = bool(payload.get('ok', payload.get('order_id')))

            order = {
                **base_order,
                'sdk_response': payload,
                'status': payload.get('status', 'submitted' if accepted else 'rejected'),
                'accepted': accepted,
            }
            self.order_history.append(order)
            self.total_volume += amount
            return order
        except Exception as exc:
            return {
                **base_order,
                'status': 'error',
                'error': str(exc),
            }
    
    def get_positions(self) -> list:
        """Get current positions"""
        if not self.is_live_mode():
            return []
        
        # Would call API for real positions
        return []
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        if not self.is_live_mode():
            return {'status': 'cancelled', 'mode': 'paper'}
        
        # Would call API to cancel
        return {'order_id': order_id, 'status': 'cancelled', 'mode': 'live'}
    
    def get_order_history(self, limit: int = 50) -> list:
        """Get order history"""
        return self.order_history[-limit:]
    
    def get_trading_summary(self) -> Dict:
        """Get trading summary"""
        total_orders = len(self.order_history)
        filled = sum(1 for o in self.order_history if o.get('status') == 'filled')
        
        return {
            'mode': self.mode,
            'total_orders': total_orders,
            'filled_orders': filled,
            'total_volume': self.total_volume,
            'is_live': self.is_live_mode()
        }


class TradingSession:
    """Manages a trading session with both paper and live modes"""
    
    def __init__(self, starting_balance: float = 100, mode: str = 'paper',
                 api_key: str = '', api_secret: str = '', api_passphrase: str = '', private_key: str = '',
                 enable_mirofish: Optional[bool] = None):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.mode = mode
        
        # Initialize executor
        self.executor = PolymarketOrderExecutor(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            private_key=private_key,
            mode=mode
        )
        
        # Trade history
        self.trades = []
        self.stats = {'wins': 0, 'losses': 0}
        self._last_signal = None
        self._last_signal_market_id = None
        self.mirofish = self._init_mirofish(enable_mirofish)

    def _init_mirofish(self, enable_mirofish: Optional[bool]) -> Optional[object]:
        """Initialize MiroFish if enabled and the backend is reachable."""
        if not MIROFISH_AVAILABLE:
            return None

        if enable_mirofish is None:
            enabled = os.getenv("MIROFISH_ENABLED", "true").lower() == "true"
        else:
            enabled = bool(enable_mirofish)

        if not enabled:
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
                return integrator
        except Exception as exc:
            print(f"[MiroFish] Init error: {exc}")

        return None

    def get_market_signal(self, market: Dict, price: float,
                          volume: Optional[float] = None) -> Optional[Dict]:
        """Build a normalized signal for the current market."""
        if not self.mirofish:
            return None

        question = market.get("question", "")
        prices = _extract_binary_prices(market)
        if prices:
            yes_price = prices["yes"]
            no_price = prices["no"]
        else:
            yes_price = max(0.01, min(0.99, float(price)))
            no_price = max(0.01, min(0.99, 1.0 - yes_price))

        try:
            signal = self.mirofish.build_trade_signal(
                question,
                market,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume if volume is not None else _extract_volume(market),
            )
        except Exception as exc:
            print(f"[MiroFish] Signal error: {exc}")
            return None

        self._last_signal = signal
        self._last_signal_market_id = market.get("id") or market.get("condition_id") or question
        return signal
    
    def execute_trade(self, market: Dict, price: float, edge: float,
                      confidence: float, win_prob: float,
                      market_data: Optional[Dict] = None,
                      signal: Optional[Dict] = None) -> Dict:
        """Execute a trade (paper or live)"""
        
        market_signal = signal
        if market_signal is None and self.mirofish:
            market_signal = self.get_market_signal(
                market,
                price,
                volume=_extract_volume(market_data or market),
            )

        selected_outcome = "yes"
        selected_price = max(price, 0.01)
        adjusted_win_prob = win_prob

        if market_signal:
            selected_outcome = market_signal.get("selected_side", "yes")
            selected_price = _parse_float(
                market_signal.get("selected_price"), default=selected_price
            )
            adjusted_win_prob = max(
                0.01,
                min(0.99, float(market_signal.get("predicted_prob", adjusted_win_prob))),
            )
            edge = max(edge, float(market_signal.get("edge", edge)))
            confidence = max(confidence, float(market_signal.get("confidence", confidence)))

        # Calculate position size from env caps. Live tests can force a fixed amount.
        max_position_pct = _parse_float(os.getenv("MAX_POSITION_PCT"), 0.15)
        min_order_size = self.executor.config.MIN_ORDER_SIZE
        max_order_size = self.executor.config.MAX_ORDER_SIZE
        fixed_live_amount = self.executor.config.LIVE_TEST_ORDER_AMOUNT

        if self.mode == "live" and fixed_live_amount > 0:
            bet = fixed_live_amount
        else:
            bet = min(self.balance * max_position_pct, max_order_size)

        if market_signal and not (self.mode == "live" and fixed_live_amount > 0):
            signal_boost = max(0.0, min(float(market_signal.get("score", 0.0)), 0.25))
            bet *= 1.0 + signal_boost

        bet = round(max(min_order_size, min(max_order_size, bet)), 2)
        token_id = _extract_outcome_token_id(market, selected_outcome)

        if self.mode == "live":
            max_live_trades = int(_parse_float(
                os.getenv("MAX_LIVE_TRADES", os.getenv("MAX_DAILY_TRADES", "1")),
                1,
            ))
            submitted_live_trades = sum(
                1
                for trade in self.trades
                if trade.get("mode") == "live"
                and trade.get("order_status") not in {"blocked", "error", "skipped"}
            )
            if submitted_live_trades >= max_live_trades:
                trade = {
                    'order_id': None,
                    'market': market.get('question', '')[:50],
                    'price': selected_price,
                    'token_id': token_id,
                    'bet': bet,
                    'won': None,
                    'profit': 0.0,
                    'edge': edge,
                    'confidence': confidence,
                    'selected_outcome': selected_outcome,
                    'signal_source': market_signal.get('source') if market_signal else 'fallback',
                    'signal_score': market_signal.get('score') if market_signal else None,
                    'mirofish_consensus_yes_pct': market_signal.get('consensus_yes_pct') if market_signal else None,
                    'mode': self.mode,
                    'order_status': 'skipped',
                    'error': f'MAX_LIVE_TRADES={max_live_trades} reached',
                    'timestamp': datetime.now().isoformat()
                }
                self.trades.append(trade)
                return trade
        
        # Place order via executor
        order = self.executor.place_order(
            market_id=market.get('id', 'unknown'),
            outcome=selected_outcome,
            amount=bet,
            price=selected_price,
            side='buy',
            token_id=token_id,
        )
        
        if self.mode == 'paper':
            # Simulate outcome based on win probability
            import random

            won = random.random() < adjusted_win_prob
            
            if won:
                profit = bet * (1 / selected_price - 1) * 0.93  # 7% fee
            else:
                profit = -bet
            
            self.balance += profit
            
            if won:
                self.stats['wins'] += 1
            else:
                self.stats['losses'] += 1
        else:
            won = None
            profit = 0.0
        
        trade = {
            'order_id': order.get('order_id'),
            'market': market.get('question', '')[:50],
            'price': selected_price,
            'token_id': token_id,
            'bet': bet,
            'won': won,
            'profit': profit,
            'edge': edge,
            'confidence': confidence,
            'selected_outcome': selected_outcome,
            'signal_source': market_signal.get('source') if market_signal else 'fallback',
            'signal_score': market_signal.get('score') if market_signal else None,
            'mirofish_consensus_yes_pct': market_signal.get('consensus_yes_pct') if market_signal else None,
            'mode': self.mode,
            'order_status': order.get('status'),
            'timestamp': datetime.now().isoformat()
        }
        
        self.trades.append(trade)
        
        return trade
    
    def get_session_summary(self) -> Dict:
        """Get session summary"""
        total = self.stats['wins'] + self.stats['losses']
        win_rate = (self.stats['wins'] / total * 100) if total > 0 else 0
        
        return {
            'mode': self.mode,
            'starting_balance': self.starting_balance,
            'current_balance': self.balance,
            'total_trades': total,
            'wins': self.stats['wins'],
            'losses': self.stats['losses'],
            'win_rate': win_rate,
            'total_profit': self.balance - self.starting_balance,
            'executor_status': self.executor.get_trading_summary()
        }


def create_live_session(
    api_key: str,
    api_secret: str,
    api_passphrase: str = '',
    private_key: str = '',
    starting_balance: float = 100,
    enable_mirofish: Optional[bool] = None,
):
    """Create a live trading session"""
    return TradingSession(
        starting_balance=starting_balance,
        mode='live',
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        private_key=private_key,
        enable_mirofish=enable_mirofish,
    )


def create_paper_session(starting_balance: float = 100, enable_mirofish: Optional[bool] = None):
    """Create a paper trading session"""
    return TradingSession(
        starting_balance=starting_balance,
        mode='paper',
        enable_mirofish=enable_mirofish,
    )


if __name__ == "__main__":
    # Test paper trading
    session = create_paper_session(100)
    
    # Simulate a trade
    market = {'id': 'test_123', 'question': 'Will BTC hit $100k?'}
    trade = session.execute_trade(market, 0.05, 0.92, 85, 0.93)
    
    print(f"Trade executed: {trade['won']} | Profit: ${trade['profit']:.2f}")
    print(f"Balance: ${session.balance:.2f}")
    print(f"Summary: {session.get_session_summary()}")
