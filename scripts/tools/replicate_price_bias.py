"""Replicate the entry-price bias on closed markets absent from the dataset.

The v4 entry dataset shows a large positive gap between realised YES rate and
the price sampled 7 days before close. This script draws a fresh set of closed
markets (skipping the pages the dataset builder already consumed), applies the
same filters, samples the same 7-day-before-close price, and reports whether
the gap repeats.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "tools"))

import build_entry_dataset as bed  # noqa: E402


def cluster_ci(vals, clusters, iters=4000, seed=9):
    import random
    rng = random.Random(seed)
    by = defaultdict(list)
    for v, c in zip(vals, clusters):
        by[c].append(v)
    keys = list(by)
    means = []
    for _ in range(iters):
        flat = [v for k in (rng.choice(keys) for _ in keys) for v in by[k]]
        means.append(st.mean(flat))
    means.sort()
    return means[int(0.025 * iters)], means[int(0.975 * iters)]


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data/test_runs/price_bias_replication.json"

    prior = []
    if os.path.exists(os.path.join(ROOT, out_path)):
        prior = json.load(open(os.path.join(ROOT, out_path), encoding="utf-8")).get("records", [])
        print(f"prior records: {len(prior)}")

    existing = {r["market_id"] for r in
                json.load(open(os.path.join(ROOT, "data/training/entry_price_dataset_v4.json"),
                               encoding="utf-8"))}
    existing |= {r["market_id"] for r in prior}

    plan = [("closedTime", "false", 14, 20), ("endDate", "false", 14, 20),
            ("volumeNum", "true", 0, 8), ("endDate", "true", 0, 8),
            ("volumeNum", "false", 10, 19), ("closedTime", "true", 14, 18)]
    candidates = []
    for order, asc, p0, p1 in plan:
        for page in range(p0, p1):
            body = bed._get_json(bed._thread_session(), bed.GAMMA, {
                "closed": "true", "limit": 100, "offset": page * 100,
                "order": order, "ascending": asc,
            })
            if not body:
                break
            fresh = 0
            for m in body:
                mid = m.get("id")
                if mid in existing or any(c["id"] == mid for c in candidates):
                    continue
                if bed.is_usable(m):
                    candidates.append(m)
                    fresh += 1
            print(f"  {order}/{asc} page {page}: +{fresh} usable (total {len(candidates)})")
            if len(candidates) >= limit * 3:
                break
        if len(candidates) >= limit * 3:
            break

    print(f"candidates: {len(candidates)}")
    records = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(bed.build_record, m) for m in candidates]
        for fut in as_completed(futures):
            rec, reason = fut.result()
            if rec:
                records.append(rec)
                if len(records) % 25 == 0:
                    print(f"  priced {len(records)}", flush=True)
            if len(records) >= limit and len(futures) > 0:
                pass

    if not records and not prior:
        print("no records")
        return
    by_id = {r["market_id"]: r for r in prior}
    for r in records:
        by_id[r["market_id"]] = r
    records = list(by_id.values())
    records.sort(key=lambda r: r["timestamp"])
    ys = [1 if r["outcome"] == "yes" else 0 for r in records]
    pr = [r["entry_price"] for r in records]
    months = [r["timestamp"][:7] for r in records]
    print(f"\nFRESH SAMPLE n={len(records)}  price={st.mean(pr):.4f}  yes_rate={st.mean(ys):.4f}  "
          f"gap={st.mean(ys)-st.mean(pr):+.4f}  months={len(set(months))}")

    for spread in (0.0, 0.005, 0.01, 0.02):
        pnl = [(y - (p + spread)) / (p + spread) for p, y in zip(pr, ys)]
        lo, hi = cluster_ci(pnl, months)
        ev = st.mean([y - (p + spread) for p, y in zip(pr, ys)])
        print(f"  buy YES @ p+{spread:.3f}: EV/contract={ev:+.4f}  mean_return={st.mean(pnl):+.3f}  "
              f"95% CI [{lo:+.3f},{hi:+.3f}]")

    json.dump({"n": len(records), "mean_price": st.mean(pr), "yes_rate": st.mean(ys),
               "records": records}, open(os.path.join(ROOT, out_path), "w", encoding="utf-8"), indent=1)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
