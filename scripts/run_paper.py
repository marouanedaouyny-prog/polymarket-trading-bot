#!/usr/bin/env python3
"""
MiroFish-assisted paper trading script for Polymarket.

This script is paper-only. It uses live market data plus an optional MiroFish
signal to prioritize markets and size positions.
"""

import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from math import log1p
from pathlib import Path

from dotenv import load_dotenv

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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.data.polymarket_client import PolymarketClient
from src.data.crypto_section import fetch_crypto_section_markets
from src.utils.config import config as app_config

try:
    from src.prediction import MiroFishIntegrator
    MIROFISH_AVAILABLE = True
except ImportError:
    MIROFISH_AVAILABLE = False


FEE_RATE = float(os.getenv("PAPER_FEE_RATE", "0.07"))
STARTING_BALANCE = float(
    os.getenv("PAPER_STARTING_BALANCE", os.getenv("STARTING_BALANCE", "10"))
)
MAX_TRADES = int(os.getenv("PAPER_MAX_TRADES", "3"))
ANALYSIS_LIMIT = int(os.getenv("PAPER_ANALYSIS_LIMIT", "5"))
MIN_SIGNAL_EDGE = float(os.getenv("PAPER_MIN_SIGNAL_EDGE", "0.03"))
MIN_SIGNAL_CONFIDENCE = float(os.getenv("PAPER_MIN_SIGNAL_CONFIDENCE", "60"))
MIN_VOLUME = float(
    os.getenv("PAPER_MIN_VOLUME", str(getattr(app_config, "MIN_VOLUME", 15000)))
)
MAX_POSITION_PCT = float(
    os.getenv(
        "PAPER_MAX_POSITION_PCT",
        str(getattr(app_config, "MAX_POSITION_PCT", 0.15)),
    )
)
PRICE_MIN = float(
    os.getenv("PAPER_PRICE_MIN", str(getattr(app_config, "PRICE_MIN", 0.01)))
)
PRICE_MAX = float(
    os.getenv("PAPER_PRICE_MAX", str(getattr(app_config, "PRICE_MAX", 0.35)))
)


def parse_number(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("current", "value", "amount", "total", "size"):
            parsed = parse_number(value.get(key), default=0.0)
            if parsed:
                return parsed
        return default
    if isinstance(value, str):
        text = value.strip().replace("$", "").replace(",", "").replace("%", "").upper()
        multiplier = 1.0
        if text.endswith("K"):
            multiplier = 1_000.0
            text = text[:-1]
        elif text.endswith("M"):
            multiplier = 1_000_000.0
            text = text[:-1]
        elif text.endswith("B"):
            multiplier = 1_000_000_000.0
            text = text[:-1]
        try:
            return float(text) * multiplier
        except ValueError:
            return default
    return default


def normalize_sequence(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            return parts or [text]
        return [text]
    return []


def normalize_label(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def csv_env(name, default):
    raw = os.getenv(name, default)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def keyword_hit(text, keywords):
    for keyword in keywords:
        if re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text):
            return True
    return False


def market_text(market):
    parts = []
    for key in ("question", "category", "tags", "slug", "description"):
        value = market.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def parse_end_date(market):
    raw = market.get("endDate") or market.get("end_date") or market.get("endDateIso")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def days_to_end(market):
    end_date = parse_end_date(market)
    if not end_date:
        return None
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    return (end_date - datetime.now(timezone.utc)).total_seconds() / 86400.0


def is_yes_label(label):
    return normalize_label(label) in {"yes", "y", "true"}


def is_no_label(label):
    return normalize_label(label) in {"no", "n", "false"}


def market_id(market):
    return (
        market.get("condition_id")
        or market.get("conditionId")
        or market.get("id", "")
    )


def extract_odds(market):
    outcomes = normalize_sequence(market.get("outcomes") or [])
    prices = normalize_sequence(market.get("outcomePrices") or [])
    odds = {}
    for outcome, price in zip(outcomes, prices):
        parsed = parse_number(price)
        if parsed > 0:
            odds[str(outcome)] = parsed

    tokens = market.get("tokens") or []
    if tokens:
        token_odds = {}
        for token in tokens:
            outcome = token.get("outcome") or token.get("name")
            price = parse_number(token.get("price"))
            if outcome is not None and price > 0:
                token_odds[str(outcome)] = price
        if token_odds:
            return token_odds

    return odds


def extract_binary_prices(market):
    odds = extract_odds(market)
    if not odds:
        return None

    yes_key = next((key for key in odds if is_yes_label(key)), None)
    no_key = next((key for key in odds if is_no_label(key)), None)
    if yes_key is None or no_key is None:
        if len(odds) != 2:
            return None
        first_key, second_key = list(odds.keys())[:2]
        return {
            "yes": odds[first_key],
            "no": odds[second_key],
            "raw": odds,
            "yes_label": str(first_key).strip().lower(),
            "no_label": str(second_key).strip().lower(),
            "generic_binary": True,
        }

    return {
        "yes": odds[yes_key],
        "no": odds[no_key],
        "raw": odds,
        "yes_label": str(yes_key).strip().lower(),
        "no_label": str(no_key).strip().lower(),
        "generic_binary": False,
    }


def extract_volume(market):
    for key in ("volume", "liquidity", "dailyVolume", "marketVolume"):
        value = market.get(key)
        parsed = parse_number(value)
        if parsed > 0:
            return parsed
    return 0.0


class PaperTrader:
    def __init__(self):
        self.client = PolymarketClient()
        self.starting_balance = STARTING_BALANCE
        self.balance = STARTING_BALANCE
        self.trade_log = []
        self.max_trades = MAX_TRADES
        self.analysis_limit = ANALYSIS_LIMIT
        self.min_signal_edge = MIN_SIGNAL_EDGE
        self.min_signal_confidence = MIN_SIGNAL_CONFIDENCE
        self.min_volume = MIN_VOLUME
        self.max_position_pct = MAX_POSITION_PCT
        self.price_min = PRICE_MIN
        self.price_max = PRICE_MAX
        self.fee_rate = FEE_RATE
        self.crypto_only = env_bool("PAPER_CRYPTO_ONLY", False)
        self.market_keywords = csv_env(
            "PAPER_MARKET_KEYWORDS",
            "bitcoin,btc,ethereum,eth,megaeth,solana,sol,xrp,crypto,dogecoin,doge",
        )
        self.exclude_keywords = csv_env(
            "PAPER_EXCLUDE_KEYWORDS",
            "fifa,world cup,soccer,football,nba,nfl,mlb,nhl,election,president",
        )
        self.max_days_to_end = float(os.getenv("PAPER_MAX_DAYS_TO_END", "0"))
        self.market_source = os.getenv("POLYMARKET_MARKET_SOURCE", "gamma").strip().lower()
        self.crypto_locale = os.getenv("POLYMARKET_CRYPTO_LOCALE", "fr").strip()
        self.mirofish = self._init_mirofish()

    def _init_mirofish(self):
        if not MIROFISH_AVAILABLE:
            return None
        if not getattr(app_config, "MIROFISH_ENABLED", True):
            return None
        try:
            integrator = MiroFishIntegrator(
                base_url=getattr(app_config, "MIROFISH_URL", "http://localhost:5001"),
                use_cache=getattr(app_config, "MIROFISH_USE_CACHE", True),
                cache_ttl=getattr(app_config, "MIROFISH_CACHE_TTL", 3600),
                simulation_rounds=getattr(app_config, "MIROFISH_SIMULATION_ROUNDS", 50),
                agent_count=getattr(app_config, "MIROFISH_AGENT_COUNT", 50),
                min_call_interval_seconds=0,
            )
            if integrator.available:
                return integrator
        except Exception as exc:
            print(f"[MiroFish] Init error: {exc}")
        return None

    def fetch_candidates(self, limit=50):
        if self.market_source == "crypto_page":
            markets = fetch_crypto_section_markets(locale=self.crypto_locale, limit=limit)
        else:
            params = {"closed": "false", "archived": "false"}
            if self.max_days_to_end > 0:
                now = datetime.now(timezone.utc)
                max_end = now.timestamp() + (self.max_days_to_end * 86400.0)
                params["end_date_min"] = now.isoformat()
                params["end_date_max"] = datetime.fromtimestamp(max_end, tz=timezone.utc).isoformat()

            markets = self.client.get_markets(limit=limit, params=params)
        scored = []

        for market in markets:
            if market.get("closed", False):
                continue
            if not self.market_matches_filters(market):
                continue

            prices = extract_binary_prices(market)
            if not prices:
                continue

            volume = extract_volume(market)
            cheapest_side = min(prices["yes"], prices["no"])
            if cheapest_side < self.price_min or cheapest_side > self.price_max:
                continue
            if volume and volume < self.min_volume:
                continue

            volume_score = min(log1p(max(volume, 1.0)) / 12.0, 1.0)
            price_score = 1.0 - cheapest_side
            score = (price_score * 0.7) + (volume_score * 0.3)
            scored.append((market, prices, volume, score))

        return sorted(scored, key=lambda item: item[3], reverse=True)

    def market_matches_filters(self, market):
        text = market_text(market)
        if keyword_hit(text, self.exclude_keywords):
            return False
        if self.crypto_only and not keyword_hit(text, self.market_keywords):
            return False
        if self.max_days_to_end > 0:
            remaining_days = days_to_end(market)
            if remaining_days is None or remaining_days > self.max_days_to_end:
                return False
        return True

    def build_opportunity(self, market, prices, volume, fallback_score):
        question = market.get("question", "")
        signal = None
        signal_source = "heuristic"

        if self.mirofish:
            try:
                signal = self.mirofish.get_market_intelligence(question, market)
            except Exception as exc:
                print(f"[MiroFish] Analysis failed for {market_id(market)}: {exc}")
                signal = None

        if signal and signal.get("consensus_yes_pct") is not None:
            yes_prob = max(
                0.01,
                min(0.99, float(signal.get("consensus_yes_pct", 50)) / 100.0),
            )
            confidence = float(signal.get("confidence", 50))
            confidence_boost = float(signal.get("confidence_boost", 0))
            yes_edge = yes_prob - prices["yes"]
            no_prob = 1.0 - yes_prob
            no_edge = no_prob - prices["no"]

            if yes_edge >= no_edge:
                side = "yes"
                price = prices["yes"]
                predicted_prob = yes_prob
                edge = yes_edge
            else:
                side = "no"
                price = prices["no"]
                predicted_prob = no_prob
                edge = no_edge

            if edge < self.min_signal_edge or confidence < self.min_signal_confidence:
                return None

            score = edge * (confidence / 100.0) * (1.0 + confidence_boost / 100.0)
            signal_source = "mirofish"
        else:
            # Fallback: keep the previous paper behavior, but only on clear
            # high-probability markets.
            odds = prices["raw"]
            best_outcome = max(odds, key=odds.get)
            price = odds[best_outcome]
            if price < 0.7:
                return None

            side = str(best_outcome).strip().lower()
            predicted_prob = min(0.99, max(0.55, price))
            edge = max(0.0, price - 0.5)
            confidence = price * 100.0
            confidence_boost = 0.0
            score = fallback_score

        bet_amount = self.size_position(edge, confidence, confidence_boost)
        if bet_amount <= 0:
            return None

        return {
            "market": market,
            "market_id": market_id(market),
            "question": question,
            "outcome_chosen": side,
            "price": price,
            "predicted_prob": predicted_prob,
            "edge": edge,
            "confidence": confidence,
            "confidence_boost": confidence_boost,
            "score": score,
            "amount": bet_amount,
            "volume": volume,
            "prices": prices["raw"],
            "signal": signal,
            "signal_source": signal_source,
        }

    def size_position(self, edge, confidence, confidence_boost):
        risk_budget = self.balance * self.max_position_pct
        edge_multiplier = min(max(edge * 6.0, 0.25), 1.0)
        confidence_multiplier = max(min(confidence / 100.0, 1.0), 0.5)
        boost_multiplier = 1.0 + max(confidence_boost, 0.0) / 100.0
        amount = risk_budget * edge_multiplier * confidence_multiplier * boost_multiplier
        amount = max(1.0, min(self.balance, amount))
        return round(amount, 2)

    def execute_trade(self, opportunity):
        price = max(opportunity["price"], 0.01)
        bet_amount = opportunity["amount"]
        predicted_prob = opportunity["predicted_prob"]
        won = random.random() < predicted_prob

        if won:
            gross_profit = bet_amount * (1 / price - 1)
            profit = round(gross_profit * (1 - self.fee_rate), 2)
        else:
            profit = round(-bet_amount, 2)

        self.balance = round(self.balance + profit, 2)

        trade_log = {
            "timestamp": datetime.now().isoformat(),
            "market_id": opportunity["market_id"],
            "question": opportunity["question"],
            "outcome_chosen": opportunity["outcome_chosen"],
            "amount": bet_amount,
            "price": round(price, 4),
            "predicted_prob": round(predicted_prob, 4),
            "edge": round(opportunity["edge"], 4),
            "confidence": round(opportunity["confidence"], 2),
            "confidence_boost": round(opportunity["confidence_boost"], 2),
            "score": round(opportunity["score"], 4),
            "volume": round(opportunity["volume"], 2),
            "signal_source": opportunity["signal_source"],
            "signal": opportunity["signal"],
            "won": won,
            "profit": profit,
            "balance": self.balance,
        }
        self.trade_log.append(trade_log)
        return trade_log

    def save_logs(self):
        with open("paper_trades.json", "w", encoding="utf-8") as handle:
            json.dump(self.trade_log, handle, indent=2, ensure_ascii=False)

    def run(self):
        print("MiroFish-Assisted Polymarket Paper Trading")
        print(f"Starting Balance: ${self.balance:.2f}")
        if self.mirofish:
            print("MiroFish: enabled")
        else:
            print("MiroFish: fallback mode")
            print(
                "   backend not reachable at "
                f"{getattr(app_config, 'MIROFISH_URL', 'http://localhost:5001')}"
            )
        print("-" * 50)

        markets = self.fetch_candidates(limit=50)
        print(f"Found {len(markets)} candidate markets")

        opportunities = []
        for index, (market, prices, volume, fallback_score) in enumerate(
            markets[:self.analysis_limit], start=1
        ):
            opportunity = self.build_opportunity(market, prices, volume, fallback_score)
            if not opportunity:
                continue
            opportunities.append(opportunity)
            print(
                f"Candidate {index}: {opportunity['question'][:60]}"
                f"{'...' if len(opportunity['question']) > 60 else ''}"
            )
            print(
                f"   Side: {opportunity['outcome_chosen'].upper()} @ "
                f"{opportunity['price']:.4f} | Edge: {opportunity['edge']:.3f} "
                f"| Confidence: {opportunity['confidence']:.1f}"
            )
            remaining_days = days_to_end(opportunity["market"])
            if remaining_days is not None:
                print(f"   Days to end: {remaining_days:.1f}")

        if not opportunities:
            print("No positive-edge opportunities found.")
            self.save_logs()
            return

        opportunities.sort(key=lambda item: item["score"], reverse=True)

        for index, opportunity in enumerate(opportunities[: self.max_trades], start=1):
            trade = self.execute_trade(opportunity)
            print(f"Trade {index}: {trade['question'][:50]}...")
            print(
                f"   Bet: ${trade['amount']:.2f} on '{trade['outcome_chosen']}' "
                f"(predicted win: {trade['predicted_prob'] * 100:.1f}%)"
            )
            print(
                f"   Result: {'WIN' if trade['won'] else 'LOSS'} | "
                f"PnL: {trade['profit']:+.2f} | Balance: ${trade['balance']:.2f}"
            )
            print("-" * 50)

        self.save_logs()
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Total Profit: {self.balance - self.starting_balance:+.2f}")


def main():
    trader = PaperTrader()
    trader.run()


if __name__ == "__main__":
    main()
