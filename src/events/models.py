"""Signal event models for Polymarket and stock webhook integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SignalRow:
    source: str
    raw: Dict[str, Any]
    market_id: Optional[str] = None
    ticker: Optional[str] = None
    question: Optional[str] = None
    outcome: Optional[str] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    risk_per_share: Optional[float] = None
    reward_per_share: Optional[float] = None
    r_multiple_target: Optional[float] = None
    price: Optional[float] = None
    volume: Optional[float] = None
    status: Optional[str] = None
    setup: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignalEvent:
    event_id: str
    event: str
    date_key: Optional[str]
    sent_at: Optional[str]
    received_at: str
    delivery_id: Optional[str]
    count: int
    signals: List[Dict[str, Any]]
    raw_payload: Dict[str, Any]
    duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
