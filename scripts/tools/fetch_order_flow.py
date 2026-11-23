"""Collect leak-free order-flow features for every market in the entry dataset.

Trades come from the Polymarket Data API v2 feed. `start`/`end` filters are
ignored on the market shape, so the feed is walked backwards from the latest
fill and every trade at or after the entry timestamp is discarded. Only trades
strictly before entry are aggregated, which keeps the features leak-free.

Output is one JSON object per market (resumable JSONL).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

GAMMA = "https://gamma-api.polymarket.com/markets"
TRADES = "https://data-api.polymarket.com/v2/trades"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DAY = 86400
ENTRY_DAYS = 7  # matches build_entry_dataset.ENTRY_DAYS
WINDOWS = {"24h": 1 * DAY}
MIN_BIG_NOTIONAL = 1000.0

_print_lock = threading.Lock()


def _get(url, params, retries=4, timeout=45):
    delay = 1.0
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            return None
        except requests.RequestException:
            time.sleep(delay)
            delay *= 2
    return None


def condition_id_for(market_id, cache):
    if market_id in cache:
        return cache[market_id]
    body = _get(GAMMA, {"id": market_id, "closed": "true", "limit": 1})
    cid = body[0].get("conditionId") if body else None
    cache[market_id] = cid
    return cid


def _blank():
    return {
        "n_trades": 0,
        "n_buy": 0,
        "n_sell": 0,
        "notional_buy": 0.0,
        "notional_sell": 0.0,
        "notional": 0.0,
        "signed_yes_notional": 0.0,
        "big_notional": 0.0,
        "signed_yes_big": 0.0,
        "n_big": 0,
        "wallets": set(),
        "wallet_notional": {},
        "yes_size": 0.0,
        "yes_notional": 0.0,
        "last_yes_ts": None,
        "last_yes_price": None,
    }


def _accumulate(acc, row):
    side = row.get("side")
    size = float(row.get("size") or 0.0)
    price = float(row.get("price") or 0.0)
    notional = size * price
    idx = row.get("outcome_index")
    ts = row.get("timestamp")

    acc["n_trades"] += 1
    acc["notional"] += notional
    if side == "BUY":
        acc["n_buy"] += 1
        acc["notional_buy"] += notional
    else:
        acc["n_sell"] += 1
        acc["notional_sell"] += notional

    if idx is not None:
        long_yes = (side == "BUY") == (idx == 0)
        signed = notional if long_yes else -notional
        acc["signed_yes_notional"] += signed
        if notional >= MIN_BIG_NOTIONAL:
            acc["n_big"] += 1
            acc["big_notional"] += notional
            acc["signed_yes_big"] += signed
        if idx == 0:
            acc["yes_size"] += size
            acc["yes_notional"] += notional
            if ts is not None and (acc["last_yes_ts"] is None or ts > acc["last_yes_ts"]):
                acc["last_yes_ts"] = ts
                acc["last_yes_price"] = price

    wallet = row.get("proxy_wallet")
    if wallet:
        acc["wallets"].add(wallet)
        acc["wallet_notional"][wallet] = acc["wallet_notional"].get(wallet, 0.0) + notional


def _finalize(acc):
    gross = acc["notional"]
    n = acc["n_trades"]
    wallets = acc["wallets"]
    hhi = 0.0
    if gross > 0 and wallets:
        hhi = sum((v / gross) ** 2 for v in acc["wallet_notional"].values())
    return {
        "n_trades": n,
        "n_buy": acc["n_buy"],
        "n_sell": acc["n_sell"],
        "flow_imbalance": ((acc["notional_buy"] - acc["notional_sell"]) / gross) if gross > 0 else 0.0,
        "count_imbalance": ((acc["n_buy"] - acc["n_sell"]) / n) if n else 0.0,
        "yes_flow_imbalance": (acc["signed_yes_notional"] / gross) if gross > 0 else 0.0,
        "n_wallets": len(wallets),
        "wallet_hhi": hhi,
        "avg_notional": (gross / n) if n else 0.0,
        "n_big_trades": acc["n_big"],
        "big_yes_imbalance": (acc["signed_yes_big"] / acc["big_notional"]) if acc["big_notional"] > 0 else 0.0,
        "vwap_yes": (acc["yes_notional"] / acc["yes_size"]) if acc["yes_size"] > 0 else None,
        "last_yes_price": acc["last_yes_price"],
        "last_yes_ts": acc["last_yes_ts"],
    }


def collect_market(market, cid, max_pages, page_size):
    # The dataset's `timestamp` is the market's closedTime, so the entry time
    # the bot would actually trade at is ENTRY_DAYS before that.
    close_ts = int(datetime.fromisoformat(market["timestamp"].replace(" ", "T")).timestamp())
    entry_ts = close_ts - ENTRY_DAYS * DAY
    cutoff = entry_ts - max(WINDOWS.values())

    accs = {name: _blank() for name in WINDOWS}
    cursor = None
    pages = 0
    rows_seen = 0
    oldest = None
    truncated = False

    while pages < max_pages:
        params = {"condition": cid, "limit": page_size} if not cursor else {"condition": cid, "cursor": cursor}
        body = _get(TRADES, params)
        if body is None:
            truncated = True
            break
        data = body.get("data") or []
        pages += 1
        rows_seen += len(data)
        page_oldest = None
        for row in data:
            ts = row.get("timestamp")
            if ts is None:
                continue
            page_oldest = ts if page_oldest is None else min(page_oldest, ts)
            if ts >= entry_ts:
                continue
            for name, span in WINDOWS.items():
                if ts >= entry_ts - span:
                    _accumulate(accs[name], row)
        if page_oldest is not None:
            oldest = page_oldest if oldest is None else min(oldest, page_oldest)
            if page_oldest < cutoff:
                break
        cursor = (body.get("pagination") or {}).get("next_cursor")
        if not cursor or not data:
            break
        time.sleep(0.05)
    else:
        truncated = True

    complete = oldest is not None and oldest < cutoff
    out = {
        "market_id": market["market_id"],
        "question": market.get("question"),
        "close_ts": close_ts,
        "entry_ts": entry_ts,
        "condition_id": cid,
        "pages": pages,
        "rows_seen": rows_seen,
        "oldest_ts": oldest,
        "truncated": truncated,
        "complete": complete,
        "windows": {name: _finalize(acc) for name, acc in accs.items()},
    }
    return out


def load_done(path):
    done = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done[rec["market_id"]] = rec
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/training/entry_price_dataset_v4.json")
    ap.add_argument("--out", default="data/training/order_flow_v1.jsonl")
    ap.add_argument("--min-entry-date", default="2025-01-01")
    ap.add_argument("--max-pages", type=int, default=250)
    ap.add_argument("--page-size", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="Process at most N markets (0 = all)")
    args = ap.parse_args()

    with open(os.path.join(ROOT, args.dataset), encoding="utf-8") as fh:
        markets = json.load(fh)
    markets = [m for m in markets if m["timestamp"][:10] >= args.min_entry_date]
    markets.sort(key=lambda m: m["timestamp"])

    out_path = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = load_done(out_path)
    todo = [m for m in markets if m["market_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"dataset={len(markets)} already={len(done)} todo={len(todo)} -> {out_path}")

    cid_cache = {mid: rec.get("condition_id") for mid, rec in done.items()}
    cid_lock = threading.Lock()
    write_lock = threading.Lock()
    counter = {"n": 0, "empty": 0}

    def work(market):
        with cid_lock:
            cid = condition_id_for(market["market_id"], cid_cache)
        if not cid:
            close_ts = int(datetime.fromisoformat(market["timestamp"].replace(" ", "T")).timestamp())
            return {
                "market_id": market["market_id"],
                "question": market.get("question"),
                "close_ts": close_ts,
                "entry_ts": close_ts - ENTRY_DAYS * DAY,
                "condition_id": None,
                "pages": 0,
                "rows_seen": 0,
                "oldest_ts": None,
                "truncated": False,
                "complete": False,
                "windows": {},
            }
        return collect_market(market, cid, args.max_pages, args.page_size)

    with open(out_path, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, m): m for m in todo}
        for fut in as_completed(futures):
            try:
                rec = fut.result()
            except Exception as exc:  # keep the run alive on a single bad market
                m = futures[fut]
                rec = {"market_id": m["market_id"], "error": str(exc), "windows": {}}
            with write_lock:
                out.write(json.dumps(rec) + "\n")
                out.flush()
                counter["n"] += 1
                if not rec.get("windows"):
                    counter["empty"] += 1
                if counter["n"] % 25 == 0:
                    with _print_lock:
                        print(f"  {counter['n']}/{len(todo)} written ({counter['empty']} without data)", flush=True)

    print(f"done: {counter['n']} markets, {counter['empty']} without data")


if __name__ == "__main__":
    main()
