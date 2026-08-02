"""
Self-Improvement Pipeline — walk-forward validation with genome mutation/selection.

Schedules periodic evaluation against resolved markets, mutates strategy
parameters (genome), promotes winners, and persists the champion config.
"""

from __future__ import annotations

import json
import os
import copy
import random
import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable

from .autopredict_bridge import (
    ScoringBridge,
    build_forecasts,
    backtest_report,
    load_resolved_markets,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Genome — the tunable strategy parameter vector
# ---------------------------------------------------------------------------

DEFAULT_GENOME: dict[str, Any] = {
    "max_position_pct": 0.10,
    "min_edge": 0.08,
    "min_confidence": 85,
    "min_volume": 10_000,
    "price_min": 0.05,
    "price_max": 0.50,
    "take_profit_pct": 0.50,
    "stop_loss_pct": 0.15,
    "daily_loss_limit": 0.05,
}

GENOME_BOUNDS: dict[str, tuple[float, float]] = {
    "max_position_pct": (0.02, 0.25),
    "min_edge": (0.02, 0.25),
    "min_confidence": (50, 99),
    "min_volume": (1_000, 100_000),
    "price_min": (0.01, 0.20),
    "price_max": (0.20, 0.90),
    "take_profit_pct": (0.10, 2.00),
    "stop_loss_pct": (0.05, 0.40),
    "daily_loss_limit": (0.02, 0.20),
}

MUTATION_RATES: dict[str, float] = {
    "max_position_pct": 0.04,
    "min_edge": 0.03,
    "min_confidence": 5.0,
    "min_volume": 5_000,
    "price_min": 0.03,
    "price_max": 0.05,
    "take_profit_pct": 0.15,
    "stop_loss_pct": 0.05,
    "daily_loss_limit": 0.02,
}


def clamp_genome(g: dict) -> dict:
    """Clamp every gene to its declared bounds."""
    for key, (lo, hi) in GENOME_BOUNDS.items():
        if key in g:
            g[key] = max(lo, min(hi, g[key]))
    return g


def mutate_genome(g: dict, rate: float = 1.0) -> dict:
    """Return a mutated copy of genome *g*."""
    child = copy.deepcopy(g)
    for key, step in MUTATION_RATES.items():
        if key not in child:
            continue
        delta = random.gauss(0, step * rate)
        if key == "min_confidence":
            child[key] = int(round(child[key] + delta))
        else:
            child[key] = child[key] + delta
    return clamp_genome(child)


def genome_distance(a: dict, b: dict) -> float:
    """Normalised Euclidean distance between two genomes (0 = identical)."""
    dist_sq = 0.0
    for key in GENOME_BOUNDS:
        lo, hi = GENOME_BOUNDS[key]
        if hi == lo:
            continue
        va = (a.get(key, lo) - lo) / (hi - lo)
        vb = (b.get(key, lo) - lo) / (hi - lo)
        dist_sq += (va - vb) ** 2
    return math.sqrt(dist_sq / len(GENOME_BOUNDS))


# ---------------------------------------------------------------------------
# Backtesting helper
# ---------------------------------------------------------------------------


def genome_to_predict_fn(genome: dict) -> Callable:
    """Build a simple rule-based predict function from genome thresholds."""

    def predict_fn(price: float, volume: float, is_crypto: int = 0, **kwargs) -> float:
        edge = genome.get("min_edge", 0.08)
        conf = genome.get("min_confidence", 85) / 100.0
        min_vol = genome.get("min_volume", 10_000)
        p_min = genome.get("price_min", 0.05)
        p_max = genome.get("price_max", 0.50)

        if volume < min_vol:
            return 0.02  # skip — no-volume markets
        if price < p_min or price > p_max:
            return 0.02

        raw = price * 0.15 + conf * 0.45 + edge * 0.40
        return min(max(raw, 0.02), 0.70)

    return predict_fn


# ---------------------------------------------------------------------------
# Champion — evaluate, select, persist
# ---------------------------------------------------------------------------

_CHAMPION_PATH = os.path.join("data", "training", "champion_genome.json")


def load_champion() -> dict:
    """Load the persisted champion genome (or default if missing)."""
    if os.path.isfile(_CHAMPION_PATH):
        try:
            with open(_CHAMPION_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_GENOME)


def save_champion(genome: dict, metadata: dict | None = None) -> None:
    """Persist *genome* with evaluation metadata."""
    record = {"genome": genome, "metadata": metadata or {}, "updated": datetime.now(timezone.utc).isoformat()}
    os.makedirs(os.path.dirname(_CHAMPION_PATH), exist_ok=True)
    with open(_CHAMPION_PATH, "w") as f:
        json.dump(record, f, indent=2)
    logger.info("Champion genome saved to %s", _CHAMPION_PATH)


def evaluate_genome(
    records: list[dict],
    genome: dict,
    predict_fn: Callable | None = None,
    min_volume: float = 1000,
) -> dict:
    """Score a genome via backtest_report and return the summary dict."""
    if predict_fn is None:
        predict_fn = genome_to_predict_fn(genome)
    bt = backtest_report(records, predict_fn, min_volume=min_volume)
    scoring = bt["scoring"]
    summary = bt["summary"]
    return {
        "brier": scoring["brier_score"],
        "log_loss": scoring["log_loss"],
        "cal_gap": scoring["calibration"]["mean_absolute_gap"],
        "win_rate": summary["win_rate"],
        "roi_pct": summary["roi_pct"],
        "total_trades": summary["total_trades"],
        "final_cash": summary["final_cash"],
    }


# ---------------------------------------------------------------------------
# Evolution — run a generation of mutation / selection
# ---------------------------------------------------------------------------


def evolve(
    records: list[dict],
    champion: dict | None = None,
    population: int = 10,
    children: int = 5,
    mutation_rate: float = 1.0,
    min_trades: int = 5,
) -> dict:
    """Run one evolution generation.

    Args:
        records: Resolved market records.
        champion: Starting genome (default: load_champion()).
        population: How many children to generate per parent.
        children: How many parents survive to reproduce.
        mutation_rate: Standard deviation multiplier for mutations.
        min_trades: Skip genomes that produce fewer trades than this.

    Returns:
        {"champion": genome, "fitness": dict, "generation": dict}
    """
    if champion is None:
        champion = load_champion()
    champion = dict(champion)

    # Score baseline
    base_score = evaluate_genome(records, champion)
    base_fitness = _fitness(base_score)
    logger.info(
        "Baseline genome: Brier=%.4f CalGap=%.4f WR=%.1f%% ROI=%.1f%% fit=%.4f",
        base_score["brier"], base_score["cal_gap"],
        base_score["win_rate"] * 100, base_score["roi_pct"], base_fitness,
    )

    # Generate candidates
    candidates = [champion]
    for _ in range(population):
        candidates.append(mutate_genome(champion, mutation_rate))

    # Score them
    scored = []
    for g in candidates:
        s = evaluate_genome(records, g)
        if s["total_trades"] < min_trades:
            continue
        scored.append((_fitness(s), g, s))

    if not scored:
        logger.warning("No viable candidates — keeping champion")
        return {"champion": champion, "fitness": base_score, "generation": {"kept": 0, "total": len(candidates)}}

    # Sort by fitness descending, pick top *children*
    scored.sort(key=lambda x: x[0], reverse=True)
    best_fitness, best_genome, best_score = scored[0]

    if best_fitness > base_fitness:
        logger.info(
            "New champion: fit=%.4f (was %.4f) Brier=%.4f WR=%.1f%% ROI=%.1f%%",
            best_fitness, base_fitness, best_score["brier"],
            best_score["win_rate"] * 100, best_score["roi_pct"],
        )
        save_champion(best_genome, {"fitness": best_fitness, "evaluation": best_score})
        return {"champion": best_genome, "fitness": best_score, "generation": {"kept": 1, "total": len(scored)}}
    else:
        logger.info("No improvement — keeping existing champion")
        return {"champion": champion, "fitness": base_score, "generation": {"kept": 0, "total": len(scored)}}


def _fitness(s: dict) -> float:
    """Composite fitness: higher is better."""
    if s["total_trades"] == 0:
        return -999
    roi_clipped = max(-1, min(1, s["roi_pct"] / 100))
    wr = s["win_rate"]
    brier_penalty = max(0, s["brier"] - 0.05) * 5  # penalise Brier > 0.05
    cal_penalty = s["cal_gap"] * 3
    return roi_clipped * 0.5 + wr * 0.3 - brier_penalty - cal_penalty


# ---------------------------------------------------------------------------
# Full pipeline — convenience entrypoint
# ---------------------------------------------------------------------------


def run_pipeline(
    records: list[dict] | None = None,
    generations: int = 3,
    population: int = 10,
    children: int = 5,
    min_trades: int = 5,
) -> dict:
    """Run *generations* of evolution over resolved markets.

    Returns a structured report with per-generation results.
    """
    if records is None:
        records = load_resolved_markets()
    if len(records) < 10:
        return {"error": f"Need at least 10 resolved markets, got {len(records)}"}

    champion = load_champion()
    history = []

    for gen in range(1, generations + 1):
        logger.info("--- Generation %d/%d ---", gen, generations)
        result = evolve(
            records=records,
            champion=champion,
            population=population,
            children=children,
            min_trades=min_trades,
        )
        champion = result["champion"]
        history.append(result)
        logger.info("Gen %d: fitness=%s", gen, result["fitness"])

    return {
        "generations": len(history),
        "champion_genome": champion,
        "champion_fitness": history[-1]["fitness"] if history else {},
        "history": history,
        "records_used": len(records),
    }