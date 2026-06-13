"""
Normalized market state model for aggregating data from multiple sources.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class MarketState:
    """Represents the normalized state of a market."""

    market_id: str
    title: str
    description: str
    yes_price: float
    no_price: float
    yes_outcome: str
    no_outcome: str
    fee: float
    liquidity: float
    volume: float
    created_at: datetime
    expires_at: datetime
    market_type: str
    status: str
    image: str
    yes_bid_price: float
    yes_bid_size: float
    yes_ask_price: float
    yes_ask_size: float
    no_bid_price: float
    no_bid_size: float
    no_ask_price: float
    no_ask_size: float
    last_updated: datetime

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)

class MarketStateManager:
    """Manages the normalized market state from multiple data sources."""

    def __init__(self):
        self.markets = {}

    def update_from_gamma(self, gamma_data: Dict) -> None:
        """Update market state from Gamma API data."""
        # Implementation would go here
        pass

    def update_from_clob(self, clob_data: Dict) -> None:
        """Update market state from CLOB data."""
        # Get market ID from the clob_data
        pass

    def update_from_websocket(self, ws_data: Dict) -> None:
        """Update market state from WebSocket data."""
        # Implementation would go here
        pass

    def get_market_state(self, market_id: str) -> MarketState:
        """Get the current state of a market."""
        # Implementation would go here
        pass

    def get_all_markets(self) -> List[MarketState]:
        """Get all market states."""
        # Implementation would go here
        pass