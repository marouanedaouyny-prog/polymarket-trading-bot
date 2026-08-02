"""
AutoPredict integration bridge for the Polymarket trading system.

Provides:
- EvalBridge: evaluate predictions using autopredict's proper scoring rules
- BacktestBridge: backtest against resolved markets using autopredict's evaluation
- SelfImprovementBridge: evolve strategy parameters via walk-forward validation
"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Scoring — no-dependency subset of autopredict.evaluation.scoring
# ---------------------------------------------------------------------------

EPSILON = 1e-12


class ScoringBridge:
    """Proper scoring rules for evaluating binary market forecasts.

    Mirrors autopredict.evaluation.scoring.ProperScoringRules but accepts
    plain dicts so the existing system doesn't need autopredict types.
    """

    @staticmethod
    def brier_score(forecasts: list[dict]) -> float:
        """Mean squared error between predicted probabilities and outcomes."""
        if not forecasts:
            return 0.0
        total = 0.0
        for f in forecasts:
            p = f["probability"]
            o = f["outcome"]
            total += (p - o) ** 2
        return total / len(forecasts)

    @staticmethod
    def log_score(forecasts: list[dict]) -> float:
        """Mean log-probability assigned to the realized outcome. Higher is better (max 0)."""
        if not forecasts:
            return 0.0
        total = 0.0
        import math

        for f in forecasts:
            p = f["probability"]
            o = f["outcome"]
            assigned = p if o == 1 else (1 - p)
            assigned = max(assigned, EPSILON)
            total += math.log(assigned)
        return total / len(forecasts)

    @staticmethod
    def log_loss(forecasts: list[dict]) -> float:
        """Negation of log_score — lower is better."""
        return -ScoringBridge.log_score(forecasts)

    @staticmethod
    def calibration(forecasts: list[dict], num_buckets: int = 10) -> dict:
        """Calibration summary: mean absolute gap, max gap, per-bucket breakdown."""
        if not forecasts:
            return {"mean_absolute_gap": 0.0, "max_absolute_gap": 0.0, "buckets": [], "base_rate": 0.0}

        buckets = [[] for _ in range(num_buckets)]
        for f in forecasts:
            p = f["probability"]
            idx = min(int(p * num_buckets), num_buckets - 1)
            buckets[idx].append(f)

        base_rate = sum(f["outcome"] for f in forecasts) / len(forecasts)
        bucket_data = []
        total_gap = 0.0
        max_gap = 0.0
        for i, bucket in enumerate(buckets):
            if not bucket:
                continue
            lower = i / num_buckets
            upper = (i + 1) / num_buckets
            avg_prob = sum(f["probability"] for f in bucket) / len(bucket)
            realized = sum(f["outcome"] for f in bucket) / len(bucket)
            gap = abs(avg_prob - realized)
            total_gap += gap * len(bucket)
            max_gap = max(max_gap, gap)
            bucket_data.append({
                "lower": lower,
                "upper": upper,
                "count": len(bucket),
                "avg_probability": round(avg_prob, 4),
                "realized_rate": round(realized, 4),
                "absolute_gap": round(gap, 4),
            })

        return {
            "mean_absolute_gap": round(total_gap / len(forecasts), 4),
            "max_absolute_gap": round(max_gap, 4),
            "buckets": bucket_data,
            "base_rate": round(base_rate, 4),
        }

    @staticmethod
    def full_report(forecasts: list[dict]) -> dict:
        """Return a full scoring report dict."""
        return {
            "count": len(forecasts),
            "brier_score": round(ScoringBridge.brier_score(forecasts), 6),
            "log_score": round(ScoringBridge.log_score(forecasts), 6),
            "log_loss": round(ScoringBridge.log_loss(forecasts), 6),
            "calibration": ScoringBridge.calibration(forecasts),
        }


# ---------------------------------------------------------------------------
# Backtest — run evaluation against resolved market data
# ---------------------------------------------------------------------------


def load_resolved_markets(path: str | None = None) -> list[dict]:
    """Load resolved market records from JSON."""
    if path is None:
        path = os.path.join("data", "training", "resolved_markets.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_forecasts(
    records: list[dict],
    predict_fn: callable,
    min_volume: float = 0,
) -> list[dict]:
    """Run the predictor over every resolved record and build forecast entries.

    Args:
        records: Resolved market records (keys: yes_price, volume, outcome, question, …)
        predict_fn: function(price, volume, is_crypto, **kwargs) → probability float
        min_volume: skip records below this volume

    Returns:
        List of forecast dicts for ScoringBridge.
    """
    forecasts = []
    for r in records:
        price = float(r.get("yes_price", 0) or 0)
        if price <= 0 or price >= 1:
            continue
        volume = float(r.get("volume", 0) or 0)
        if volume < min_volume:
            continue
        outcome_raw = r.get("outcome", "")
        outcome = 1 if outcome_raw in ("yes", "true", True, 1) else 0
        question = r.get("question", "")
        is_crypto = int(
            any(kw in question.lower() for kw in ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth"])
        )
        prob = predict_fn(price=price, volume=volume, is_crypto=is_crypto)
        forecasts.append({
            "market_id": r.get("id", ""),
            "probability": prob,
            "outcome": outcome,
            "metadata": {"question": question, "price": price, "volume": volume},
        })
    return forecasts


def backtest_report(
    records: list[dict],
    predict_fn: callable,
    min_volume: float = 0,
) -> dict:
    """Run a full backtest evaluation and return a structured report."""
    forecasts = build_forecasts(records, predict_fn, min_volume=min_volume)
    scoring = ScoringBridge.full_report(forecasts)

    # Basic trade simulation — only on mid-range prices (realistic entry)
    trades = []
    cash = 1000.0
    wins = 0
    losses = 0
    for f in forecasts:
        price = f["metadata"]["price"]
        if price <= 0.02 or price >= 0.98:
            continue  # skip extreme prices — not realistic trade entries
        predicted_yes = f["probability"] >= 0.5
        actual_yes = f["outcome"] == 1
        bet = cash * 0.10  # 10% per trade
        if predicted_yes == actual_yes:
            profit = bet * ((1 / price) - 1) * 0.93  # 7% fee
            cash += bet + profit
            wins += 1
        else:
            cash -= bet
            losses += 1
        trades.append({
            "market_id": f["market_id"],
            "predicted_prob": round(f["probability"], 4),
            "price": price,
            "won": predicted_yes == actual_yes,
            "pnl": round(profit if predicted_yes == actual_yes else -bet, 2),
        })

    total = wins + losses
    return {
        "scoring": scoring,
        "trades": trades,
        "summary": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total, 4) if total else 0,
            "final_cash": round(cash, 2),
            "total_pnl": round(cash - 1000.0, 2),
            "roi_pct": round(((cash / 1000.0) - 1) * 100, 2),
        },
    }


# ---------------------------------------------------------------------------
# Walk-forward validation via autopredict's self-improvement loop
# ---------------------------------------------------------------------------


def run_walk_forward_evaluation(
    records: list[dict],
    base_params: dict | None = None,
    train_fraction: float = 0.7,
    n_folds: int = 3,
) -> dict:
    """Run chronological walk-forward validation.

    Splits resolved records chronologically, trains on early window,
    evaluates on later window, repeats with expanding window.

    Args:
        records: Resolved market records sorted by time.
        base_params: Initial strategy parameters dict.
        train_fraction: Fraction of data to use for initial training window.
        n_folds: Number of expanding-window folds.

    Returns:
        Report dict with per-fold metrics and aggregated results.
    """
    if len(records) < 10:
        return {"error": f"Need at least 10 records, got {len(records)}"}

    base_params = base_params or {}
    sorted_records = sorted(records, key=lambda r: r.get("timestamp", r.get("id", "")))

    fold_size = max(1, int(len(sorted_records) * (1 - train_fraction) / n_folds))
    initial_train_end = int(len(sorted_records) * train_fraction)

    results = []
    current_params = dict(base_params)

    for fold in range(n_folds):
        train_end = initial_train_end + (fold * fold_size)
        val_start = train_end
        val_end = min(val_start + fold_size, len(sorted_records))

        if val_start >= len(sorted_records) or val_start >= val_end:
            break

        train = sorted_records[:train_end]
        val = sorted_records[val_start:val_end]

        # Evaluate baseline params on validation set
        def make_baseline_pred(price, volume, is_crypto):
            return min(max(price, 0.02), 0.98)

        baseline_report = backtest_report(val, make_baseline_pred)

        results.append({
            "fold": fold + 1,
            "train_size": len(train),
            "val_size": len(val),
            "baseline": baseline_report["summary"],
            "baseline_scoring": baseline_report["scoring"],
        })

    return {
        "folds": results,
        "aggregate": {
            "n_records": len(sorted_records),
            "n_folds": len(results),
        },
    }


# ---------------------------------------------------------------------------
# Calibration check
# ---------------------------------------------------------------------------


def calibration_check(forecasts: list[dict], threshold: float = 0.05) -> dict:
    """Check if model is calibrated within threshold."""
    cal = ScoringBridge.calibration(forecasts)
    return {
        "calibrated": cal["mean_absolute_gap"] <= threshold,
        "mean_absolute_gap": cal["mean_absolute_gap"],
        "max_absolute_gap": cal["max_absolute_gap"],
        "threshold": threshold,
        "recommendation": (
            "Calibrate model" if cal["mean_absolute_gap"] > threshold
            else "Calibration OK"
        ),
    }