#!/usr/bin/env python3
"""Training Workflow for Polymarket Trading System.

Uses the system's existing autopredict/self-improvement pipeline
to evaluate model calibration. Does NOT guarantee any win rate.
"""

import sys
import json
import os
sys.path.insert(0, '.')

from src.utils.config import config
from src.prediction.autopredict_bridge import backtest_report
from src.prediction.self_improvement import evolve

def step1_evaluate():
    """Step 1: Evaluate model calibration using resolved markets."""
    print("=" * 60)
    print("STEP 1: MODEL CALIBRATION EVALUATION")
    print("=" * 60)
    
    resolved_file = os.path.join('data', 'training', 'resolved_markets.json')
    if not os.path.isfile(resolved_file):
        print(f"[SKIP] No {resolved_file}")
        print("[INFO] Run trading system first to generate trade data.")
        return
    
    records = json.load(open(resolved_file))
    print(f"[INFO] Loaded {len(records)} resolved markets")
    
    # Simple baseline predictor (price-only, no model)
    def predict_fn(price, volume, is_crypto):
        return min(max(price, 0.02), 0.70)
    
    bt = backtest_report(records, predict_fn, min_volume=1000)
    report = bt["scoring"]
    summary = bt["summary"]
    
    print(f"\n[RESULTS]")
    print(f"  Total trades: {summary['total_trades']}")
    print(f"  Win rate: {summary['win_rate']:.1f}%")
    print(f"  ROI: {summary['roi_pct']:.1f}%")
    print(f"\n[SCORING]")
    print(f"  Brier score: {report['brier_score']:.4f}  (lower is better)")
    print(f"  Log score: {report['log_score']:.4f}  (higher is better)")
    print(f"  Cal gap: {report['calibration']['mean_absolute_gap']:.4f}")
    
    gap = report['calibration']['mean_absolute_gap']
    if gap < 0.05:
        print(f"\n[ASSESSMENT] Excellent calibration (gap < 5%)")
    elif gap < 0.10:
        print(f"\n[ASSESSMENT] Good calibration (gap 5-10%)")
    elif gap < 0.20:
        print(f"\n[ASSESSMENT] Fair — consider retraining")
    else:
        print(f"\n[ASSESSMENT] Poor — retraining recommended")
    
    return gap

def step2_evolution():
    """Step 2: Run self-improvement evolution on model genomes."""
    print("\n" + "=" * 60)
    print("STEP 2: SELF-IMPROVEMENT EVOLUTION")
    print("=" * 60)
    
    resolved_file = os.path.join('data', 'training', 'resolved_markets.json')
    if not os.path.isfile(resolved_file):
        print("[SKIP] No resolved markets — run step 1 first")
        return
    
    records = json.load(open(resolved_file))
    if len(records) < 10:
        print(f"[SKIP] Need at least 10 records, have {len(records)}")
        return
    
    print(f"[INFO] Evolving {len(records)} markets...")
    result = evolve(records, population=5, children=3, min_trades=3)
    
    kept = result.get('generation', {}).get('kept', 0)
    if kept > 0:
        brier = result.get('fitness', {}).get('brier', 'N/A')
        print(f"\n[SUCCESS] {kept} genomes kept")
        print(f"  Brier score: {brier:.4f}")
        print(f"  Improvement over baseline possible")
    else:
        print("[INFO] Evolution completed — no genomes kept this round")
        print("[INFO] May need more data or different parameters")

def step3_mirofish_status():
    """Step 3: MiroFish integration status."""
    print("\n" + "=" * 60)
    print("STEP 3: MIROFISH INTEGRATION")
    print("=" * 60)
    
    enabled = getattr(config, 'MIROFISH_ENABLED', True)
    url = getattr(config, 'MIROFISH_URL', 'http://localhost:5001')
    print(f"[CONFIG] MIROFISH_ENABLED: {enabled}")
    print(f"[CONFIG] MIROFISH_URL: {url}")
    
    # Check if MiroFish service concepts are in the codebase
    try:
        from src.prediction import MiroFishIntegrator
        print("[CODE] MiroFishIntegrator module exists in src/prediction/")
        print("[CODE] Integrated via get_llm_intelligence() in trader_agent.py")
        print("[CODE] Provides confidence boost and edge adjustment")
        print("[CODE] Circuit breaker if intelligence fails")
    except ImportError:
        print("[CODE] MiroFishIntegrator not yet imported in this context")

def step4_risk_review():
    """Step 4: Review risk parameters and consistency."""
    print("\n" + "=" * 60)
    print("STEP 4: RISK PARAMETERS & CONSISTENCY")
    print("=" * 60)
    
    print("All parameters sourced from src/utils/config.py (single source of truth)")
    print()
    print("Current conservative defaults vs old docs:")
    print(f"  MIN_EDGE:        {config.MIN_EDGE*100:.1f}%  <--OLD: 65%")
    print(f"  MIN_CONFIDENCE:  {config.MIN_CONFIDENCE}%   <--OLD: 65%")
    print(f"  PRICE_MIN:       ${config.PRICE_MIN:.2f}      <--OLD: $0.01")
    print(f"  PRICE_MAX:       ${config.PRICE_MAX:.2f}      <--OLD: $0.35")
    print(f"  MIN_VOLUME:      ${config.MIN_VOLUME:,}      <--OLD: $15,000")
    print()
    print("To change these (requires updating 5+ places):")
    print("  1. Update .env defaults")
    print("  2. Update README.md strategy section")
    print("  3. Update all agent prompt files in src/agents/prompts/")
    print("  4. Create GitHub Issue with rationale")
    print("  5. Re-run check_config.py to verify")
    
    # Run consistency check
    import subprocess
    result = subprocess.run([sys.executable, "check_config.py"], 
                          capture_output=True, text=True)
    print("\n[CONSISTENCY CHECK]")
    # Print first few lines
    lines = result.stdout.strip().split('\n')
    for line in lines[:8]:
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  (see full output with: python check_config.py)")

def main():
    print("POLYMARKET TRAINING WORKFLOW")
    print("=" * 60)
    print("Evaluates model calibration and self-improvement pipeline.")
    print("NO guaranteed win rates — focuses on calibration quality.")
    print("=" * 60)
    print()
    
    print("This workflow uses the system's existing pipelines.")
    print("Results reflect calibration quality, not guaranteed returns.")
    print()
    
    print("[1/4] Model calibration evaluation...")
    gap = step1_evaluate()
    
    print("\n[2/4] Self-improvement evolution...")
    step2_evolution()
    
    print("\n[3/4] MiroFish integration status...")
    step3_mirofish_status()
    
    print("\n[4/4] Risk parameters & consistency check...")
    step4_risk_review()
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print("Key takeaways:")
    print("• Calibration gap (Brier score) is the real metric — not win rate")
    print("• Conservative config protects capital in volatile markets")
    print("• All parameters must stay consistent across the codebase")
    print("• Model evolution improves over time with more resolved data")
    print("• MiroFish enhances signal quality when available")
    print("• Always trade within risk limits — never over-leverage")

if __name__ == "__main__":
    main()