"""
Market data routers backed by Polymarket connectors.
"""

import json
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Query
from pydantic import BaseModel

try:
    from ...data.connectors.clob import CLOBConnector
    from ...data.connectors.gamma import PolymarketAPI
except ImportError:
    from data.connectors.clob import CLOBConnector
    from data.connectors.gamma import PolymarketAPI


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_yes_no_prices(market: Dict) -> Tuple[float, float]:
    yes_price = _to_float(
        market.get("yes_price")
        or market.get("yesPrice")
        or market.get("probability")
        or market.get("lastTradePrice")
        or market.get("lastPrice")
    )
    no_price = _to_float(market.get("no_price") or market.get("noPrice"))

    outcomes = market.get("outcomes")
    if (yes_price == 0.0 or no_price == 0.0) and isinstance(outcomes, list) and len(outcomes) >= 2:
        # outcomes list may contain dicts with price keys or plain labels
        first = outcomes[0]
        second = outcomes[1]
        if isinstance(first, dict):
            if yes_price == 0.0:
                yes_price = _to_float(first.get("price"), yes_price)
        elif isinstance(first, str) and yes_price == 0.0:
            yes_price = _to_float(first, yes_price)
        if isinstance(second, dict):
            if no_price == 0.0:
                no_price = _to_float(second.get("price"), no_price)
        elif isinstance(second, str) and no_price == 0.0:
            no_price = _to_float(second, no_price)

    outcome_prices = market.get("outcomePrices")
    if (yes_price == 0.0 or no_price == 0.0) and outcome_prices is not None:
        parsed = outcome_prices
        if isinstance(outcome_prices, str):
            try:
                parsed = json.loads(outcome_prices)
            except json.JSONDecodeError:
                parsed = None
        if isinstance(parsed, list) and len(parsed) >= 2:
            if yes_price == 0.0:
                yes_price = _to_float(parsed[0], yes_price)
            if no_price == 0.0:
                no_price = _to_float(parsed[1], no_price)

    if no_price == 0.0 and 0.0 < yes_price <= 1.0:
        no_price = max(0.0, 1.0 - yes_price)

    return yes_price, no_price


class MarketResponse(BaseModel):
    id: str
    title: str
    description: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float


router = APIRouter()
gamma_api = PolymarketAPI()
clob_api = CLOBConnector()


def _normalize_market(market: Dict) -> Optional[MarketResponse]:
    market_id = str(
        market.get("id")
        or market.get("market_id")
        or market.get("conditionId")
        or market.get("slug")
        or ""
    )
    if not market_id:
        return None

    title = (
        market.get("title")
        or market.get("question")
        or market.get("name")
        or f"Market {market_id}"
    )
    description = market.get("description") or ""
    yes_price, no_price = _extract_yes_no_prices(market)

    volume = _to_float(
        market.get("volume")
        or market.get("volumeNum")
        or market.get("volume24hr")
        or market.get("liquidityClob")
    )
    liquidity = _to_float(
        market.get("liquidity")
        or market.get("liquidityNum")
        or market.get("liquidityClob")
    )

    return MarketResponse(
        id=market_id,
        title=str(title),
        description=str(description),
        yes_price=yes_price,
        no_price=no_price,
        volume=volume,
        liquidity=liquidity,
    )


@router.get("/", response_model=List[MarketResponse])
async def get_markets(limit: int = Query(default=20, ge=1, le=100)):
    """Return normalized market list from Polymarket Gamma API."""
    raw_markets = await gamma_api.get_markets(limit=limit)
    normalized = []
    for market in raw_markets:
        item = _normalize_market(market)
        if item:
            normalized.append(item)
    return normalized[:limit]


@router.get("/market/{market_id}", response_model=MarketResponse)
async def get_market_data(market_id: str):
    """Return normalized single market data from Polymarket Gamma API."""
    raw = await gamma_api.get_market(market_id)
    normalized = _normalize_market(raw)
    if normalized:
        return normalized

    # Graceful fallback object when API has no data.
    return MarketResponse(
        id=market_id,
        title=f"Market {market_id}",
        description="No live market data available for this ID.",
        yes_price=0.0,
        no_price=0.0,
        volume=0.0,
        liquidity=0.0,
    )


@router.get("/book/{market_id}")
async def get_market_orderbook(market_id: str):
    """Return orderbook data from CLOB/Gamma connectors."""
    clob_data = await clob_api.get_orderbook(market_id)
    gamma_book = await gamma_api.get_market_orderbook(market_id)
    return {
        "market_id": market_id,
        "clob_orderbook": clob_data,
        "gamma_orderbook": gamma_book,
    }
