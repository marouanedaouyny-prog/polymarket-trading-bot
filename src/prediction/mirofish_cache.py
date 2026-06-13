"""
Cache layer for MiroFish simulation results.
Avoids redundant simulations for the same market question.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path("data/mirofish_cache")


class MiroFishCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        return CACHE_DIR / f"{key}.json"

    def _make_key(self, market_question: str, context: str = "") -> str:
        raw = f"{market_question.lower().strip()}|{context.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, market_question: str, context: str = "") -> Optional[dict]:
        key = self._make_key(market_question, context)
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            age = time.time() - entry.get("timestamp", 0)
            if age > self.ttl_seconds:
                path.unlink()
                return None
            return entry.get("result")
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, market_question: str, result: dict, context: str = "") -> None:
        key = self._make_key(market_question, context)
        entry = {
            "timestamp": time.time(),
            "question": market_question,
            "result": result,
        }
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

    def invalidate(self, market_question: str, context: str = "") -> None:
        key = self._make_key(market_question, context)
        path = self._cache_path(key)
        if path.exists():
            path.unlink()

    def clear_expired(self) -> int:
        now = time.time()
        cleared = 0
        for path in CACHE_DIR.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if now - entry.get("timestamp", 0) > self.ttl_seconds:
                    path.unlink()
                    cleared += 1
            except (json.JSONDecodeError, OSError):
                path.unlink()
                cleared += 1
        return cleared
