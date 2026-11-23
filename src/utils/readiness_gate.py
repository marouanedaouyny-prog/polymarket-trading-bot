"""Fail-closed gate for real-money trading.

Live orders stay blocked unless a fresh passing verdict exists, produced by
`scripts/tools/readiness_check.py --json`. Paper mode never consults this gate.
"""
import json
import os
from datetime import datetime, timezone

DEFAULT_VERDICT_PATH = os.path.join("data", "readiness_verdict.json")
MAX_AGE_DAYS = 7


class LiveReadinessError(RuntimeError):
    """Raised when live trading is requested without a fresh passing verdict."""


def verdict_path() -> str:
    return os.getenv("READINESS_VERDICT_PATH", DEFAULT_VERDICT_PATH)


def _age_days(checked_at: str, now: datetime) -> float:
    ts = checked_at
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    checked = datetime.fromisoformat(ts)
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return (now - checked).total_seconds() / 86400.0


def check_live_readiness(path: str = None, max_age_days: float = MAX_AGE_DAYS,
                         now: datetime = None) -> str:
    """Return None when live trading is allowed, else the blocking reason."""
    path = path or verdict_path()
    now = now or datetime.now(timezone.utc)

    try:
        with open(path, encoding="utf-8") as f:
            verdict = json.load(f)
    except FileNotFoundError:
        return (f"no readiness verdict at {path}; run "
                f"`python scripts/tools/readiness_check.py --json {path}`")
    except (OSError, json.JSONDecodeError) as e:
        return f"unreadable readiness verdict at {path}: {e}"

    if verdict.get("passed") is not True:
        failed = verdict.get("failed") or verdict.get("checks") or "unknown"
        return f"readiness verdict is failing ({failed})"

    checked_at = verdict.get("checked_at")
    if not checked_at:
        return "readiness verdict has no checked_at timestamp"
    try:
        age = _age_days(checked_at, now)
    except ValueError as e:
        return f"readiness verdict has an invalid checked_at: {e}"
    if age > max_age_days:
        return (f"readiness verdict is {age:.1f} days old (max {max_age_days}); re-run "
                f"`python scripts/tools/readiness_check.py --json {path}`")
    if age < -0.25:
        return f"readiness verdict is dated in the future ({checked_at})"
    return None


def require_live_readiness(path: str = None, max_age_days: float = MAX_AGE_DAYS) -> None:
    """Raise LiveReadinessError unless a fresh passing verdict exists."""
    reason = check_live_readiness(path=path, max_age_days=max_age_days)
    if reason:
        raise LiveReadinessError(reason)
