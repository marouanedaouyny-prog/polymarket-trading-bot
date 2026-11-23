#!/usr/bin/env python3
"""Measure realised returns by entry-price band on resolved markets.

Answers: is there any systematic mispricing in the 5-50c segment the bot
trades?  For every band we report the YES hit rate versus the average price,
plus the per-trade ROI of buying YES and of buying NO, net of fees.

A band where |realised - price| is much larger than the standard error is
evidence of a real edge (or of a data problem).
"""

import argparse
import json
import math
import os

BANDS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
         (0.30, 0.40), (0.40, 0.50), (0.50, 0.70), (0.70, 1.00)]


def roi_stats(returns):
    n = len(returns)
    if n == 0:
        return None
    mean = sum(returns) / n
    if n > 1:
        var = sum((r - mean) ** 2 for r in returns) / (n - 1)
        se = math.sqrt(var / n)
    else:
        se = float("nan")
    return {"n": n, "mean": mean, "se": se,
            "t": (mean / se) if se and se > 0 else None}


def band_stats(rows, lo, hi, fee):
    sel = [r for r in rows if lo <= r["entry_price"] < hi]
    if not sel:
        return None
    n = len(sel)
    yes = sum(1 for r in sel if r["outcome"] == "yes")
    avg_price = sum(r["entry_price"] for r in sel) / n
    yes_roi = [
        ((1 / r["entry_price"] - 1) * (1 - fee)) if r["outcome"] == "yes" else -1.0
        for r in sel if 0 < r["entry_price"] < 1
    ]
    no_roi = [
        ((1 / (1 - r["entry_price"]) - 1) * (1 - fee)) if r["outcome"] == "no" else -1.0
        for r in sel if 0 < r["entry_price"] < 1
    ]
    return {
        "band": f"{lo:.2f}-{hi:.2f}",
        "n": n,
        "avg_price": round(avg_price, 4),
        "yes_rate": round(yes / n, 4),
        "price_minus_yes_rate": round(avg_price - yes / n, 4),
        "yes_roi": roi_stats(yes_roi),
        "no_roi": roi_stats(no_roi),
    }


def print_table(title, stats):
    print(f"\n{title}")
    print(f"{'band':>10} {'n':>5} {'avg_px':>7} {'yes%':>6} {'px-yes':>7} "
          f"{'YES roi':>9} {'t':>6} | {'NO roi':>9} {'t':>6}")
    for s in stats:
        if not s:
            continue
        y = s["yes_roi"]
        n = s["no_roi"]
        yt = f"{y['t']:+.2f}" if y and y["t"] is not None else "   -"
        nt = f"{n['t']:+.2f}" if n and n["t"] is not None else "   -"
        print(f"{s['band']:>10} {s['n']:>5} {s['avg_price']:>7.3f} "
              f"{s['yes_rate']*100:>5.1f}% {s['price_minus_yes_rate']:>+7.3f} "
              f"{y['mean']*100:>+8.1f}% {yt:>6} | "
              f"{n['mean']*100:>+8.1f}% {nt:>6}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+",
                    default=[os.path.join("data", "training", "entry_price_dataset.json")])
    ap.add_argument("--fee", type=float, default=0.07)
    ap.add_argument("--split", type=float, default=0.7,
                    help="chronological train fraction; the rest is held out")
    ap.add_argument("--out", default=os.path.join("data", "test_runs", "edge_analysis.json"))
    args = ap.parse_args()

    out = {}
    for path in args.datasets:
        rows = json.load(open(path, encoding="utf-8"))
        rows = [r for r in rows if 0 < r["entry_price"] < 1]
        print(f"\n=== {path}: {len(rows)} resolved markets "
              f"({rows[0]['timestamp'][:10]} .. {rows[-1]['timestamp'][:10]}) ===")
        stats = [band_stats(rows, lo, hi, args.fee) for lo, hi in BANDS]
        print_table(f"Fee {args.fee:.0%}", stats)
        overall = band_stats(rows, 0.0, 1.0, args.fee)
        print(f"\nOverall: YES roi {overall['yes_roi']['mean']*100:+.1f}% "
              f"(t={overall['yes_roi']['t']:+.2f}), "
              f"NO roi {overall['no_roi']['mean']*100:+.1f}% "
              f"(t={overall['no_roi']['t']:+.2f})")

        # Bot's actual trading window, all markets.
        w = band_stats(rows, 0.05, 0.5001, args.fee)
        if w:
            print(f"Bot window 0.05-0.50: n={w['n']} yes_rate={w['yes_rate']*100:.1f}% "
                  f"avg_px={w['avg_price']:.3f} YES roi={w['yes_roi']['mean']*100:+.1f}% "
                  f"NO roi={w['no_roi']['mean']*100:+.1f}%")

        # Chronological holdout: does the effect survive after the split?
        split = max(1, int(len(rows) * args.split))
        train, test = rows[:split], rows[split:]
        print(f"\nChronological split at {split}: train ends {train[-1]['timestamp'][:10]}, "
              f"test {len(test)} markets from {test[0]['timestamp'][:10]}")
        for name, subset in (("train", train), ("test", test)):
            st = [band_stats(subset, lo, hi, args.fee) for lo, hi in BANDS]
            print_table(f"{name} ({len(subset)} markets)", st)
            win = band_stats(subset, 0.05, 0.5001, args.fee)
            if win:
                print(f"  {name} bot window: n={win['n']} "
                      f"YES roi={win['yes_roi']['mean']*100:+.1f}% "
                      f"(t={win['yes_roi']['t']:+.2f})")

        # Annual stability for the two key bands.
        print("\nAnnual stability (YES roi / n):")
        years = sorted({r["timestamp"][:4] for r in rows})
        keys = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.50)]
        header = "year " + "".join(f"{f'{lo:.2f}-{hi:.2f}':>20}" for lo, hi in keys)
        print(header)
        for y in years:
            line = f"{y:>4} "
            for lo, hi in keys:
                sel = [r for r in rows if r["timestamp"].startswith(y)
                       and lo <= r["entry_price"] < hi]
                if not sel:
                    line += f"{'-':>20}"
                    continue
                r = roi_stats([
                    ((1 / x["entry_price"] - 1) * (1 - args.fee))
                    if x["outcome"] == "yes" else -1.0
                    for x in sel if 0 < x["entry_price"] < 1
                ])
                line += f"{r['mean']*100:>+12.1f}%/n{r['n']:<6}"
            print(line)
        out[os.path.basename(path)] = {"bands": stats, "overall": overall,
                                       "bot_window": w}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
