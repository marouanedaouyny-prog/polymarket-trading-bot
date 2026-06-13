"""
Latency monitoring and stale-quote cancellation module.
"""

import time
from typing import Dict, Optional
import asyncio

class LatencyMonitor:
    """Monitors latency and handles stale quote detection."""

    def __init__(self):
        self.last_quote_time = {}
        self.max_latency = 1.0  # seconds
        self.stale_quote_threshold = 5.0  # seconds

    def update_quote_timestamp(self, market_id: str):
        """Update the timestamp for a market's quote."""
        self.last_quote_time[market_id] = time.time()

    def is_quote_stale(self, market_id: str) -> bool:
        """Check if a quote is stale based on timestamp."""
        last_time = self.last_quote_time.get(market_id, 0)
        current_time = time.time()
        time_diff = current_time - last_time
        return time_diff > self.stale_quote_threshold

    def get_quote_age(self, market_id: str) -> float:
        """Get the age of a quote in seconds."""
        last_time = self.last_quote_time.get(market_id, 0)
        current_time = time.time()
        return current_time - last_time

    def should_cancel_stale_quotes(self) -> Dict[str, bool]:
        """Check all quotes for staleness and return markets that need cancellation."""
        stale_markets = {}
        current_time = time.time()

        for market_id, last_time in self.last_quote_time.items():
            time_diff = current_time - last_time
            if time_diff > self.stale_quote_threshold:
                stale_markets[market_id] = True

        return stale_markets

class LatencyWatchdog:
    """Monitors system latency and performance metrics."""

    def __init__(self):
        self.latency_threshold = 0.5  # seconds
        self.metrics = {}
        self.alerts = []

    def record_latency(self, operation: str, latency: float):
        """Record latency for an operation."""
        if latency > self.latency_threshold:
            self.alerts.append(f"High latency alert for {operation}: {latency:.2f}s")

    def should_alert(self, operation: str, latency: float) -> bool:
        """Check if latency exceeds threshold and should trigger an alert."""
        return latency > self.latency_threshold

    def get_performance_metrics(self) -> dict:
        """Get system performance metrics."""
        return {
            "latency_threshold": self.latency_threshold,
            "alerts": self.alerts.copy()
        }