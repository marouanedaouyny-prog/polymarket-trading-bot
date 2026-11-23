"""Do Polymarket crypto threshold markets misprice option math?

For every crypto market in the entry dataset with a parseable strike and
deadline, compute the risk-neutral touch probability implied by realised
volatility (30 days of hourly Binance closes before entry) and compare its
Brier score with the market's own entry price.

This is a direct calibration comparison: no training, no fitted parameters,
so there is no walk-forward machinery to get wrong.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics as st
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

BINANCE = "https://api.binance.com/api/v3/klines"
GAMMA = "https://gamma-api.polymarket.com/markets"
DVOL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

_session = requests.Session()
_session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=4, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])))
SYMBOLS = [
    (("bitcoin", "btc"), "BTCUSDT"),
    (("ethereum", " eth", "eth "), "ETHUSDT"),
    (("solana",), "SOLUSDT"),
    (("xrp",), "XRPUSDT"),
    (("dogecoin", "doge"), "DOGEUSDT"),
]
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

STRIKE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k|m)?", re.I)
UP_RE = re.compile(r"\b(reach|hit|above|exceed|top)\b", re.I)
DOWN_RE = re.compile(r"\b(dip|drop|fall|below|crash)\b", re.I)
BY_DATE_RE = re.compile(r"\bby\s+([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", re.I)
IN_MONTH_RE = re.compile(r"\bin\s+([a-z]+)\b", re.I)
IN_YEAR_RE = re.compile(r"\bin\s+(\d{4})\b", re.I)
Q_RE = re.compile(r"\bQ([1-4])\s*(\d{4})?\b", re.I)


def _norm(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def symbol_for(question):
    q = " " + question.lower() + " "
    for keys, sym in SYMBOLS:
        if any(k in q for k in keys):
            return sym
    return None


def parse_strike(question):
    m = STRIKE_RE.search(question)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        val *= 1_000
    elif suffix == "m":
        val *= 1_000_000
    return val


def parse_deadline(question, close_dt):
    m = BY_DATE_RE.search(question)
    if m and m.group(1).lower() in MONTHS:
        try:
            return datetime(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)),
                            23, 59, tzinfo=timezone.utc)
        except ValueError:
            return None
    q = Q_RE.search(question)
    if q and q.group(2):
        year = int(q.group(2))
        month = int(q.group(1)) * 3
        return datetime(year, month, 1, tzinfo=timezone.utc) + timedelta(days=31)
    m = IN_YEAR_RE.search(question)
    if m:
        return datetime(int(m.group(1)), 12, 31, 23, 59, tzinfo=timezone.utc)
    m = IN_MONTH_RE.search(question)
    if m and m.group(1).lower() in MONTHS:
        month = MONTHS[m.group(1).lower()]
        year = close_dt.year
        if month > close_dt.month + 1:
            year -= 1
        end = datetime(year, month, 1, tzinfo=timezone.utc) + timedelta(days=31)
        return end.replace(day=1) - timedelta(minutes=1)
    return None


def klines(symbol, start_ms, end_ms):
    out = []
    cursor = start_ms
    while cursor < end_ms:
        try:
            r = _session.get(BINANCE, params={
                "symbol": symbol, "interval": "1h", "startTime": cursor,
                "endTime": end_ms, "limit": 1000,
            }, headers=HEADERS, timeout=30)
        except requests.RequestException as exc:
            print(f"  klines {symbol} failed: {exc.__class__.__name__}")
            return None
        if r.status_code != 200:
            print(f"  klines {symbol} http {r.status_code}")
            return None
        rows = r.json()
        if not rows:
            break
        out.extend(rows)
        cursor = rows[-1][0] + 3_600_000
        if len(rows) < 1000:
            break
        time.sleep(0.1)
    return out


def spot_and_vol(symbol, entry_ts, lookback_days=30):
    entry_ms = int(entry_ts * 1000)
    start_ms = entry_ms - lookback_days * 86_400_000
    rows = klines(symbol, start_ms, entry_ms)
    if not rows or len(rows) < 100:
        return None, None
    closes = [float(r[4]) for r in rows if r[0] <= entry_ms]
    if len(closes) < 100:
        return None, None
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    if len(rets) < 50:
        return None, None
    hourly = st.pstdev(rets)
    return closes[-1], hourly * math.sqrt(24 * 365)


_DVOL_CACHE = {}


def dvol_at(currency, entry_ts):
    """Deribit 30-day implied vol (fraction) as of the entry day."""
    key = (currency, entry_ts // 86400)
    if key in _DVOL_CACHE:
        return _DVOL_CACHE[key]
    end_ms = int(entry_ts * 1000)
    start_ms = end_ms - 6 * 86_400_000
    try:
        r = _session.get(DVOL, params={"currency": currency, "start_timestamp": start_ms,
                                       "end_timestamp": end_ms, "resolution": "1D"},
                         headers=HEADERS, timeout=30)
        data = r.json()["result"]["data"] if r.status_code == 200 else []
    except Exception:
        data = []
    closes = [(row[0], float(row[4])) for row in data if row[0] <= end_ms]
    val = closes[-1][1] / 100.0 if closes else None
    _DVOL_CACHE[key] = val
    return val


def touch_prob(spot, strike, sigma, years, up):
    """First-passage probability of ever touching the level before expiry.

    Uses the risk-neutral log drift -0.5*sigma^2 and the reflection term:
        P = Phi((-b - 0.5*s^2*T)/(s*sqrt(T)))
            + exp(-b) * Phi((-b + 0.5*s^2*T)/(s*sqrt(T)))
    with b = |ln(strike/spot)|. Valid for either barrier direction.
    """
    if sigma <= 0 or years <= 0 or spot <= 0 or strike <= 0:
        return None
    b = abs(math.log(strike / spot))
    s = sigma * math.sqrt(years)
    p = _norm((-b - 0.5 * sigma * sigma * years) / s) + \
        math.exp(-b) * _norm((-b + 0.5 * sigma * sigma * years) / s)
    return min(1.0, max(0.0, p))


def digital_prob(spot, strike, sigma, years):
    """P(S_T above strike) for a terminal-value market."""
    if sigma <= 0 or years <= 0:
        return None
    d2 = (math.log(spot / strike) - 0.5 * sigma * sigma * years) / (sigma * math.sqrt(years))
    return _norm(d2)


def classify_rule(description, question, spot, strike):
    """Read the resolution text; fall back to spot-vs-strike direction."""
    d = (description or "").lower()
    if "low" in d and ("or lower" in d or "below" in d):
        return "down_touch"
    if "high" in d and ("or higher" in d or "above" in d):
        return "up_touch"
    if "final price" in d or "at 12:00" in d:
        return "digital"
    if DOWN_RE.search(question):
        return "down_touch"
    if UP_RE.search(question):
        return "up_touch"
    return "up_touch" if spot < strike else "down_touch"


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/training/entry_price_dataset_v4.json")
    ap.add_argument("--out", default="data/test_runs/crypto_option_edge.json")
    args = ap.parse_args()

    recs = json.load(open(args.dataset, encoding="utf-8"))
    rows, skipped = [], {}
    for r in recs:
        q = r["question"]
        sym = symbol_for(q)
        if not sym:
            continue
        up, down = bool(UP_RE.search(q)), bool(DOWN_RE.search(q))
        if up == down:
            skipped["direction"] = skipped.get("direction", 0) + 1
            continue
        strike = parse_strike(q)
        if not strike:
            skipped["strike"] = skipped.get("strike", 0) + 1
            continue
        close_dt = datetime.fromisoformat(r["timestamp"].replace(" ", "T"))
        deadline = parse_deadline(q, close_dt)
        if not deadline:
            skipped["deadline"] = skipped.get("deadline", 0) + 1
            continue
        entry_ts = int(close_dt.timestamp()) - 7 * 86400
        years = (deadline.timestamp() - entry_ts) / (365 * 86400)
        if years <= 0:
            skipped["expired"] = skipped.get("expired", 0) + 1
            continue
        rows.append({**r, "_sym": sym, "_strike": strike, "_years": years, "_up": up})

    print(f"parsed {len(rows)} crypto markets; skipped {skipped}")
    desc_cache = {}
    priced = []
    for r in rows:
        entry_ts = int(datetime.fromisoformat(r["timestamp"].replace(" ", "T")).timestamp()) - 7 * 86400
        spot, sigma = spot_and_vol(r["_sym"], entry_ts)
        if spot is None:
            continue
        mid = r["market_id"]
        if mid not in desc_cache:
            g = _session.get(GAMMA, params={"id": mid, "closed": "true", "limit": 1},
                             headers=HEADERS, timeout=30)
            body = g.json() if g.status_code == 200 else []
            desc_cache[mid] = (body[0].get("description") or "") if body else ""
        rule = classify_rule(desc_cache[mid], r["question"], spot, r["_strike"])
        p = digital_prob(spot, r["_strike"], sigma, r["_years"]) if rule == "digital" \
            else touch_prob(spot, r["_strike"], sigma, r["_years"], rule == "up_touch")
        if p is None:
            continue
        currency = r["_sym"].replace("USDT", "")
        iv = dvol_at(currency, entry_ts) if currency in ("BTC", "ETH") else None
        p_iv = None
        if iv:
            p_iv = digital_prob(spot, r["_strike"], iv, r["_years"]) if rule == "digital" \
                else touch_prob(spot, r["_strike"], iv, r["_years"], rule == "up_touch")
        priced.append({**r, "_spot": spot, "_sigma": sigma, "_bsm": p, "_iv": iv or 0.0,
                       "_bsm_iv": p_iv, "_rule": rule})

    if len(priced) < 15:
        print(f"only {len(priced)} priced markets; aborting")
        return

    ys = [1 if r["outcome"] == "yes" else 0 for r in priced]
    price = [r["entry_price"] for r in priced]
    bsm = [r["_bsm"] for r in priced]
    print(f"priced {len(priced)} markets")
    print(f"Brier  price={brier(price, ys):.4f}  bsm-realised-vol={brier(bsm, ys):.4f}")

    with_iv = [r for r in priced if r["_bsm_iv"] is not None]
    if len(with_iv) >= 15:
        ys_iv = [1 if r["outcome"] == "yes" else 0 for r in with_iv]
        pr_iv = [r["entry_price"] for r in with_iv]
        re_iv = [r["_bsm"] for r in with_iv]
        iv_iv = [r["_bsm_iv"] for r in with_iv]
        print(f"\nDVOL subset n={len(with_iv)}")
        print(f"  Brier price={brier(pr_iv, ys_iv):.4f}  realised={brier(re_iv, ys_iv):.4f}  "
              f"implied={brier(iv_iv, ys_iv):.4f}")
        for label, arr in (("realised", re_iv), ("implied", iv_iv)):
            d = [(a - y) ** 2 - (p - y) ** 2 for a, p, y in zip(arr, pr_iv, ys_iv)]
            print(f"  delta {label:8s} vs price = {st.mean(d):+.4f}")
        for tenor, lo, hi in (("<=14d", 0, 14), (">14d", 14, 1e9)):
            sel = [i for i, r in enumerate(with_iv) if lo <= r["_years"] * 365 < hi]
            if len(sel) < 8:
                continue
            ys2 = [ys_iv[i] for i in sel]
            print(f"  tenor {tenor:5s} n={len(sel):3d} price={brier([pr_iv[i] for i in sel], ys2):.4f} "
                  f"implied={brier([iv_iv[i] for i in sel], ys2):.4f}")

    for r in priced:
        iv = f"{r['_bsm_iv']:.3f}" if r["_bsm_iv"] is not None else "  -  "
        print(f"  {r['timestamp'][:10]} {r['_sym']:8s} K={r['_strike']:>10,.2f} "
              f"S0={r['_spot']:>10,.0f} rv={r['_sigma']:.2f} iv={r['_iv']:.2f} T={r['_years']*365:5.1f}d "
              f"{r['_rule']:10s} bsm={r['_bsm']:.3f} ivp={iv} price={r['entry_price']:.3f} out={r['outcome']}")

    diffs = [(b - y) ** 2 - (p - y) ** 2 for b, p, y in zip(bsm, price, ys)]
    print(f"mean brier delta (negative = bsm better) = {st.mean(diffs):+.4f}")

    json.dump({"n": len(priced), "brier_price": brier(price, ys), "brier_bsm": brier(bsm, ys),
               "rows": [{k: v for k, v in r.items() if k.startswith("_") or k in
                         ("market_id", "question", "timestamp", "entry_price", "outcome")} for r in priced]},
              open(args.out, "w", encoding="utf-8"), indent=1, default=str)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
