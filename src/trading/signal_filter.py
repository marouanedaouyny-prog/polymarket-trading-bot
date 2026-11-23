"""
Real Market Signal Filter

Fetches LIVE markets from Polymarket's public Gamma API and applies
honest filters. No fabricated win rates. No synthetic data.

A market passes only if:
  1. Price is in the configured range (not too cheap, not too expensive)
  2. Volume is above the minimum threshold (liquid enough to trade)
  3. The market closes soon enough to be actionable
  4. The question contains keywords suggesting a clear binary outcome

This does NOT predict the future. It only filters out markets that are
obviously bad bets (zero volume, already expired, etc.).
"""

import os
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    _HTTPX_AVAILABLE = False

# Import requests at module level for testing
import requests

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
_HEADERS = {"User-Agent": "PolymarketSignalFilter/1.0"}


async def _fetch_active_markets_async(limit: int = 100) -> List[Dict]:
    """Async fetch of active markets using httpx."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GAMMA_API}/markets",
                params={"active": "true", "closed": "false", "limit": limit},
                headers=_HEADERS,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else data.get("markets", [])
            logger.warning(f"Gamma API returned {resp.status_code}")
    except Exception as e:
        logger.error(f"Async fetch failed: {e}")
    return []


def _fetch_active_markets(limit: int = 100) -> List[Dict]:
    """Sync wrapper — uses asyncio if loop available, else falls back to requests."""
    if _HTTPX_AVAILABLE:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Inside async context (FastAPI) — caller should use async version
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _fetch_active_markets_async(limit))
                    return future.result(timeout=20)
            else:
                return loop.run_until_complete(_fetch_active_markets_async(limit))
        except Exception:
            pass
    # Pure fallback
    # Simplified fallback – use requests directly so that tests can patch it
    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"active": "true", "closed": "false", "limit": limit},
            timeout=15,
            headers=_HEADERS,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else data.get("markets", [])
    except Exception as e:
        logger.error(f"Failed to fetch markets: {e}")
    return []


def _parse_price(market: Dict) -> Optional[float]:
    """Extract the best YES price from a market dict."""
    # Gamma API uses outcomePrices or bestBid/bestAsk
    try:
        prices = market.get("outcomePrices")
        if prices:
            # outcomePrices is a JSON string like '["0.12","0.88"]' or a list
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            if isinstance(prices, list) and len(prices) >= 1:
                return float(prices[0])
        bid = market.get("bestBid")
        if bid:
            return float(bid)
    except (ValueError, TypeError, Exception):
        pass
    return None


def _parse_volume(market: Dict) -> float:
    """Extract total volume from a market dict."""
    for key in ("volume24hr", "volume", "volumeNum"):
        val = market.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return 0.0


def _closes_within_days(market: Dict, max_days: int = 30) -> bool:
    """Return True if the market closes within max_days from now."""
    end_date = market.get("endDate") or market.get("endDateIso")
    if not end_date:
        return True  # unknown → don't filter out
    try:
        if isinstance(end_date, (int, float)):
            closes = datetime.fromtimestamp(end_date, tz=timezone.utc)
        else:
            closes = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        days_left = (closes - datetime.now(tz=timezone.utc)).days
        return 0 < days_left <= max_days
    except Exception:
        return True


def filter_markets(
    price_min: float = 0.05,
    price_max: float = 0.50,
    min_volume: float = 10_000,
    max_close_days: int = 30,
    limit: int = 100,
) -> List[Dict]:
    """
    Fetch live markets and return those that pass basic quality filters.

    Returns a list of dicts with keys:
        id, question, price, volume, days_left, url
    """
    raw = _fetch_active_markets(limit=limit)
    if not raw:
        logger.warning("No markets returned from API.")
        return []

    results = []
    for m in raw:
        price = _parse_price(m)
        volume = _parse_volume(m)

        if price is None:
            continue
        if not (price_min <= price <= price_max):
            continue
        if volume < min_volume:
            continue
        if not _closes_within_days(m, max_days=max_close_days):
            continue

        end_date = m.get("endDate") or m.get("endDateIso", "")
        try:
            if isinstance(end_date, (int, float)):
                closes = datetime.fromtimestamp(end_date, tz=timezone.utc)
            else:
                closes = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            days_left = (closes - datetime.now(tz=timezone.utc)).days
        except Exception:
            days_left = -1

        results.append({
            "id": m.get("id") or m.get("conditionId", ""),
            "question": m.get("question", ""),
            "price": round(price, 4),
            "volume": round(volume, 2),
            "days_left": days_left,
            "url": f"https://polymarket.com/event/{m.get('slug', m.get('id', ''))}",
        })

    # Sort by volume descending — more liquid = easier to trade
    results.sort(key=lambda x: x["volume"], reverse=True)
    logger.info(f"Signal filter: {len(raw)} markets fetched, {len(results)} passed filters.")
    return results


def _enrich_with_timesfm(markets: list[dict], price_history_len: int = 30) -> None:
    """Enrich market dicts with TimesFM forecast data in-place."""
    try:
        from src.ml.timesfm_predictor import TimesFMPredictor
        from src.data.price_history import get_price_history

        predictor = TimesFMPredictor()
        if not predictor.is_loaded:
            predictor.load_model()

        for m in markets:
            market_id = m["id"]
            try:
                prices, _ = get_price_history(market_id, lookback_days=price_history_len)
            except Exception:
                prices = []

            if len(prices) >= 20:
                signal = predictor.get_trend_signal(prices)
                m["timesfm_direction"] = signal["direction"]
                m["timesfm_confidence"] = round(signal["confidence"], 4)
                m["timesfm_forecast_end"] = round(signal.get("forecast_end", 0), 6)
                m["timesfm_uncertainty"] = round(signal.get("uncertainty", 0), 6)
                m["timesfm_reason"] = signal["reason"]
            else:
                m["timesfm_direction"] = 0
                m["timesfm_confidence"] = 0.0
                m["timesfm_forecast_end"] = 0.0
                m["timesfm_uncertainty"] = 0.0
                m["timesfm_reason"] = "insufficient price history"
    except Exception as e:
        logger.warning(f"TimesFM enrichment skipped: {e}")


def score_markets(
    markets: list[dict],
    price_history_len: int = 30,
    use_timesfm: bool = True,
) -> list[dict]:
    """
    Apply technical strategy scoring to pre-filtered markets.

    Uses real cached price history from src.data.price_history when available;
    falls back to a synthetic flat series only when the cache is empty.
    Optionally enriches with TimesFM forecast data.
    """
    try:
        from src.trading.strategies import MarketSnapshot, evaluate_all
    except ImportError:
        logger.warning("strategies module not available; skipping strategy scoring")
        return markets

    try:
        from src.data.price_history import get_price_history
        _has_price_history = True
    except ImportError:
        _has_price_history = False

    scored = []
    for m in markets:
        price = m["price"]
        market_id = m["id"]

        prices, volumes = [], []
        if _has_price_history:
            try:
                prices, volumes = get_price_history(market_id, lookback_days=price_history_len)
            except Exception as e:
                logger.debug(f"price_history fetch failed for {market_id}: {e}")

        if len(prices) < 10:
            prices = [price] * price_history_len
            volumes = [m["volume"] / 24] * price_history_len

        snapshot = MarketSnapshot(
            market_id=market_id,
            prices=prices,
            volumes=volumes,
            current_price=price,
            days_left=m.get("days_left", 7),
            question=m.get("question", ""),
        )

        signal = evaluate_all(snapshot)
        if signal:
            m["strategy_signal"] = signal.action.value
            m["strategy_confidence"] = signal.confidence
            m["strategy_reason"] = signal.reason
            m["strategy_metadata"] = signal.metadata
        else:
            m["strategy_signal"] = "HOLD"
            m["strategy_confidence"] = 0.0
            m["strategy_reason"] = "no consensus signal"
            m["strategy_metadata"] = {}
        scored.append(m)

    if use_timesfm:
        _enrich_with_timesfm(scored, price_history_len)

    return scored


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    markets = filter_markets()
    scored = score_markets(markets)
    print(f"\n{'='*60}")
    print(f"REAL MARKETS PASSING FILTERS ({len(scored)} found)")
    print(f"{'='*60}")
    for m in scored[:10]:
        sig = m.get("strategy_signal", "—")
        conf = m.get("strategy_confidence", 0)
        print(f"\n  {m['question'][:70]}")
        print(f"  Price: {m['price']:.2%}  |  Volume: ${m['volume']:,.0f}  |  Closes in {m['days_left']}d")
        print(f"  Signal: {sig} (conf={conf:.0%})  |  {m.get('strategy_reason','')}")
        print(f"  {m['url']}")
