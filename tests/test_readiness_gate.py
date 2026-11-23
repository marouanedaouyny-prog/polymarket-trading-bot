"""Tests for the fail-closed live-trading readiness gate."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.utils.readiness_gate import (
    LiveReadinessError,
    check_live_readiness,
    require_live_readiness,
)

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def _write(tmp_path, **overrides):
    verdict = {
        "checked_at": (NOW - timedelta(days=1)).isoformat(),
        "passed": True,
        "failed": [],
    }
    verdict.update(overrides)
    path = tmp_path / "verdict.json"
    path.write_text(json.dumps(verdict), encoding="utf-8")
    return str(path)


def test_missing_verdict_blocks(tmp_path):
    reason = check_live_readiness(path=str(tmp_path / "nope.json"), now=NOW)
    assert reason and "no readiness verdict" in reason
    with pytest.raises(LiveReadinessError):
        require_live_readiness(path=str(tmp_path / "nope.json"))


def test_failed_verdict_blocks(tmp_path):
    path = _write(tmp_path, passed=False, failed=["model beats price"])
    reason = check_live_readiness(path=path, now=NOW)
    assert reason and "model beats price" in reason


def test_stale_verdict_blocks(tmp_path):
    path = _write(tmp_path, checked_at=(NOW - timedelta(days=8)).isoformat())
    reason = check_live_readiness(path=path, now=NOW)
    assert reason and "days old" in reason


def test_future_verdict_blocks(tmp_path):
    path = _write(tmp_path, checked_at=(NOW + timedelta(days=2)).isoformat())
    reason = check_live_readiness(path=path, now=NOW)
    assert reason and "future" in reason


def test_invalid_json_blocks(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    reason = check_live_readiness(path=str(path), now=NOW)
    assert reason and "unreadable" in reason


def test_fresh_passing_verdict_allows(tmp_path):
    path = _write(tmp_path, checked_at="2026-11-04T12:00:00Z")
    assert check_live_readiness(path=path, now=NOW) is None


def test_order_manager_live_without_verdict_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.setenv("POLYMARKET_ALLOW_REAL_ORDERS", "true")
    monkeypatch.setenv("READINESS_VERDICT_PATH", str(tmp_path / "missing.json"))

    from src.execution.order_manager import OrderManager

    om = OrderManager(mode="live")
    assert om.live_adapter is None
    assert om.live_block_reason
    assert om.place_order({"market_id": "m1", "side": "YES", "price": 0.5, "size": 10}) is False
    assert om.order_history == []


def test_order_manager_paper_ignores_gate(monkeypatch):
    monkeypatch.delenv("POLYMARKET_ALLOW_REAL_ORDERS", raising=False)
    monkeypatch.setenv("EXCHANGE_LATENCY", "0")

    from src.execution.order_manager import OrderManager

    om = OrderManager(mode="paper")
    assert om.live_block_reason is None
    assert om.place_order({"market_id": "m1", "side": "YES", "price": 0.5, "size": 10}) is True
