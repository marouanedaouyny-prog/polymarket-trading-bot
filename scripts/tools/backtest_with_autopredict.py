#!/usr/bin/env python3
"""
Backtesting CLI — evaluate strategy performance against resolved markets.

Usage:
    python scripts/tools/backtest_with_autopredict.py                        # default: backtest
    python scripts/tools/backtest_with_autopredict.py --mode evolve          # run evolution
    python scripts/tools/backtest_with_autopredict.py --mode report          # show champion
    python scripts/tools/backtest_with_autopredict.py --help
"""

import argparse
import json
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.prediction.autopredict_bridge import (
    ScoringBridge,
    backtest_report,
    build_forecasts,
    load_resolved_markets,
    calibration_check,
)
from src.prediction.self_improvement import (
    load_champion,
    save_champion,
    evaluate_genome,
    genome_to_predict_fn,
    run_pipeline,
    DEFAULT_GENOME,
)


def cmd_backtest(args):
    """Run a single backtest against resolved markets."""
    records = load_resolved_markets()
    if not records:
        print("No resolved markets found.")
        return None

    champion = load_champion()

    def predict_fn(price, volume, is_crypto):
        g = champion
        if volume < g.get("min_volume", 1000):
            return 0.02
        if price < g.get("price_min", 0.01) or price > g.get("price_max", 0.90):
            return 0.02
        return min(max(price, 0.02), 0.70)

    bt = backtest_report(records, predict_fn, min_volume=args.min_volume)

    scoring = bt["scoring"]
    summary = bt["summary"]
    cal = calibration_check(
        build_forecasts(records, predict_fn, min_volume=args.min_volume)
    )

    print("=" * 60)
    print("BACKTEST REPORT  -  AutoPredict Evaluation")
    print("=" * 60)
    print(f"Resolved markets      : {len(records)}")
    print(f"Trades simulated      : {summary['total_trades']}")
    print(f"Win rate              : {summary['win_rate']:.1%}")
    print(f"Wins / Losses         : {summary['wins']}/{summary['losses']}")
    print(f"Starting cash         : $1,000.00")
    print(f"Final cash            : ${summary['final_cash']:.2f}")
    print(f"Total PnL             : ${summary['total_pnl']:.2f}")
    print(f"ROI                   : {summary['roi_pct']:.2f}%")
    print()
    print("-" * 40)
    print("Scoring Metrics")
    print("-" * 40)
    print(f"Brier Score           : {scoring['brier_score']:.6f}  (0=perfect)")
    print(f"Log Score             : {scoring['log_score']:.6f}  (0=perfect)")
    print(f"Log Loss              : {scoring['log_loss']:.6f}  (lower=better)")
    print(f"Mean Calibration Gap  : {scoring['calibration']['mean_absolute_gap']:.4f}")
    print(f"Max Calibration Gap   : {scoring['calibration']['max_absolute_gap']:.4f}")
    print(f"Base Rate             : {scoring['calibration']['base_rate']:.4f}")
    print(f"Calibrated (<5% gap)  : {'YES' if cal['calibrated'] else 'NO'}")
    print()
    print("Calibration Buckets:")
    for b in scoring["calibration"]["buckets"]:
        bar = "#" * max(1, int(b["count"] / max(1, scoring["count"]) * 60))
        print(f"  [{b['lower']:.1f}-{b['upper']:.1f}) n={b['count']:3d}  "
              f"avg={b['avg_probability']:.3f}  realized={b['realized_rate']:.3f}  "
              f"gap={b['absolute_gap']:.3f}")
    print("=" * 60)
    return bt


def cmd_evolve(args):
    """Run the self-improvement evolution pipeline."""
    records = load_resolved_markets()
    if not records:
        print("No resolved markets found.")
        return

    print(f"Loaded {len(records)} resolved markets.")
    print(f"Running {args.generations} generation(s) with population {args.population}...\n")

    result = run_pipeline(
        records=records,
        generations=args.generations,
        population=args.population,
        min_trades=args.min_trades,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print("\n" + "=" * 60)
    print("EVOLUTION COMPLETE")
    print("=" * 60)
    print(f"Generations           : {result['generations']}")
    print(f"Records used          : {result['records_used']}")
    fitness = result["champion_fitness"]
    print(f"Champion Brier        : {fitness.get('brier', '?'):.4f}")
    print(f"Champion Cal Gap      : {fitness.get('cal_gap', '?'):.4f}")
    print(f"Champion Win Rate     : {fitness.get('win_rate', '?'):.1%}")
    print(f"Champion ROI          : {fitness.get('roi_pct', '?'):.1f}%")
    print(f"Champion trades       : {fitness.get('total_trades', '?')}")
    print("\nChampion Genome:")
    for k, v in result["champion_genome"].items():
        print(f"  {k:24s}: {v}")
    print("=" * 60)


def cmd_report(args):
    """Show the current champion genome and its evaluation."""
    champion = load_champion()
    records = load_resolved_markets()

    print("=" * 60)
    print("CHAMPION GENOME REPORT")
    print("=" * 60)
    print("\nCurrent Genome:")
    for k, v in champion.items():
        print(f"  {k:24s}: {v}")

    if records:
        score = evaluate_genome(records, champion)
        print(f"\nEvaluation ({len(records)} records):")
        print(f"  Brier                : {score['brier']:.4f}")
        print(f"  Log Loss             : {score['log_loss']:.4f}")
        print(f"  Calibration Gap      : {score['cal_gap']:.4f}")
        print(f"  Win Rate             : {score['win_rate']:.1%}")
        print(f"  ROI                  : {score['roi_pct']:.1f}%")
        print(f"  Trades               : {score['total_trades']}")
    else:
        print("\nNo resolved markets available for evaluation.")
    print("=" * 60)
    return {"genome": champion, "evaluation": score} if records else {"genome": champion}


def cmd_forecasts(args):
    """Dump raw forecast data for inspection."""
    records = load_resolved_markets()
    champion = load_champion()
    predict_fn = genome_to_predict_fn(champion)
    forecasts = build_forecasts(records, predict_fn, min_volume=args.min_volume)

    print(f"Total forecasts: {len(forecasts)}\n")
    for f in forecasts[:20]:
        meta = f["metadata"]
        correct = "+" if abs(f["probability"] - f["outcome"]) < 0.5 else "-"
        print(f"  {correct} p={f['probability']:.3f} "
              f"outcome={f['outcome']} "
              f"price={meta['price']:.4f} vol={meta['volume']:>8.0f}  "
              f"{meta.get('question', '')[:60]}")
    return {"count": len(forecasts), "sample": forecasts[:20]}

def main():
    parser = argparse.ArgumentParser(
        description="AutoPredict Backtesting CLI - evaluate & evolve strategy"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["backtest", "evolve", "report", "forecasts"],
        default="backtest",
        help="Operation mode (default: backtest)",
    )
    parser.add_argument(
        "--min-volume", type=float, default=1000,
        help="Minimum market volume to include (default: 1000)",
    )
    parser.add_argument(
        "--generations", "-g", type=int, default=3,
        help="Number of evolution generations (default: 3)",
    )
    parser.add_argument(
        "--population", "-p", type=int, default=10,
        help="Candidates per generation (default: 10)",
    )
    parser.add_argument(
        "--min-trades", type=int, default=5,
        help="Minimum trades to accept a genome (default: 5)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save JSON output to file",
    )

    args = parser.parse_args()

    commands = {
        "backtest": cmd_backtest,
        "evolve": cmd_evolve,
        "report": cmd_report,
        "forecasts": cmd_forecasts,
    }

    result = commands[args.mode](args)

    if args.output and result:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to {args.output}")


if __name__ == "__main__":
    main()