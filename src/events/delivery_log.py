"""Persistent delivery log for signed webhook events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SignalEvent, utc_now_iso

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DELIVERY_LOG_PATH = PROJECT_ROOT / "data" / "events" / "deliveries.jsonl"


class DeliveryLog:
    """Append-only delivery log with duplicate detection."""

    def __init__(self, path: Path = DELIVERY_LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        return self.path.read_text(encoding="utf-8").splitlines()

    def contains_delivery_id(self, delivery_id: Optional[str]) -> bool:
        if not delivery_id:
            return False
        return any(
            self._delivery_id_from_line(line) == delivery_id
            for line in self._read_lines()
        )

    def append(self, event: SignalEvent, payload: Dict[str, Any]) -> None:
        record = {
            "received_at": utc_now_iso(),
            "event": event.to_dict(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        lines = self._read_lines()
        selected = lines[-limit:]
        records = []
        for line in selected:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    @staticmethod
    def _delivery_id_from_line(line: str) -> Optional[str]:
        try:
            record = json.loads(line)
            event = record.get("event", {})
            return event.get("delivery_id")
        except (TypeError, ValueError, json.JSONDecodeError):
            return None


delivery_log = DeliveryLog()


def get_delivery_log() -> DeliveryLog:
    return delivery_log
