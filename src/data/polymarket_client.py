# Polymarket API Client with DNS Patch

import requests
import socket
import time
from typing import Dict, List, Optional
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pre-resolve blocked domains
RESOLVED_IPS = {
    "gamma-api.polymarket.com": "172.64.153.51",
    "api.polymarket.com": "172.64.153.51",
}

# Patch DNS
if not hasattr(socket, '_polymarket_patched'):
    _orig = socket.getaddrinfo
    
    def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host in RESOLVED_IPS:
            return [(socket.AF_INET, type, proto, '', (RESOLVED_IPS[host], port))]
        return _orig(host, port, family, type, proto, flags)
    
    socket.getaddrinfo = _patched_getaddrinfo
    socket._polymarket_patched = True
    logger.info("[DNS] Polymarket DNS patched")


class PolymarketClient:
    def __init__(self, api_key: str = None):
        # Choose sandbox or production based on env var
        sandbox = os.getenv('POLYMARKET_SANDBOX', 'false').lower() == 'true'
        self.base_url = "https://sandbox-api.polymarket.com" if sandbox else "https://gamma-api.polymarket.com"
        # Keep any optional Gamma bearer key separate from the CLOB auth key.
        self.api_key = api_key or os.getenv('POLYMARKET_GAMMA_API_KEY', '')
        self.session = requests.Session()
        self.session.trust_env = False
        # Keep SSL verification on for safety; can be overridden via env if needed
        self.session.verify = os.getenv('POLYMARKET_VERIFY_SSL', 'true').lower() == 'true'
        self.headers = {
            'User-Agent': 'PolymarketBot/1.0',
            'Accept': 'application/json'
        }
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        # Internal retry configuration
        self.max_retries = int(os.getenv('POLYMARKET_MAX_RETRIES', '3'))

    # Existing request helper remains unchanged

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Perform an HTTP request with exponential back‑off retries.
        Returns the Response on success or None after exhausting retries.
        """
        delay = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=15, **kwargs)
                if resp.status_code == 200:
                    return resp
                else:
                    logger.warning(f"Polymarket API returned {resp.status_code} on attempt {attempt} for {url}")
            except Exception as e:
                logger.error(f"Polymarket request error on attempt {attempt} for {url}: {e}")
            if attempt < self.max_retries:
                logger.info(f"Retrying Polymarket request in {delay}s…")
                time.sleep(delay)
                delay *= 2
        return None

    # ---------- Order & Account API ----------
    def place_order(self, market_id: str, side: str, price: float, size: float) -> Optional[Dict]:
        """Place a limit order on a market. Returns order info or None on failure.
        `side` should be 'yes' or 'no'. Uses sandbox if enabled.
        """
        payload = {
            'marketId': market_id,
            'side': side,
            'price': price,
            'size': size,
        }
        resp = self._request_with_retry('POST', f"{self.base_url}/orders", json=payload, headers=self.headers)
        if resp:
            return resp.json()
        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order. Returns True if successful."""
        resp = self._request_with_retry('DELETE', f"{self.base_url}/orders/{order_id}", headers=self.headers)
        return resp is not None and resp.status_code == 200

    def get_balance(self) -> Optional[float]:
        """Fetch account balance. Returns balance value or None on failure."""
        resp = self._request_with_retry('GET', f"{self.base_url}/account/balance", headers=self.headers)
        if resp:
            data = resp.json()
            return float(data.get('available', 0))
        return None

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Retrieve status of a specific order."""
        resp = self._request_with_retry('GET', f"{self.base_url}/orders/{order_id}", headers=self.headers)
        if resp:
            return resp.json()
        return None
    
    def get_markets(self, limit: int = 50, params: Optional[Dict] = None) -> List[Dict]:
        request_params = {"limit": limit, "active": "true"}
        if params:
            request_params.update(params)

        resp = self._request_with_retry(
            "GET",
            f"{self.base_url}/markets",
            params=request_params,
            headers=self.headers,
        )
        if resp:
            data = resp.json()
            return data if isinstance(data, list) else data.get('markets', [])
        return []

    def get_market(self, market_id: str) -> Optional[Dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/markets/{market_id}",
                headers=self.headers,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Error: {e}")
        return None
    
    def get_trending(self, limit: int = 10) -> List[Dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/markets/trending",
                params={"limit": limit},
                headers=self.headers,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Error: {e}")
        return []


if __name__ == "__main__":
    logger.info("Fetching Polymarket data...")
    client = PolymarketClient()
    markets = client.get_markets(10)
    print(f"Got {len(markets)} markets")
    for m in markets[:3]:
        print(f"  - {m.get('question', 'N/A')[:50]}")
