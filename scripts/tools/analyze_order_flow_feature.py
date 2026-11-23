"""Walk-forward test: does pre-entry order flow beat the market price?

All order-flow features come from trades strictly before the entry timestamp
(see fetch_order_flow.py), so nothing here sees the future. Every predictor is
scored on the identical set of out-of-sample rows.

Predictors
  1. price          raw entry price
  2. base           logistic on price + volume/spread/momentum
  3. base+flow24h   base plus last-24h-before-entry flow
  4. all+flow7d     base plus both flow windows
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics as st
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def _log1p(x):
    return math.log1p(max(0.0, float(x or 0.0)))


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys)


def base_features(r):
    spread = r.get("bid_ask_spread")
    return [
        r["entry_price"],
        _log1p(r.get("volume")),
        abs(r.get("price_velocity") or 0.0),
        float(r.get("is_crypto") or 0),
        0.02 if spread is None else float(spread),
        _log1p(r.get("history_points")),
    ]


def flow_features(w, entry_price):
    if not w:
        return None
    last_ts = w.get("last_yes_ts")
    stale_h = (entry_price["entry_ts"] - last_ts) / 3600.0 if last_ts else 168.0
    vwap = w.get("vwap_yes")
    gap = (vwap - entry_price["entry_price"]) if vwap is not None else 0.0
    return [
        _log1p(w.get("n_trades")),
        w.get("yes_flow_imbalance", 0.0),
        w.get("count_imbalance", 0.0),
        _log1p(w.get("n_wallets")),
        w.get("wallet_hhi", 0.0),
        _log1p(w.get("avg_notional")),
        _log1p(w.get("n_big_trades")),
        w.get("big_yes_imbalance", 0.0),
        gap,
        min(stale_h, 336.0) / 24.0,
    ]


def fit_predict(train_X, train_y, test_X):
    if not train_X:
        return None
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced"),
    )
    model.fit(np.array(train_X, dtype=float), np.array(train_y))
    return model.predict_proba(np.array(test_X, dtype=float))[:, 1]


def walk_forward(rows, feature_fn, warmup, retrain_every):
    preds = [None] * len(rows)
    model = None
    for i in range(warmup, len(rows)):
        if (i - warmup) % retrain_every == 0:
            train_X = [feature_fn(j, rows[j]) for j in range(i)]
            train_y = [1 if r["outcome"] == "yes" else 0 for r in rows[:i]]
            model = (train_X, train_y)
        if model is None:
            continue
        p = fit_predict(model[0], model[1], [feature_fn(i, rows[i])])
        preds[i] = None if p is None else float(p[0])
    return preds


def month_key(r):
    return r["timestamp"][:7]


def cluster_bootstrap(diffs, clusters, iters=4000, seed=7):
    rng = random.Random(seed)
    by = {}
    for d, c in zip(diffs, clusters):
        by.setdefault(c, []).append(d)
    keys = list(by)
    means = []
    for _ in range(iters):
        sample = [by[rng.choice(keys)] for _ in keys]
        flat = [v for group in sample for v in group]
        means.append(st.mean(flat))
    means.sort()
    return means[int(0.025 * iters)], means[int(0.975 * iters)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/training/entry_price_dataset_v4.json")
    ap.add_argument("--flow", default="data/training/order_flow_v1.jsonl")
    ap.add_argument("--warmup", type=int, default=250)
    ap.add_argument("--retrain-every", type=int, default=25)
    ap.add_argument("--out", default="data/test_runs/order_flow_analysis.json")
    args = ap.parse_args()

    recs = {r["market_id"]: r for r in json.load(open(args.dataset, encoding="utf-8"))}
    flow = {}
    for line in open(args.flow, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("windows"):
            flow[rec["market_id"]] = rec

    merged = []
    for mid, rec in recs.items():
        f = flow.get(mid)
        if not f or not f.get("complete"):
            continue
        f = dict(f)
        f["entry_price"] = rec["entry_price"]
        f["entry_ts"] = f.get("entry_ts") or 0
        merged.append((rec, f))
    merged.sort(key=lambda t: t[0]["timestamp"])
    print(f"joined rows with flow: {len(merged)} / dataset {len(recs)}")

    rows, flow24, flow7 = [], [], []
    for rec, f in merged:
        w24 = f["windows"].get("24h")
        w7 = f["windows"].get("7d")
        if not w24 or w24.get("n_trades", 0) < 5:
            continue
        f24 = flow_features(w24, f)
        f7 = flow_features(w7, f) if w7 else None
        rows.append(rec)
        flow24.append(f24)
        flow7.append(f7)

    if len(rows) < 100:
        print("not enough rows with flow; aborting")
        return

    def feat_base(i, r):
        return base_features(r)

    def feat_flow24(i, r):
        return base_features(r) + flow24[i]

    def feat_all(i, r):
        f7 = flow7[i] if flow7[i] is not None else [0.0] * 10
        return base_features(r) + flow24[i] + f7

    ys = [1 if r["outcome"] == "yes" else 0 for r in rows]
    prices = [r["entry_price"] for r in rows]

    preds = {
        "base": walk_forward(rows, feat_base, args.warmup, args.retrain_every),
        "base+flow24h": walk_forward(rows, feat_flow24, args.warmup, args.retrain_every),
    }
    if any(f is not None for f in flow7):
        preds["all+flow7d"] = walk_forward(rows, feat_all, args.warmup, args.retrain_every)

    idx = [i for i in range(len(rows)) if all(preds[k][i] is not None for k in preds)]
    print(f"scored {len(idx)} rows ({rows[idx[0]]['timestamp'][:10]} .. {rows[idx[-1]]['timestamp'][:10]})")
    sy = [ys[i] for i in idx]
    sp = [prices[i] for i in idx]
    clusters = [month_key(rows[i]) for i in idx]

    results = {"n": len(idx), "brier": {}}
    print(f"{'predictor':14s} {'brier':>8s}  {'delta vs price':>14s}  {'95% CI (month cluster)':>24s}")
    print(f"{'price':14s} {brier(sp, sy):8.4f}")
    results["brier"]["price"] = brier(sp, sy)
    for k in preds:
        pr = [preds[k][i] for i in idx]
        b = brier(pr, sy)
        diffs = [(p - y) ** 2 - (q - y) ** 2 for p, q, y in zip(pr, sp, sy)]
        lo, hi = cluster_bootstrap(diffs, clusters)
        results["brier"][k] = b
        results.setdefault("delta_vs_price", {})[k] = {
            "mean": st.mean(diffs), "ci95": [lo, hi],
        }
        print(f"{k:14s} {b:8.4f}  {st.mean(diffs):+14.4f}  [{lo:+.4f}, {hi:+.4f}]")

    # residual signal: does flow predict where the price is wrong?
    resid = [y - p for y, p in zip(sy, sp)]
    for name, arr in (("yes_flow_24h", [flow24[i][1] for i in idx]),
                      ("big_yes_24h", [flow24[i][7] for i in idx]),
                      ("vwap_gap_24h", [flow24[i][8] for i in idx])):
        mu_f, mu_r = st.mean(arr), st.mean(resid)
        cov = sum((a - mu_f) * (b - mu_r) for a, b in zip(arr, resid)) / len(arr)
        sd = st.pstdev(arr) * st.pstdev(resid)
        corr = cov / sd if sd else 0.0
        results.setdefault("residual_corr", {})[name] = corr
        print(f"corr({name}, outcome-price) = {corr:+.3f}")

    # within the band the bot actually trades
    band = [(flow24[i], ys[i], prices[i]) for i in idx if 0.05 <= prices[i] <= 0.50]
    if band:
        band.sort(key=lambda t: t[0][1])
        third = max(1, len(band) // 3)
        lo_g, hi_g = band[:third], band[-third:]
        print(f"band 0.05-0.50 n={len(band)}  low-flow yes_rate={st.mean([b[1] for b in lo_g]):.3f}"
              f"  high-flow yes_rate={st.mean([b[1] for b in hi_g]):.3f}")
        results["band"] = {
            "n": len(band),
            "low_flow_yes_rate": st.mean([b[1] for b in lo_g]),
            "high_flow_yes_rate": st.mean([b[1] for b in hi_g]),
        }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(results, open(args.out, "w", encoding="utf-8"), indent=1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
