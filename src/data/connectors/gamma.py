"""
Polymarket Gamma API connector.
"""

import os
from typing import Dict, List, Optional

import aiohttp


class PolymarketAPI:
    """Connector for Polymarket Gamma API market/trade data."""

    def __init__(self):
        # Gamma market data is public; keep the optional bearer key separate
        # from the CLOB trading credentials.
        self.api_key = os.getenv("POLYMARKET_GAMMA_API_KEY", "")
        self.base_url = os.getenv("POLYMARKET_GAMMA_BASE_URL", "https://gamma-api.polymarket.com")

    async def _get_json(self, path: str, params: Optional[Dict] = None):
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(f"{self.base_url}{path}", params=params, timeout=20) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
            except Exception:
                return None

    async def get_markets(self, limit: int = 50) -> List[Dict]:
        """Fetch markets. Handles both list and dict API response shapes."""
        data = await self._get_json("/markets", params={"limit": limit})
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            markets = data.get("markets")
            if isinstance(markets, list):
                return markets
        return []

    async def get_market(self, market_id: str) -> Dict:
        """Fetch one market by id."""
        data = await self._get_json(f"/markets/{market_id}")
        if isinstance(data, dict):
            return data
        return {}

    async def get_market_orderbook(self, market_id: str) -> Dict:
        """Fetch market orderbook from Gamma endpoint if available."""
        data = await self._get_json(f"/markets/{market_id}/book")
        if isinstance(data, dict):
            return data
        return {}

    async def get_trades(self, market_id: str, limit: int = 50) -> List[Dict]:
        """Fetch recent trades for a market."""
        data = await self._get_json(f"/markets/{market_id}/trades", params={"limit": limit})
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            trades = data.get("trades")
            if isinstance(trades, list):
                return trades
        return []
