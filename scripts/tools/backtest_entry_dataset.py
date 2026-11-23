#!/usr/bin/env python3
"""Walk-forward backtest of the live agent stack on real resolved markets.

Protocol
--------
1. Sort the 424 real entry-time records chronologically.
2. Warm up on the first WARMUP records, then for every later record retrain a
   fresh model on all data *before* that record (no lookahead) and predict it.
3. Feed the out-of-sample prediction through the real research filters, the
   real RiskAgent, and the real TraderAgent (TradingAgentSystem), settling each
   trade against the market's actual resolution.
4. Run two bankrolls: the user's $20 and a $100 diagnostic (same rules).

Every trade is settled by the code in agent_trading_system.py, not by this
script.  Filesystem side effects (SQLite, paper ledger, risk state) are stubbed
so the run does not pollute live data.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("FASTAPI_API_KEY", "test-key")

DATASET = os.path.join("data", "training", "entry_price_dataset.json")
OUT = os.path.join("data", "test_runs", "walkforward_50trade_results.json")
WARMUP = 120
RETRAIN_EVERY = 25
TARGET_TRADES = 50
FEE = 0.07


def stub_side_effects():
    """Prevent the real stack from writing DB/ledger/state files during a backtest."""
    import src.data.sqlite_db as sdb
    sdb.get_db = lambda *a, **k: None

    import src.trading.ledger as ledger_mod
    class _NoLedger:
        def record_entry(self, *a, **k):
            return None
        def record_resolution(self, *a, **k):
            return None
    ledger_mod.PaperLedger = _NoLedger

    import src.risk.state_storage as state_mod
    state_mod.save_state = lambda *a, **k: None
    state_mod.load_state = lambda *a, **k: {}

    import src.trading.signal_accuracy as acc_mod
    class _NoTracker:
        def log_outcome(self, *a, **k):
            return None
    acc_mod.get_tracker = lambda *a, **k: _NoTracker()


def train_oos_model(records, upto):
    from src.ml.market_predictor import MarketPredictor
    p = MarketPredictor()
    p._save_model = lambda: None
    p._save_metrics = lambda *a, **k: None
    p.train(records[:upto])
    return p if p.is_trained else None


def make_opportunity(rec, model, sentiment_agent):
    q = rec["question"]
    price = float(rec["entry_price"])
    volume = float(rec["volume"])
    senti = sentiment_agent.analyze_sentiment(q)
    confidence = min(max(senti["score"] * 100, 0), 100)
    is_crypto = bool(rec.get("is_crypto"))
    p = model.predict_win_probability(
        price=price, volume=volume, edge=0.0, confidence=confidence,
        is_crypto=is_crypto, question=q, days_to_close=7.0, spread=0.02,
    )
    ev = (p * ((1 / price - 1) * (1 - FEE))) - (1 - p)
    return {
        "market_id": rec.get("market_id"),
        "canonical_id": f"BT-{rec.get('market_id')}",
        "question": q,
        "price": price,
        "volume": volume,
        "edge": p - price,
        "confidence": confidence,
        "sector": "crypto" if is_crypto else "other",
        "sentiment_score": senti["score"],
        "ev": ev,
        "model_prob": p,
        "outcome": rec["outcome"],
        "date": rec["timestamp"][:10],
    }, senti


def research_gate(opp, senti):
    """Mirror of TradingAgentSystem.research_agent filters."""
    reasons = []
    if "Analysis failed" in senti.get("reasoning", "") or senti["score"] < 0.1:
        reasons.append("sentiment")
    if not (0.05 <= opp["price"] <= 0.50):
        reasons.append("price_range")
    if opp["volume"] < 10000:
        reasons.append("volume")
    if opp["ev"] < 0.10:
        reasons.append("ev")
    if opp["edge"] < 0.08:
        reasons.append("edge")
    if opp["confidence"] < 70:
        reasons.append("confidence")
    return reasons


def run_bankroll(start_balance, candidates, sentiment_agent, max_attempts, target_trades):
    from agent_trading_system import TradingAgentSystem

    system = TradingAgentSystem(starting_balance=start_balance)
    system.resolved_outcomes = {}
    system.identity_manager = None
    system.db = None
    system.ledger = None
    system.trades_today = 0
    system.daily_start = start_balance
    system.killed = False
    if system.risk_manager:
        system.risk_manager.start_session(start_balance)

    state = {
        "starting_balance": start_balance,
        "attempts": 0,
        "research_passed": 0,
        "approved": 0,
        "executed": 0,
        "wins": 0,
        "losses": 0,
        "research_blocked": {},
        "risk_blocked": {},
        "halted": None,
        "trades": [],
        "model_prob_sum": 0.0,
        "entry_price_sum": 0.0,
    }

    last_date = None
    for cand in candidates:
        if state["attempts"] >= max_attempts or state["executed"] >= target_trades or state["halted"]:
            break

        opp = cand["opp"]
        rec = cand["rec"]
        model = cand["model"]

        # daily counters reset on a new calendar day
        if opp["date"] != last_date:
            last_date = opp["date"]
            system.trades_today = 0
            system.daily_start = system.balance
            if system.risk_manager:
                # reset_daily() exists in DynamicRiskManager but is never called
                # by the live system; without this a single loss day freezes
                # all future entries.
                system.risk_manager.reset_daily(system.balance)

        state["attempts"] += 1
        system.ml_model = model
        system.resolved_outcomes[opp["canonical_id"]] = opp["outcome"]

        reasons = research_gate(opp, cand["sentiment"])
        if reasons:
            for r in reasons:
                state["research_blocked"][r] = state["research_blocked"].get(r, 0) + 1
            continue
        state["research_passed"] += 1

        risk = system.risk_agent(opp)
        if not risk["approved"]:
            key = risk["reason"]
            state["risk_blocked"][key] = state["risk_blocked"].get(key, 0) + 1
            if "Balance too low" in key:
                state["halted"] = f"balance floor: ${system.balance:.2f}"
            continue
        state["approved"] += 1

        balance_before = system.balance
        result = system.trader_agent(opp)
        if result.get("blocked") or result.get("won") is None:
            state["risk_blocked"]["trader_blocked"] = state["risk_blocked"].get("trader_blocked", 0) + 1
            continue

        state["executed"] += 1
        state["model_prob_sum"] += opp["model_prob"]
        state["entry_price_sum"] += opp["price"]
        if result["won"]:
            state["wins"] += 1
        else:
            state["losses"] += 1
        bet = max(balance_before * 0.05, 1.0)
        state["trades"].append({
            "date": opp["date"],
            "question": opp["question"][:80],
            "price": round(opp["price"], 4),
            "model_prob": round(opp["model_prob"], 4),
            "edge": round(opp["edge"], 4),
            "bet": round(bet, 4),
            "won": result["won"],
            "profit": round(result["profit"], 4),
            "balance": round(system.balance, 4),
        })

    state["final_balance"] = round(system.balance, 4)
    state["pnl"] = round(system.balance - start_balance, 4)
    state["pnl_pct"] = round((system.balance - start_balance) / start_balance * 100, 2)
    state["win_rate"] = (
        round(state["wins"] / state["executed"] * 100, 1) if state["executed"] else None
    )
    state["avg_entry_price"] = (
        round(state["entry_price_sum"] / state["executed"], 4) if state["executed"] else None
    )
    state["avg_model_prob"] = (
        round(state["model_prob_sum"] / state["executed"], 4) if state["executed"] else None
    )
    state["max_drawdown"] = (
        round(getattr(system.risk_manager, "max_drawdown", 0.0), 4)
        if system.risk_manager else None
    )
    return state


def main():
    global WARMUP, RETRAIN_EVERY
    import argparse
    from src.agents.sentiment_agent import SentimentAgent

    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--warmup", type=int, default=WARMUP)
    ap.add_argument("--retrain-every", type=int, default=RETRAIN_EVERY)
    ap.add_argument("--max-attempts", type=int, default=TARGET_TRADES)
    ap.add_argument("--target-trades", type=int, default=TARGET_TRADES)
    args = ap.parse_args()

    WARMUP = args.warmup
    RETRAIN_EVERY = args.retrain_every

    stub_side_effects()

    records = json.load(open(args.dataset, encoding="utf-8"))
    records.sort(key=lambda r: r["timestamp"])
    print(f"{len(records)} records, {records[0]['timestamp'][:10]} .. {records[-1]['timestamp'][:10]}")

    sentiment_agent = SentimentAgent()
    oos = []
    model = None
    retrains = 0
    for i, rec in enumerate(records):
        if i < WARMUP:
            continue
        if model is None or (i - WARMUP) % RETRAIN_EVERY == 0:
            new_model = train_oos_model(records, i)
            retrains += 1
            if new_model is None:
                print(f"  retrain at {i} failed (leakage guard or too few rows)")
            else:
                model = new_model
                print(f"  retrain @ {i} ({rec['timestamp'][:10]})")
        if model is None:
            continue
        opp, senti = make_opportunity(rec, model, sentiment_agent)
        oos.append({"opp": opp, "rec": rec, "model": model, "sentiment": senti})

    passing = [o for o in oos if not research_gate(o["opp"], o["sentiment"])]
    print(f"\n{retrains} retrains, {len(oos)} out-of-sample candidates, "
          f"{len(passing)} pass the research gate\n")

    results = {}
    for balance in (20.0, 100.0):
        print(f"=== Bankroll ${balance:.0f} ===")
        st = run_bankroll(balance, oos, sentiment_agent,
                          max_attempts=args.max_attempts,
                          target_trades=args.target_trades)
        print(f"  attempts={st['attempts']} research_passed={st['research_passed']} "
              f"approved={st['approved']} executed={st['executed']} "
              f"W/L={st['wins']}/{st['losses']} PnL=${st['pnl']:.2f} ({st['pnl_pct']:+.1f}%)")
        if st["halted"]:
            print(f"  HALTED: {st['halted']}")
        print(f"  research rejections: {st['research_blocked']}")
        print(f"  risk rejections: {st['risk_blocked']}")
        results[str(int(balance))] = st

    # Price-baseline reference on the same out-of-sample rows.
    y = [1 if o["rec"]["outcome"] == "yes" else 0 for o in oos]
    if y:
        price_brier = sum((o["opp"]["price"] - t) ** 2 for o, t in zip(oos, y)) / len(y)
        model_brier = sum((o["opp"]["model_prob"] - t) ** 2 for o, t in zip(oos, y)) / len(y)
        py = [1 if o["rec"]["outcome"] == "yes" else 0 for o in passing]
        pass_price_brier = (
            sum((o["opp"]["price"] - t) ** 2 for o, t in zip(passing, py)) / len(py)
            if py else None
        )
        pass_model_brier = (
            sum((o["opp"]["model_prob"] - t) ** 2 for o, t in zip(passing, py)) / len(py)
            if py else None
        )
        naive_yes_roi = (
            sum(((1 / o["opp"]["price"] - 1) * (1 - FEE)) if t == 1 else -1.0
                for o, t in zip(passing, py)) / len(py)
            if py else None
        )
        print(f"\nOOS Brier (all {len(oos)}):  price={price_brier:.4f}  model={model_brier:.4f}")
        if py:
            print(f"OOS Brier (research-passing {len(py)}): "
                  f"price={pass_price_brier:.4f}  model={pass_model_brier:.4f}")
            print(f"Naive buy-YES ROI per passing trade: {naive_yes_roi*100:+.1f}%")
        results["oos_summary"] = {
            "n_candidates": len(oos),
            "n_research_passing": len(passing),
            "price_brier": round(price_brier, 4),
            "model_brier": round(model_brier, 4),
            "passing_price_brier": round(pass_price_brier, 4) if pass_price_brier is not None else None,
            "passing_model_brier": round(pass_model_brier, 4) if pass_model_brier is not None else None,
            "passing_naive_yes_roi_pct": round(naive_yes_roi * 100, 2) if naive_yes_roi is not None else None,
            "passing_yes_rate": round(sum(py) / len(py), 4) if py else None,
        }

    results["protocol"] = {
        "dataset": args.dataset,
        "records": len(records),
        "warmup": WARMUP,
        "retrain_every": RETRAIN_EVERY,
        "target_trades": TARGET_TRADES,
        "max_attempts": TARGET_TRADES,
        "oos_candidates": len(oos),
        "timestamp": datetime.now().isoformat(),
    }
    results["oos_rows"] = [
        {
            "date": o["opp"]["date"],
            "question": o["opp"]["question"],
            "price": o["opp"]["price"],
            "model_prob": o["opp"]["model_prob"],
            "edge": round(o["opp"]["edge"], 6),
            "ev": round(o["opp"]["ev"], 6),
            "confidence": o["opp"]["confidence"],
            "volume": o["opp"]["volume"],
            "is_crypto": o["rec"]["is_crypto"],
            "outcome": o["rec"]["outcome"],
        }
        for o in oos
    ]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
