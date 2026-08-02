"""
Market Data Connector for Polymarket

Safe data-only connection (no trading execution)
Features:
- Real-time market data
- Historical data access
- Rate limiting
- Error handling
- Paper trading mode
"""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import os


# Set up logging
logger = logging.getLogger(__name__)


class MarketDataConnector:
    """
    Safe market data connector for Polymarket.

    This class provides read-only access to market data without
    the ability to execute trades. Designed for paper trading
    and backtesting purposes.
    """

    def __init__(self, api_key: str = "", base_url: str = "https://polymarket.com/api/v1"):
        """
        Initialize the market data connector.

        Args:
            api_key: Polymarket API key (optional for public endpoints)
            base_url: Base API URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()

        # Set headers
        self.session.headers.update({
            'User-Agent': 'PolymarketTradingBot/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'

        # Rate limiting
        self.last_request_time = 0
        self.request_delay = 0.1  # 100ms between requests

        # Local cache for testing
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(exist_ok=True)

    def _rate_limit(self):
        """Enforce rate limiting to avoid API bans."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    def _get_cache_file(self, endpoint: str) -> Path:
        """Get cache file path for an endpoint."""
        safe_name = endpoint.replace('/', '_').replace('?', '_').replace('&', '_')
        return self.cache_dir / f"{safe_name}.json"

    def _load_from_cache(self, endpoint: str) -> Optional[Dict]:
        """Load data from cache if available."""
        cache_file = self._get_cache_file(endpoint)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Cache load error for {endpoint}: {e}")
        return None

    def _save_to_cache(self, endpoint: str, data: Dict):
        """Save data to cache."""
        cache_file = self._get_cache_file(endpoint)
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Cache save error for {endpoint}: {e}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_cache: bool = True,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> Optional[Dict]:
        """Make an API request with retry + exponential back-off."""
        url = f"{self.base_url}/{endpoint}"

        if use_cache:
            cached = self._load_from_cache(endpoint)
            if cached:
                return cached

        last_exc = None
        for attempt in range(retries):
            try:
                self._rate_limit()
                if method.upper() == "GET":
                    response = self.session.get(url, params=params)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=data, params=params)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code == 200:
                    result = response.json()
                    self._save_to_cache(endpoint, result)
                    return result

                logger.warning(f"API {response.status_code} on attempt {attempt+1}: {response.text[:120]}")
                if response.status_code in (429, 503):
                    time.sleep(backoff * (2 ** attempt))

            except Exception as e:
                last_exc = e
                logger.warning(f"Request attempt {attempt+1} failed: {e}")
                time.sleep(backoff * (2 ** attempt))

        logger.error(f"All {retries} attempts failed for {url}. Last error: {last_exc}")
        return None

    def health_check(self) -> Dict:
        """Check connectivity to the Polymarket API. Returns status dict."""
        import time as _t
        start = _t.monotonic()
        try:
            resp = self.session.get(
                f"{self.base_url}/markets",
                params={"limit": 1},
                timeout=5,
            )
            latency_ms = round((_t.monotonic() - start) * 1000, 1)
            ok = resp.status_code == 200
            return {"healthy": ok, "status_code": resp.status_code, "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = round((_t.monotonic() - start) * 1000, 1)
            return {"healthy": False, "error": str(e), "latency_ms": latency_ms}

    def get_markets(self, limit: int = 50) -> List[Dict]:
        """
        Get list of available markets.

        Args:
            limit: Maximum number of markets to return

        Returns:
            List of market dictionaries
        """
        endpoint = f"markets?limit={limit}"
        data = self._make_request("GET", endpoint)

        if data and 'markets' in data:
            return data['markets']

        return []

    def get_market_details(self, market_id: str) -> Optional[Dict]:
        """
        Get details for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            Market details dictionary
        """
        endpoint = f"markets/{market_id}"
        return self._make_request("GET", endpoint)

    def get_market_history(
        self,
        market_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict]:
        """
        Get historical price data for a market.

        Args:
            market_id: Market identifier
            start_time: ISO format start time
            end_time: ISO format end time

        Returns:
            List of historical price entries
        """
        # Note: This would require a real API endpoint
        # For now, return sample data for testing
        logger.warning("get_market_history not implemented - returning sample data")

        return [
            {
                "timestamp": "2023-01-01T10:00:00Z",
                "price": 0.60,
                "volume": 100000
            },
            {
                "timestamp": "2023-01-01T11:00:00Z",
                "price": 0.65,
                "volume": 150000
            }
        ]

    def get_user_positions(self) -> List[Dict]:
        """
        Get user's current positions (paper trading mode).

        Returns:
            List of position dictionaries
        """
        # In paper trading mode, return empty list
        logger.info("Paper trading mode - no real positions")
        return []

    def paper_trade(
        self,
        market_id: str,
        amount: float,
        side: str,
        price: float
    ) -> Dict:
        """
        Execute a paper trade (simulation only).

        Args:
            market_id: Market identifier
            amount: Trade amount
            side: 'buy' or 'sell'
            price: Execution price

        Returns:
            Simulated trade result
        """
        if side not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {side}")

        # Simulate trade execution
        fee = amount * 0.007  # 0.7% fee
        slippage = amount * 0.005  # 0.5% slippage

        result = {
            'market_id': market_id,
            'timestamp': datetime.utcnow().isoformat(),
            'side': side,
            'amount': amount,
            'price': price,
            'fee': fee,
            'slippage': slippage,
            'status': 'simulated'
        }

        logger.info(f"Paper trade executed: {side} {amount} of {market_id} at {price}")
        return result


class HistoricalDataLoader:
    """
    Load historical data from local files for backtesting.
    """

    def __init__(self, data_dir: str = "data/historical"):
        """Initialize with data directory."""
        self.data_dir = Path(data_dir)
        self.historical_data = {}

    def load_all_data(self):
        """Load all historical data files."""
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return

        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    market_data = json.load(f)
                    market_id = json_file.stem
                    self.historical_data[market_id] = market_data
                    logger.info(f"Loaded historical data: {market_id}")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

    def get_data_for_market(self, market_id: str) -> Optional[List[Dict]]:
        """Get historical data for a specific market."""
        return self.historical_data.get(market_id)


if __name__ == "__main__":
    print("MarketDataConnector initialized")
    print("Use for safe market data access (no trading execution)")