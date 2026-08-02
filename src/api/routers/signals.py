"""Signal webhook routes."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...events.delivery_log import get_delivery_log
from ...events.webhook_receiver import (
    delivery_id_header,
    is_recent_timestamp,
    normalize_signal_payload,
    parse_payload,
    signature_header,
    timestamp_header,
    verify_signature,
)

router = APIRouter()


class SignalSummary(BaseModel):
    event_id: str
    event: str
    delivery_id: Optional[str]
    date_key: Optional[str]
    count: int
    duplicate: bool


@router.post("/webhook")
async def receive_signal_webhook(
    request: Request,
    x_kamdenai_event: Optional[str] = Header(default=None),
    x_kamdenai_delivery: Optional[str] = Header(default=None),
    x_kamdenai_timestamp: Optional[str] = Header(default=None),
    x_kamdenai_signature: Optional[str] = Header(default=None),
):
    raw_body = await request.body()
    headers = {
        "X-KamdenAI-Event": x_kamdenai_event or request.headers.get("X-KamdenAI-Event") or "",
        "X-KamdenAI-Delivery": x_kamdenai_delivery or request.headers.get("X-KamdenAI-Delivery") or "",
        "X-KamdenAI-Timestamp": x_kamdenai_timestamp or request.headers.get("X-KamdenAI-Timestamp") or "",
        "X-KamdenAI-Signature": x_kamdenai_signature or request.headers.get("X-KamdenAI-Signature") or "",
    }

    try:
        payload = parse_payload(raw_body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid_json:{exc}") from exc

    secret = os.getenv("POLYMARKET_SIGNAL_WEBHOOK_SECRET") or os.getenv("KAMDENAI_SIGNING_SECRET")
    if secret:
        timestamp = timestamp_header(headers)
        signature = signature_header(headers)
        if not is_recent_timestamp(timestamp):
            return JSONResponse(status_code=401, content={"error": "stale_timestamp"})
        if not verify_signature(raw_body, timestamp, signature, secret):
            return JSONResponse(status_code=401, content={"error": "invalid_signature"})

    delivery_id = delivery_id_header(headers) or payload.get("deliveryId")
    duplicate = get_delivery_log().contains_delivery_id(delivery_id)
    event = normalize_signal_payload(payload, delivery_id=delivery_id, duplicate=duplicate)
    get_delivery_log().append(event, payload)

    return {
        "ok": True,
        "event_id": event.event_id,
        "event": event.event,
        "delivery_id": delivery_id,
        "date_key": event.date_key,
        "count": event.count,
        "duplicate": duplicate,
        "stored": True,
    }


@router.get("/deliveries", response_model=list[SignalSummary])
async def get_signal_deliveries(limit: int = 100):
    records = get_delivery_log().recent(limit=limit)
    summaries = []
    for record in records:
        event = record.get("event", {})
        summaries.append(
            SignalSummary(
                event_id=event.get("event_id"),
                event=event.get("event"),
                delivery_id=event.get("delivery_id"),
                date_key=event.get("date_key"),
                count=event.get("count", 0),
                duplicate=event.get("duplicate", False),
            )
        )
    return summaries


@router.get("/latest")
async def get_latest_signal():
    records = get_delivery_log().recent(limit=1)
    if not records:
        return {"ok": True, "latest": None}
    return {"ok": True, "latest": records[0]}
