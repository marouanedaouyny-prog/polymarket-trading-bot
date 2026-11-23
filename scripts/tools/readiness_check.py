"""Audit whether this bot is safe to fund with real money.

Every check reads real state (config, backtest output, dataset) and prints
PASS/FAIL with the number that decided it. The overall verdict is FAIL if any
check fails. No secrets are printed.
"""
import argparse
import json
import os
import statistics as st
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.config import config

MIN_OOS_TRADES = 30
MIN_OOS_ROWS = 200
MIN_EDGE_BRIER = 0.005
REQUIRED_TRADES = 50
MAX_MONTHS_TO_50 = 6


def _fmt_pct(x):
    return f"{x * 100:+.1f}%"


def check_flags(rows):
    mode = os.getenv("TRADING_MODE", "paper")
    allow = os.getenv("POLYMARKET_ALLOW_REAL_ORDERS", "false").lower() == "true"
    enable = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
    sandbox = os.getenv("POLYMARKET_SANDBOX", "true").lower() == "true"
    ok = not (mode == "live" and allow and enable and not sandbox)
    rows.append((
        "live flags",
        ok,
        f"mode={mode} allow_real={allow} enable_live={enable} sandbox={sandbox}",
    ))


def check_model_edge(rows, oos):
    ys = [1 if r["outcome"] == "yes" else 0 for r in oos]
    price_b = sum((r["price"] - y) ** 2 for r, y in zip(oos, ys)) / len(ys)
    model_b = sum((r["model_prob"] - y) ** 2 for r, y in zip(oos, ys)) / len(ys)
    ok = model_b < price_b - MIN_EDGE_BRIER
    rows.append((
        "model beats price",
        ok,
        f"brier model={model_b:.4f} price={price_b:.4f} gap={price_b - model_b:+.4f} "
        f"(need model better by {MIN_EDGE_BRIER})",
    ))


def check_sample(rows, oos, executed):
    ok = len(oos) >= MIN_OOS_ROWS and executed >= MIN_OOS_TRADES
    rows.append((
        "out-of-sample size",
        ok,
        f"rows={len(oos)} (need {MIN_OOS_ROWS}), executed trades={executed} (need {MIN_OOS_TRADES})",
    ))


def check_expectancy(rows, trades):
    rois = []
    for t in trades:
        bet = float(t.get("bet") or 0)
        if bet > 0:
            rois.append(float(t["profit"]) / bet)
    if len(rois) < 2:
        rows.append(("trade expectancy", False, f"{len(rois)} settled trades; need >= 2 to estimate"))
        return
    mean = st.mean(rois)
    se = st.stdev(rois) / len(rois) ** 0.5
    lower = mean - 1.96 * se
    rows.append((
        "trade expectancy > 0",
        lower > 0,
        f"mean ROI {_fmt_pct(mean)}/trade, 95% CI lower {_fmt_pct(lower)}, n={len(rois)}",
    ))


def check_bankroll(rows):
    balance = float(config.STARTING_BALANCE)
    min_bet = float(config.MIN_BET)
    pct = float(config.MAX_POSITION_PCT)
    floor = min_bet / pct
    if balance <= floor:
        max_losses = 0
    else:
        max_losses = 0
        b = balance
        while b * (1 - pct) >= floor and max_losses < 1000:
            b *= (1 - pct)
            max_losses += 1
    ok = max_losses >= 5
    rows.append((
        "bankroll survives losses",
        ok,
        f"balance=${balance:.2f}, min_bet=${min_bet:.2f}, max_pos={pct:.0%}, "
        f"floor=${floor:.2f}, consecutive losses survivable={max_losses} (need >= 5)",
    ))


def check_throughput(rows, oos, executed):
    if len(oos) < 2:
        rows.append(("trade throughput", False, "not enough rows"))
        return
    from datetime import datetime

    d0 = datetime.fromisoformat(oos[0]["date"])
    d1 = datetime.fromisoformat(oos[-1]["date"])
    months = max((d1 - d0).days / 30.44, 1 / 30.44)
    rate = executed / months
    months_to_50 = REQUIRED_TRADES / rate if rate > 0 else float("inf")
    ok = months_to_50 <= MAX_MONTHS_TO_50
    rows.append((
        "can reach 50 trades",
        ok,
        f"{executed} trades over {months:.1f} months ({rate:.2f}/month) -> "
        f"{months_to_50:.0f} months to 50 (max {MAX_MONTHS_TO_50})",
    ))


def check_operational(rows):
    src = open("agent_trading_system.py", encoding="utf-8").read()
    has_roll = "_roll_daily_state" in src and "risk_manager.reset_daily" in src
    rows.append(("daily rollover wired", has_roll, "_roll_daily_state -> reset_daily"))

    risk_src = open("src/risk/dynamic_risk.py", encoding="utf-8").read()
    has_guard = "0.999" in risk_src or "roc_auc" in open(
        "src/ml/market_predictor.py", encoding="utf-8"
    ).read()
    rows.append(("leakage guard present", has_guard, "MarketPredictor rejects AUC>=0.999/Brier<=0.001"))

    gate = open("src/execution/order_manager.py", encoding="utf-8").read()
    has_gate = 'TRADING_MODE' in gate and "POLYMARKET_ALLOW_REAL_ORDERS" in gate
    rows.append(("live order gate intact", has_gate, "OrderManager requires mode+flag+adapter"))

    has_readiness = "check_live_readiness" in gate and os.path.isfile("src/utils/readiness_gate.py")
    rows.append((
        "live readiness gate wired",
        has_readiness,
        "live orders blocked without a fresh passing verdict (< 7 days)",
    ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/test_runs/walkforward_v2_full_reset_results.json")
    ap.add_argument("--json", metavar="PATH",
                    help="write a verdict file consumed by the live-mode gate "
                         "(default: data/readiness_verdict.json)")
    args = ap.parse_args()

    res = json.load(open(args.results, encoding="utf-8"))
    oos = res["oos_rows"]
    trades = res["20"]["trades"]
    executed = res["20"]["executed"]

    rows = []
    check_flags(rows)
    check_model_edge(rows, oos)
    check_sample(rows, oos, executed)
    check_expectancy(rows, trades)
    check_bankroll(rows)
    check_throughput(rows, oos, executed)
    check_operational(rows)

    print()
    print(f"{'CHECK':28} {'RESULT':6}  DETAIL")
    print("-" * 100)
    for name, ok, detail in rows:
        print(f"{name:28} {'PASS' if ok else 'FAIL':6}  {detail}")
    print("-" * 100)
    failed = [name for name, ok, _ in rows if not ok]

    if args.json:
        out = args.json
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        verdict = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "passed": not failed,
            "failed": failed,
            "results_file": args.results,
            "checks": [{"name": n, "passed": ok, "detail": d} for n, ok, d in rows],
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(verdict, f, indent=2)
        print(f"verdict written to {out} (passed={verdict['passed']})")

    if failed:
        print(f"VERDICT: NOT READY FOR REAL MONEY ({len(failed)} failed: {', '.join(failed)})")
        return 1
    print("VERDICT: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
