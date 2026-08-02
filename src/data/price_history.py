"""
Per-market price history fetcher with SQLite cache.

Usage:
    from src.data.price_history import get_price_history
    prices, volumes = get_price_history(market_id, lookback_days=30)

The cache stores rows in data/price_history.db and is considered stale after
CACHE_TTL_SECONDS (default 3600).  On cache miss, it fetches from the Gamma
API and backfills.
"""

import logging
import os
import sqlite3
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DB_PATH = os.path.join('data', 'price_history.db')
GAMMA_API = 'https://gamma-api.polymarket.com'
CACHE_TTL_SECONDS = int(os.getenv('PRICE_HISTORY_TTL', '3600'))


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            market_id  TEXT    NOT NULL,
            ts         INTEGER NOT NULL,   -- unix seconds
            price      REAL    NOT NULL,
            volume     REAL    NOT NULL DEFAULT 0,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (market_id, ts)
        )
    """)
    conn.commit()
    return conn


def _fetch_from_api(market_id: str) -> list[dict]:
    """Fetch price history from Gamma API.  Returns list of {ts, price, volume}."""
    url = f"{GAMMA_API}/markets/{market_id}/prices-history"
    try:
        resp = requests.get(url, timeout=15,
                            headers={'User-Agent': 'PolymarketPriceHistory/1.0'})
        if resp.status_code != 200:
            logger.warning(f"Gamma prices-history returned {resp.status_code} for {market_id}")
            return []
        data = resp.json()
        # Response is usually {"history": [{"t": unix_ts, "p": price}, ...]}
        rows = data.get('history', data) if isinstance(data, dict) else data
        result = []
        for row in rows:
            ts = row.get('t') or row.get('timestamp')
            price = row.get('p') or row.get('price')
            volume = row.get('v') or row.get('volume', 0.0)
            if ts and price:
                result.append({'ts': int(ts), 'price': float(price), 'volume': float(volume)})
        return result
    except Exception as e:
        logger.error(f"Failed to fetch price history for {market_id}: {e}")
        return []


def _is_cache_fresh(conn: sqlite3.Connection, market_id: str) -> bool:
    """Return True if cache has data fetched within CACHE_TTL_SECONDS."""
    row = conn.execute(
        "SELECT MAX(fetched_at) FROM price_history WHERE market_id = ?",
        (market_id,)
    ).fetchone()
    latest = row[0] if row else None
    if not latest:
        return False
    return (time.time() - latest) < CACHE_TTL_SECONDS


def _upsert_rows(conn: sqlite3.Connection, market_id: str, rows: list[dict]) -> None:
    now = int(time.time())
    conn.executemany(
        "INSERT OR REPLACE INTO price_history (market_id, ts, price, volume, fetched_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [(market_id, r['ts'], r['price'], r['volume'], now) for r in rows]
    )
    conn.commit()


def get_price_history(
    market_id: str,
    lookback_days: int = 30,
    force_refresh: bool = False,
) -> tuple[list[float], list[float]]:
    """
    Return (prices, volumes) for `market_id` covering the last `lookback_days`.

    Prices and volumes are lists ordered oldest → newest.
    On cache miss or stale cache, fetches from the Gamma API.
    Returns ([], []) if no data is available.
    """
    conn = _get_conn()
    try:
        if force_refresh or not _is_cache_fresh(conn, market_id):
            rows = _fetch_from_api(market_id)
            if rows:
                _upsert_rows(conn, market_id, rows)

        cutoff = int(time.time()) - lookback_days * 86400
        cursor = conn.execute(
            "SELECT price, volume FROM price_history "
            "WHERE market_id = ? AND ts >= ? ORDER BY ts ASC",
            (market_id, cutoff)
        )
        data = cursor.fetchall()
        if not data:
            return [], []
        prices = [r[0] for r in data]
        volumes = [r[1] for r in data]
        return prices, volumes
    finally:
        conn.close()


def invalidate_cache(market_id: Optional[str] = None) -> None:
    """Delete cached rows.  Pass market_id to target one market, or None to clear all."""
    conn = _get_conn()
    try:
        if market_id:
            conn.execute("DELETE FROM price_history WHERE market_id = ?", (market_id,))
        else:
            conn.execute("DELETE FROM price_history")
        conn.commit()
    finally:
        conn.close()
