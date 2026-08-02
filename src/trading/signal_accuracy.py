"""
Signal Accuracy Tracker

Logs every signal generated against its eventual market outcome,
then computes per-strategy win rate so the evaluate_all() consensus
can weight higher-accuracy strategies more heavily.

Usage:
    tracker = SignalAccuracyTracker()
    tracker.log_signal(strategy="momentum", market_id="mkt-001",
                       action="BUY", confidence=0.82, price=0.20)
    # ... later, when market resolves ...
    tracker.log_outcome(market_id="mkt-001", won=True)
    stats = tracker.win_rates()  # {"momentum": 0.73, "mean_reversion": 0.61, ...}
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "signal_accuracy.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy    TEXT    NOT NULL,
            market_id   TEXT    NOT NULL,
            action      TEXT    NOT NULL,
            confidence  REAL    NOT NULL,
            price       REAL    NOT NULL,
            won         INTEGER,          -- NULL until resolved
            logged_at   TEXT    NOT NULL
        )
    """)
    c.commit()
    return c


class SignalAccuracyTracker:
    """Thread-safe, SQLite-backed signal accuracy log."""

    def log_signal(
        self,
        strategy: str,
        market_id: str,
        action: str,
        confidence: float,
        price: float,
    ) -> None:
        try:
            c = _conn()
            c.execute(
                "INSERT INTO signals (strategy,market_id,action,confidence,price,logged_at) "
                "VALUES (?,?,?,?,?,?)",
                (strategy, market_id, action, confidence, price,
                 datetime.utcnow().isoformat()),
            )
            c.commit()
            c.close()
        except Exception as e:
            logger.warning(f"SignalAccuracyTracker.log_signal failed: {e}")

    def log_outcome(self, market_id: str, won: bool) -> None:
        """Update all unresolved signals for this market with the outcome."""
        try:
            c = _conn()
            c.execute(
                "UPDATE signals SET won=? WHERE market_id=? AND won IS NULL",
                (int(won), market_id),
            )
            c.commit()
            c.close()
        except Exception as e:
            logger.warning(f"SignalAccuracyTracker.log_outcome failed: {e}")

    def win_rates(self) -> dict[str, float]:
        """Return per-strategy win rate over all resolved signals."""
        try:
            c = _conn()
            rows = c.execute(
                "SELECT strategy, AVG(won), COUNT(*) FROM signals "
                "WHERE won IS NOT NULL GROUP BY strategy"
            ).fetchall()
            c.close()
            return {r[0]: round(float(r[1]), 4) for r in rows if r[2] >= 5}
        except Exception as e:
            logger.warning(f"SignalAccuracyTracker.win_rates failed: {e}")
            return {}

    def recent_accuracy(self, strategy: str, last_n: int = 20) -> Optional[float]:
        """Win rate for last N resolved signals of a strategy."""
        try:
            c = _conn()
            rows = c.execute(
                "SELECT won FROM signals WHERE strategy=? AND won IS NOT NULL "
                "ORDER BY id DESC LIMIT ?",
                (strategy, last_n),
            ).fetchall()
            c.close()
            if not rows:
                return None
            return round(sum(r[0] for r in rows) / len(rows), 4)
        except Exception as e:
            logger.warning(f"SignalAccuracyTracker.recent_accuracy failed: {e}")
            return None

    def summary(self) -> list[dict]:
        """Full summary table: strategy, total, resolved, win_rate, recent_20."""
        try:
            c = _conn()
            rows = c.execute(
                "SELECT strategy, COUNT(*), SUM(CASE WHEN won IS NOT NULL THEN 1 ELSE 0 END), "
                "AVG(CASE WHEN won IS NOT NULL THEN won END) FROM signals GROUP BY strategy"
            ).fetchall()
            c.close()
            return [
                {
                    "strategy": r[0],
                    "total_signals": r[1],
                    "resolved": r[2],
                    "win_rate": round(float(r[3]), 4) if r[3] is not None else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"SignalAccuracyTracker.summary failed: {e}")
            return []


# Module-level singleton
_tracker: Optional[SignalAccuracyTracker] = None


def get_tracker() -> SignalAccuracyTracker:
    global _tracker
    if _tracker is None:
        _tracker = SignalAccuracyTracker()
    return _tracker
