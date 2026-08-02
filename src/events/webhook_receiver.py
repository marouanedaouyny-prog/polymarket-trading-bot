"""Webhook receiver utilities adapted for Polymarket signal events."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import SignalEvent, SignalRow, utc_now_iso

REPLAY_TOLERANCE_MS = 5 * 60 * 1000


def is_recent_timestamp(timestamp: str) -> bool:
    try:
        delivered_at = int(timestamp)
    except (TypeError, ValueError):
        return False

    if delivered_at < 1_000_000_000:
        delivered_at *= 1000

    age_ms = abs(int(time.time() * 1000) - delivered_at)
    return 0 <= age_ms <= REPLAY_TOLERANCE_MS


def verify_signature(raw_body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    if not secret or not timestamp or not signature:
        return False

    payload = timestamp.encode("utf-8") + b"." + raw_body
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.lower(), expected.lower())


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_id(delivery_id: Optional[str], event: str, sent_at: Optional[str]) -> str:
    material = delivery_id or f"{event}:{sent_at}:{uuid4().hex}"
    return "evt_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _normalize_stock_signal(signal: Dict[str, Any]) -> SignalRow:
    entry = _as_float(signal.get("entry"))
    stop = _as_float(signal.get("stop"))
    target = _as_float(signal.get("target"))
    risk_per_share = _as_float(signal.get("riskPerShare"))
    reward_per_share = _as_float(signal.get("rewardPerShare"))

    if risk_per_share is None and entry is not None and stop is not None:
        risk_per_share = max(entry - stop, 0.0)
    if reward_per_share is None and entry is not None and target is not None:
        reward_per_share = max(target - entry, 0.0)

    return SignalRow(
        source="stock",
        raw=signal,
        ticker=signal.get("ticker"),
        entry=entry,
        stop=stop,
        target=target,
        risk_per_share=risk_per_share,
        reward_per_share=reward_per_share,
        r_multiple_target=_as_float(signal.get("rMultipleTarget") or signal.get("maxR")),
        status=signal.get("status"),
        setup=signal.get("setup"),
        notes=signal.get("notes"),
    )


def _normalize_polymarket_signal(signal: Dict[str, Any]) -> SignalRow:
    market_id = (
        signal.get("market_id")
        or signal.get("marketId")
        or signal.get("id")
        or signal.get("conditionId")
    )
    prices = signal.get("outcomePrices") or signal.get("prices") or []
    price = _as_float(signal.get("price") or signal.get("yes_price") or signal.get("yesPrice"))
    if price is None and isinstance(prices, list) and prices:
        price = _as_float(prices[0])

    return SignalRow(
        source="polymarket",
        raw=signal,
        market_id=str(market_id) if market_id else None,
        question=signal.get("question") or signal.get("title") or signal.get("name"),
        outcome=signal.get("outcome"),
        price=price,
        volume=_as_float(signal.get("volume") or signal.get("volume24hr")),
        status=signal.get("status"),
        notes=signal.get("notes"),
    )


def normalize_signal_payload(
    payload: Dict[str, Any],
    delivery_id: Optional[str] = None,
    duplicate: bool = False,
) -> SignalEvent:
    data = payload.get("data") or {}
    event = str(payload.get("event") or "signal.received")
    date_key = payload.get("dateKey") or payload.get("date_key")
    sent_at = payload.get("sentAt") or payload.get("sent_at")
    received_at = payload.get("receivedAt") or utc_now_iso()
    raw_signals = data.get("signals") or data.get("results") or []

    normalized_signals: List[Dict[str, Any]] = []
    for item in raw_signals:
        if not isinstance(item, dict):
            continue
        row = _normalize_polymarket_signal(item) if _looks_like_polymarket(item) else _normalize_stock_signal(item)
        normalized_signals.append(row.to_dict())

    return SignalEvent(
        event_id=_event_id(delivery_id, event, sent_at),
        event=event,
        date_key=date_key,
        sent_at=sent_at,
        received_at=received_at,
        delivery_id=delivery_id,
        count=int(data.get("count", len(normalized_signals)) if "count" in data else len(normalized_signals)),
        signals=normalized_signals,
        raw_payload=payload,
        duplicate=duplicate,
    )


def _looks_like_polymarket(signal: Dict[str, Any]) -> bool:
    return any(
        key in signal
        for key in (
            "market_id",
            "marketId",
            "conditionId",
            "question",
            "outcomePrices",
            "yes_price",
            "yesPrice",
            "outcome",
        )
    )


def parse_payload(raw_body: bytes) -> Dict[str, Any]:
    return json.loads(raw_body.decode("utf-8"))


def timestamp_header(headers: Dict[str, str]) -> str:
    return headers.get("X-KamdenAI-Timestamp") or headers.get("X-Polymarket-Timestamp") or ""


def delivery_id_header(headers: Dict[str, str]) -> Optional[str]:
    return headers.get("X-KamdenAI-Delivery") or headers.get("X-Polymarket-Delivery") or headers.get("X-Delivery-Id")


def signature_header(headers: Dict[str, str]) -> str:
    return headers.get("X-KamdenAI-Signature") or headers.get("X-Polymarket-Signature") or headers.get("X-Signature") or ""
