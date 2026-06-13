"""
One-shot guarded live smoke test.

Default mode is dry-run. A real order requires both:
  --submit --i-understand-loss
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def clear_proxy_env():
    for proxy_var in (
        "ALL_PROXY",
        "all_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
        "GIT_HTTP_PROXY",
        "GIT_HTTPS_PROXY",
    ):
        os.environ.pop(proxy_var, None)


clear_proxy_env()
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from scripts.run_paper import PaperTrader
from src.trading.live_trading import TradingSession


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return float(default)


def env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def csv_env(name, default):
    raw = os.getenv(name, default)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def market_text(market):
    parts = []
    for key in ("question", "category", "tags", "slug", "description"):
        value = market.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def keyword_hit(text, keywords):
    for keyword in keywords:
        if re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text):
            return True
    return False


def parse_end_date(market):
    raw = market.get("endDate") or market.get("end_date") or market.get("endDateIso")
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def days_to_end(market):
    end_date = parse_end_date(market)
    if not end_date:
        return None
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    return (end_date - datetime.now(timezone.utc)).total_seconds() / 86400.0


def market_matches_filters(market, crypto_only=True):
    text = market_text(market)
    include_keywords = csv_env(
        "LIVE_SMOKE_MARKET_KEYWORDS",
        "bitcoin,btc,ethereum,eth,megaeth,solana,sol,xrp,crypto,dogecoin,doge",
    )
    exclude_keywords = csv_env(
        "LIVE_SMOKE_EXCLUDE_KEYWORDS",
        "fifa,world cup,soccer,football,nba,nfl,mlb,nhl,election,president",
    )

    if keyword_hit(text, exclude_keywords):
        return False
    if crypto_only and not keyword_hit(text, include_keywords):
        return False

    max_days = env_float("LIVE_SMOKE_MAX_DAYS_TO_END", 0)
    if max_days > 0:
        remaining_days = days_to_end(market)
        if remaining_days is None or remaining_days > max_days:
            return False

    return True


def pick_opportunity(crypto_only=True):
    trader = PaperTrader()
    candidates = trader.fetch_candidates(limit=int(os.getenv("LIVE_SMOKE_MARKET_LIMIT", "50")))
    opportunities = []

    for market, prices, volume, fallback_score in candidates[: int(os.getenv("LIVE_SMOKE_ANALYSIS_LIMIT", "5"))]:
        if not market_matches_filters(market, crypto_only=crypto_only):
            continue
        opportunity = trader.build_opportunity(market, prices, volume, fallback_score)
        if opportunity:
            opportunities.append(opportunity)

    if not opportunities:
        return None

    opportunities.sort(key=lambda item: item["score"], reverse=True)
    return opportunities[0]


def main():
    parser = argparse.ArgumentParser(description="Guarded $2 Polymarket live smoke test")
    parser.add_argument("--submit", action="store_true", help="Submit the real live order")
    parser.add_argument(
        "--i-understand-loss",
        action="store_true",
        help="Required with --submit. Confirms the order can lose the full amount.",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=env_float("LIVE_TEST_ORDER_AMOUNT", 2.0),
        help="Order amount. Capped by MAX_ORDER_SIZE.",
    )
    parser.add_argument(
        "--all-markets",
        action="store_true",
        help="Disable the default crypto-only market filter.",
    )
    args = parser.parse_args()

    max_order_size = env_float("MAX_ORDER_SIZE", 2.0)
    amount = round(min(args.amount, max_order_size), 2)

    if amount <= 0:
        raise SystemExit("Amount must be positive.")

    if amount > 2:
        raise SystemExit("Refusing smoke test above $2.")

    if args.submit and not args.i_understand_loss:
        raise SystemExit("Add --i-understand-loss to submit a real order.")

    if not args.submit:
        os.environ["POLYMARKET_ALLOW_REAL_ORDERS"] = "false"

    opportunity = pick_opportunity(
        crypto_only=env_bool("LIVE_SMOKE_CRYPTO_ONLY", True) and not args.all_markets
    )
    if not opportunity:
        raise SystemExit("No live smoke-test opportunity found for the current filters.")

    market = opportunity["market"]
    side = opportunity["outcome_chosen"]
    price = float(opportunity["price"])
    edge = float(opportunity["edge"])
    confidence = float(opportunity["confidence"])
    predicted_prob = float(opportunity["predicted_prob"])

    session = TradingSession(
        starting_balance=amount,
        mode="live",
        enable_mirofish=False,
    )

    preview = session.execute_trade(
        market,
        price,
        edge,
        confidence,
        predicted_prob,
        signal={
            "source": opportunity["signal_source"],
            "selected_side": side,
            "selected_price": price,
            "predicted_prob": predicted_prob,
            "edge": edge,
            "confidence": confidence,
            "score": min(max(float(opportunity["score"]), 0.0), 0.25),
            "consensus_yes_pct": None,
        },
    )

    if not args.submit:
        print("DRY RUN ONLY - no real order was submitted")

    print("=" * 60)
    print("LIVE SMOKE TEST PREVIEW" if not args.submit else "LIVE SMOKE TEST RESULT")
    print("=" * 60)
    print(f"Market: {market.get('question', '')[:100]}")
    print(f"Outcome: {preview['selected_outcome'].upper()}")
    print(f"Token ID: {preview.get('token_id')}")
    print(f"Amount: ${preview['bet']:.2f}")
    print(f"Reference price: {preview['price']:.4f}")
    remaining_days = days_to_end(market)
    if remaining_days is not None:
        print(f"Days to market end: {remaining_days:.1f}")
    print(f"Signal source: {preview['signal_source']}")
    print(f"Order status: {preview['order_status']}")
    if preview.get("error"):
        print(f"Error: {preview['error']}")

    if not args.submit:
        print("=" * 60)
        print("Before submitting, set POLYMARKET_ALLOW_REAL_ORDERS=true in config/.env.")
        print("To submit this kind of $2 live test yourself, run:")
        print(
            ".\\.venv312\\Scripts\\python.exe .\\scripts\\tools\\live_smoke_trade.py "
            "--submit --i-understand-loss"
        )


if __name__ == "__main__":
    main()
