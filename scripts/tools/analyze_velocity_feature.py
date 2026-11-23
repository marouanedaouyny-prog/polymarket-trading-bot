"""Test whether 24h price momentum improves walk-forward prediction.

Compares three predictors on the same chronological out-of-sample rows:
  1. market price (baseline)
  2. model trained with price_velocity forced to 0 (current live behaviour)
  3. model trained with real price_velocity
"""
import argparse
import copy
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.ml.market_predictor import MarketPredictor


def brier(probs, ys):
    return sum((p - y) ** 2 for p, y in zip(probs, ys)) / len(ys)


def fit(records, use_velocity):
    rows = []
    for r in records:
        r = copy.deepcopy(r)
        if not use_velocity:
            r["price_velocity"] = 0.0
        rows.append(r)
    m = MarketPredictor()
    m._save_model = lambda *a, **k: None
    m._save_metrics = lambda *a, **k: None
    m.train(rows)
    return m if m.is_trained else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/training/entry_price_dataset_v2.json")
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--retrain-every", type=int, default=50)
    args = ap.parse_args()

    recs = json.load(open(args.dataset, encoding="utf-8"))
    recs.sort(key=lambda r: r["timestamp"])

    ys, prices, p_no, p_yes, vel = [], [], [], [], []
    model_no = model_yes = None
    for i in range(args.warmup, len(recs)):
        if (i - args.warmup) % args.retrain_every == 0:
            model_no = fit(recs[:i], use_velocity=False)
            model_yes = fit(recs[:i], use_velocity=True)
        if model_no is None or model_yes is None:
            continue
        r = recs[i]
        common = dict(
            price=r["entry_price"], volume=r["volume"], is_crypto=bool(r["is_crypto"]),
            days_to_close=7.0, spread=0.02, question=r["question"],
        )
        p_no.append(model_no.predict_win_probability(price_velocity=0.0, **common))
        p_yes.append(model_yes.predict_win_probability(
            price_velocity=abs(r.get("price_velocity", 0.0)), **common))
        prices.append(r["entry_price"])
        ys.append(1 if r["outcome"] == "yes" else 0)
        vel.append(abs(r.get("price_velocity", 0.0)))

    n = len(ys)
    print(f"{n} out-of-sample rows ({recs[args.warmup]['timestamp'][:10]} .. {recs[-1]['timestamp'][:10]})")
    print(f"Brier  price={brier(prices, ys):.4f}  model(no vel)={brier(p_no, ys):.4f}  "
          f"model(+vel)={brier(p_yes, ys):.4f}")

    # Directional check: correlation between momentum and the residual
    # (outcome - price). Positive means momentum predicts where price is wrong.
    if n > 10:
        mp, my = st.mean(prices), st.mean(ys)
        cov = sum((v - st.mean(vel)) * (y - p - (my - mp)) for v, y, p in zip(vel, ys, prices)) / n
        sd = st.pstdev(vel) * st.pstdev([y - p for y, p in zip(ys, prices)])
        print(f"corr(momentum, outcome-price) = {cov / sd:+.3f}" if sd else "corr undefined")

    # Does momentum separate winners within the low-price band the bot trades?
    band = [(v, y, p) for v, y, p in zip(vel, ys, prices) if 0.05 <= p <= 0.50]
    for lo, hi in ((0.0, 0.02), (0.02, 0.10), (0.10, 1.0)):
        sel = [y for v, y, p in band if lo <= v < hi]
        if sel:
            print(f"  momentum {lo:.2f}-{hi:.2f}: n={len(sel):3d} yes_rate={st.mean(sel):.3f}")


if __name__ == "__main__":
    main()
