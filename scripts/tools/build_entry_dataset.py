#!/usr/bin/env python3
"""Build a leak-free training dataset from real resolved Polymarket markets.

For each resolved market we sample the market's YES price 7 days before it
closed (from the CLOB prices-history endpoint), then attach the eventual
resolution as the label.  Nothing in the feature vector is derived from the
post-resolution outcome, so Brier/AUC are meaningful.

Output: data/training/entry_price_dataset.json
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB = "https://clob.polymarket.com/prices-history"
UA = {"User-Agent": "polymarket-research/1.0"}
ENTRY_DAYS = 7
WINDOW_DAYS = 9
FIDELITY_MIN = 60
MIN_CLOSE_TS = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(UA)
    return s


_thread_local = threading.local()


def _thread_session() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = _session()
        _thread_local.session = sess
    return sess


def _get_json(session, url, params, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == retries - 1:
                print(f"  request failed: {exc}", file=sys.stderr)
                return None
            time.sleep(1 + attempt)
    return None


def _parse_iso(value):
    if not value:
        return None
    value = value.replace("+00", "+00:00")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def fetch_closed_markets(session, pages_per_order=12, limit=100):
    """Pull closed markets from several Gamma orderings, deduped by market id."""
    seen = {}
    orderings = [
        ("closedTime", "false"),
        ("volumeNum", "false"),
        ("endDate", "false"),
        # Oldest-first: without this, pagination never reaches pre-2023 markets.
        ("closedTime", "true"),
        ("volumeNum", "true"),
    ]
    for order, ascending in orderings:
        for page in range(pages_per_order):
            params = {
                "closed": "true",
                "limit": limit,
                "offset": page * limit,
                "order": order,
                "ascending": ascending,
            }
            markets = _get_json(session, GAMMA, params)
            if markets is None:
                break
            if not markets:
                break
            new = 0
            for m in markets:
                mid = m.get("id")
                if mid and mid not in seen:
                    seen[mid] = m
                    new += 1
            print(f"  order={order} asc={ascending} page={page}: "
                  f"{len(markets)} markets, {new} new (total {len(seen)})")
            if new == 0 and page > 0:
                break
            time.sleep(0.15)
    return list(seen.values())


def is_usable(m):
    """Structural filters + clear binary resolution."""
    if not m.get("closed"):
        return False
    q = (m.get("question") or "").strip()
    if not q:
        return False
    close_ts = _parse_iso(m.get("closedTime"))
    if close_ts is None or close_ts < MIN_CLOSE_TS:
        return False
    try:
        vol = float(m.get("volumeNum") or 0)
    except (TypeError, ValueError):
        return False
    if vol < 10000:
        return False
    tokens = m.get("clobTokenIds")
    if isinstance(tokens, str):
        try:
            tokens = json.loads(tokens)
        except json.JSONDecodeError:
            return False
    if not isinstance(tokens, list) or len(tokens) < 2:
        return False
    prices = m.get("outcomePrices")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            return False
    if not isinstance(prices, list) or len(prices) != 2:
        return False
    try:
        p0, p1 = float(prices[0]), float(prices[1])
    except (TypeError, ValueError):
        return False
    if not ((p0 >= 0.999 and p1 <= 0.001) or (p0 <= 0.001 and p1 >= 0.999)):
        return False
    outcomes = m.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            outcomes = None
    if not isinstance(outcomes, list) or len(outcomes) != 2:
        return False
    first = str(outcomes[0]).strip().lower()
    if first not in ("yes", "no"):
        return False
    return True


def sample_entry(history, entry_ts):
    """Return (price_at_entry, price_24h_before, n_points) or None."""
    if not history:
        return None
    points = sorted(
        ({"t": int(r["t"]), "p": float(r["p"])} for r in history if "t" in r and "p" in r),
        key=lambda r: r["t"],
    )
    if len(points) < 10:
        return None
    # Need coverage from at least entry_ts - 24h through entry_ts.
    if points[0]["t"] > entry_ts - 86400:
        return None
    at_entry = None
    before = None
    for row in points:
        if row["t"] <= entry_ts:
            at_entry = row
        if row["t"] <= entry_ts - 86400:
            before = row
        if row["t"] > entry_ts and at_entry is not None:
            break
    if at_entry is None or before is None:
        return None
    if not (0.01 < at_entry["p"] < 0.99):
        return None
    return at_entry["p"], before["p"], len(points)


def build_record(m):
    """Fetch one market's entry-time price. Returns (record, skip_reason)."""
    try:
        close_ts = _parse_iso(m.get("closedTime"))
        entry_ts = close_ts - ENTRY_DAYS * 86400
        start_ts = close_ts - WINDOW_DAYS * 86400
        tokens = m.get("clobTokenIds")
        if isinstance(tokens, str):
            tokens = json.loads(tokens)
        token = tokens[0]
        data = _get_json(_thread_session(), CLOB, {
            "market": token,
            "startTs": start_ts,
            "endTs": close_ts,
            "fidelity": FIDELITY_MIN,
        })
        if data is None:
            return None, "error"
        history = data.get("history", data) if isinstance(data, dict) else data
        if not history:
            return None, "history_empty"
        sampled = sample_entry(history, entry_ts)
        if sampled is None:
            return None, "no_entry"
        price_at_entry, price_prev, n_pts = sampled
        outcomes = m.get("outcomes")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        prices = m.get("outcomePrices")
        if isinstance(prices, str):
            prices = json.loads(prices)
        yes_won = float(prices[0]) >= 0.999
        first_is_yes = str(outcomes[0]).strip().lower() == "yes"
        if not first_is_yes:
            yes_won = not yes_won
        return {
            "market_id": m.get("id"),
            "question": m.get("question"),
            "timestamp": m.get("closedTime"),
            "entry_price": round(price_at_entry, 6),
            "price_24h_before": round(price_prev, 6),
            "price_velocity": round(abs(price_at_entry - price_prev), 6),
            "days_to_close": ENTRY_DAYS,
            "volume": float(m.get("volumeNum") or 0),
            "bid_ask_spread": 0.01,
            "is_crypto": int(any(
                kw in (m.get("question") or "").lower()
                for kw in ("crypto", "bitcoin", "ethereum", "solana", "btc", "eth")
            )),
            "outcome": "yes" if yes_won else "no",
            "history_points": n_pts,
            "source": "clob_prices_history",
        }, None
    except Exception as exc:
        print(f"  market {m.get('id')} failed: {exc}", file=sys.stderr)
        return None, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-candidates", type=int, default=1400)
    ap.add_argument("--pages-per-order", type=int, default=12)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join("data", "training", "entry_price_dataset.json"))
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--min-close-date", default="2023-01-01",
                    help="Earliest closedTime to accept, YYYY-MM-DD")
    args = ap.parse_args()

    global MIN_CLOSE_TS
    MIN_CLOSE_TS = int(datetime.fromisoformat(args.min_close_date).replace(
        tzinfo=timezone.utc).timestamp())

    session = _session()
    print("Fetching closed markets from Gamma...")
    markets = fetch_closed_markets(session, pages_per_order=args.pages_per_order)
    usable = [m for m in markets if is_usable(m)]
    print(f"\n{len(markets)} unique closed markets, {len(usable)} usable after filters")

    # Prefer a chronological spread rather than only mega-volume markets.
    usable.sort(key=lambda m: _parse_iso(m.get("closedTime")) or 0)
    if len(usable) > args.max_candidates:
        step = len(usable) / args.max_candidates
        usable = [usable[int(i * step)] for i in range(args.max_candidates)]
    print(f"Sampling {len(usable)} markets for CLOB history with {args.workers} workers\n")

    records = []
    skipped = {"history_empty": 0, "no_entry": 0, "error": 0}

    def work(m):
        if args.delay:
            time.sleep(args.delay)
        return build_record(m)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (rec, reason) in enumerate(pool.map(work, usable), 1):
            if rec is not None:
                records.append(rec)
            else:
                skipped[reason] += 1
            if i % 25 == 0 or i == len(usable):
                print(f"  [{i}/{len(usable)}] kept={len(records)} skipped={skipped}")

    records.sort(key=lambda r: r["timestamp"])

    if records:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        yes = sum(1 for r in records if r["outcome"] == "yes")
        print(f"\nWrote {len(records)} records to {args.out}")
        print(f"  yes={yes} ({yes/len(records):.1%})  no={len(records)-yes}")
        print(f"  price range at entry: "
              f"{min(r['entry_price'] for r in records):.3f} .. "
              f"{max(r['entry_price'] for r in records):.3f}")
        print(f"  date range: {records[0]['timestamp'][:10]} .. {records[-1]['timestamp'][:10]}")
    else:
        print("No records built.")
        print(f"skipped={skipped}")


if __name__ == "__main__":
    main()
