"""
Full pipeline demo -- exercises every integrated tool on live Polymarket data
without placing real orders. Shows transparent ranking with all signals.
"""

import json
import time
import random
import math
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

from src.data.polymarket_client import PolymarketClient
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger("demo")

try:
    from src.agents.sentiment_agent import SentimentAgent
    SENTIMENT_OK = True
except Exception:
    SENTIMENT_OK = False

try:
    from src.ml.timesfm_predictor import TimesFMPredictor
    TIMESFM_OK = True
except Exception:
    TIMESFM_OK = False

try:
    from src.ml.market_predictor import MarketPredictor
    ML_OK = True
except Exception:
    ML_OK = False

try:
    from src.trading.signal_filter import score_markets, filter_markets
    FILTER_OK = True
except Exception:
    FILTER_OK = False

try:
    from src.trading.strategies import TimesFMStrategy, STRATEGIES
    STRATEGIES_OK = True
except Exception:
    STRATEGIES_OK = False


def generate_trending_history(current_price, length=64, trend_strength=0.3):
    """Generate price history with a realistic trend for TimesFM."""
    base_noise = 0.02  # 2% noise
    direction = 1 if random.random() > 0.4 else -1  # 60% chance uptrend
    history = []
    p = current_price * (1 - direction * trend_strength * 0.15)  # start below/above
    for _ in range(length):
        drift = direction * trend_strength * p * 0.005
        noise = p * base_noise * (random.random() - 0.5) * 2
        p = max(p + drift + noise, 0.001)
        history.append(p)
    return history


def simulate_trade(opportunity, ml_prob):
    """Simulate trade result based on ML probability."""
    price = opportunity["price"]
    bet = config.STARTING_BALANCE * config.MAX_POSITION_PCT
    fee = 0.07

    won = random.random() < ml_prob
    if won:
        profit = bet * ((1 / price - 1) * (1 - fee))
    else:
        profit = -bet

    return {"won": won, "profit": profit, "bet": bet, "roi_pct": (profit / bet) * 100}


def main():
    print("=" * 72)
    print("  POLYMARKET TRADING SYSTEM - FULL PIPELINE DEMO")
    print("  Mode: PAPER (no real orders)")
    print(f"  Balance: ${config.STARTING_BALANCE:.2f}")
    print(f"  Conservative thresholds: price=[{config.PRICE_MIN}-{config.PRICE_MAX}], "
          f"edge>={config.MIN_EDGE}, conf>={config.MIN_CONFIDENCE}, vol>={config.MIN_VOLUME}")
    print("=" * 72)

    # ---- Component status ----
    print("\n[INIT] Components:")
    print(f"  OK SentimentAgent" if SENTIMENT_OK else "  -- SentimentAgent")
    print(f"  OK TimesFMPredictor" if TIMESFM_OK else "  -- TimesFMPredictor")
    print(f"  OK MarketPredictor (ML)" if ML_OK else "  -- MarketPredictor (ML)")
    print(f"  OK SignalFilter" if FILTER_OK else "  -- SignalFilter")
    print(f"  OK Strategies (incl. TimesFMStrategy)" if STRATEGIES_OK else "  -- Strategies")

    # ---- 1. Fetch live markets ----
    print("\n[1/6] FETCHING LIVE MARKETS...")
    client = PolymarketClient()
    markets = client.get_markets(limit=50)
    print(f"  Received {len(markets)} from Gamma API ({client.base_url})")

    if not markets:
        print("  No markets returned. Exiting.")
        return

    # ---- 2. Sentiment analysis ----
    print("\n[2/6] SENTIMENT ANALYSIS...")
    sa = SentimentAgent() if SENTIMENT_OK else None
    enriched = []
    for m in markets:
        question = m.get("question", "")
        prices_raw = m.get("outcomePrices", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            price = float(prices[0]) if prices else 0.5
        except Exception:
            price = 0.5
        volume = float(m.get("volume", 0) or 0)

        if sa:
            try:
                s = sa.analyze_sentiment(question)
                score = s.get("score", 0.5)
                conf = min(max(score * 100, 0), 100)
            except Exception:
                score, conf = 0.5, 50
        else:
            score, conf = 0.5, 50

        enriched.append({
            "market_id": m.get("id", ""),
            "question": question,
            "price": price,
            "volume": volume,
            "sentiment": score,
            "confidence": conf,
        })
    print(f"  Analyzed {len(enriched)} markets")

    # ---- 3. TimesFM forecasts ----
    print("\n[3/6] TIMESFM FORECASTS...")
    if TIMESFM_OK:
        try:
            tfm = TimesFMPredictor()
            for item in enriched:
                history = generate_trending_history(item["price"])
                try:
                    signal = tfm.get_trend_signal(history, horizon=8)
                    item["timesfm_direction"] = signal.get("direction", 0)
                    item["timesfm_confidence"] = signal.get("confidence", 0.0)
                    item["timesfm_forecast_mean"] = signal.get("forecast_mean", item["price"])
                except Exception:
                    item["timesfm_direction"] = 0
                    item["timesfm_confidence"] = 0.0
        except Exception as e:
            print(f"  TimesFM init error: {e}")
            for item in enriched:
                item["timesfm_direction"] = 0
                item["timesfm_confidence"] = 0.0
    else:
        for item in enriched:
            item["timesfm_direction"] = 0
            item["timesfm_confidence"] = 0.0

    non_neutral = sum(1 for x in enriched if x.get("timesfm_direction") != 0)
    print(f"  TimesFM directional signals: {non_neutral} / {len(enriched)} markets")

    # ---- 4. ML probability predictions ----
    print("\n[4/6] ML MODEL PREDICTIONS...")
    ml_model = None
    if ML_OK:
        try:
            ml_model = MarketPredictor()
            if not ml_model.load_model():
                print("  No trained model. Training...")
                from src.ml.market_predictor import train_and_save_model
                train_and_save_model()
                ml_model.load_model()
        except Exception as e:
            print(f"  ML model error: {e}")

    for item in enriched:
        if ml_model and ml_model.is_trained:
            try:
                is_crypto = any(
                    kw in item["question"].lower()
                    for kw in ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth"]
                )
                edge = item["sentiment"] - item["price"]
                ml_prob = ml_model.predict_win_probability(
                    price=item["price"],
                    volume=item["volume"],
                    edge=edge,
                    confidence=item["confidence"],
                    is_crypto=is_crypto,
                )
            except Exception:
                ml_prob = 0.5
        else:
            edge = item["sentiment"] - item["price"]
            ml_prob = max(0.05, min(0.95, 0.5 + edge * 0.5))

        item["ml_prob"] = ml_prob
        item["edge"] = item["sentiment"] - item["price"]
    print(f"  ML predictions: {len(enriched)} markets")

    # ---- 5. Ranking table (all markets sorted by ml_prob) ----
    print("\n[5/6] RANKING (sorted by ML probability)")
    enriched.sort(key=lambda x: x["ml_prob"], reverse=True)

    # Filter checks
    def passes_filters(m):
        reasons = []
        if not (config.PRICE_MIN <= m["price"] <= config.PRICE_MAX):
            reasons.append(f"price({m['price']:.3f})")
        if m["volume"] < config.MIN_VOLUME:
            reasons.append(f"vol({m['volume']:.0f})")
        if m["edge"] < config.MIN_EDGE:
            reasons.append(f"edge({m['edge']:.1%})")
        if m["confidence"] < config.MIN_CONFIDENCE:
            reasons.append(f"conf({m['confidence']:.0f}%)")
        if m["ml_prob"] < 0.5:
            reasons.append(f"ml({m['ml_prob']:.0%})")
        return len(reasons) == 0, reasons

    header = f"  {'#':>2} {'Price':>6} {'Vol':>9} {'Edge':>5} {'Conf':>4} {'ML%':>5} {'TFM':>8}  {'Question'}"
    sep = f"  {'-'*2} {'-'*6} {'-'*9} {'-'*5} {'-'*4} {'-'*5} {'-'*8}  {'-'*40}"
    print(header)
    print(sep)
    for i, c in enumerate(enriched):
        tfm_dir = {1: "bull", -1: "bear", 0: "neut"}.get(c['timesfm_direction'], "?")
        tfm_str = f"{tfm_dir}({c['timesfm_confidence']:.0%})"
        q = c["question"][:40]
        ok, reasons = passes_filters(c)
        print(f"  {i+1:>2} {c['price']:>6.3f} {c['volume']:>9.0f} "
              f"{c['edge']:>5.1%} {c['confidence']:>3.0f}% "
              f"{c['ml_prob']:>4.0%} {tfm_str:>8}  {q}")
    print(sep)
    candidates = [c for c in enriched if passes_filters(c)[0]]
    print(f"\n  Markets passing ALL filters: {len(candidates)} / {len(enriched)}")
    if not candidates:
        print("  (thresholds are conservative - relax in .env to trade more)")

    # ---- 6. Simulate top trades ----
    print("\n[6/6] SIMULATED TRADES (paper)")
    balance = config.STARTING_BALANCE
    trades = []
    take = min(5, len(candidates) if candidates else 5)

    for i in range(take):
        if candidates:
            c = candidates[i]
        else:
            c = enriched[i]  # show even if below thresholds, so user sees the pipeline

        result = simulate_trade(c, c["ml_prob"])
        balance += result["profit"]
        trades.append(result)

        outcome = "WIN" if result["won"] else "LOSS"
        print(f"\n  Trade #{i+1}: {outcome}")
        print(f"    Market: {c['question'][:55]}")
        print(f"    Price: ${c['price']:.3f} | Edge: {c['edge']:+.1%} | "
              f"Conf: {c['confidence']:.0f}%")
        tfm_dir = {1: "bull", -1: "bear", 0: "neut"}.get(c['timesfm_direction'], "?")
        print(f"    ML prob: {c['ml_prob']:.1%} | "
              f"TimesFM: {tfm_dir} ({c['timesfm_confidence']:.0%})")
        print(f"    Sentiment: {c['sentiment']:.0%} | "
              f"Volume: {c['volume']:,.0f}")
        print(f"    Bet: ${result['bet']:.2f} | P&L: ${result['profit']:+.2f} "
              f"({result['roi_pct']:+.1f}%)")
        print(f"    Balance: ${balance:.2f}")
        time.sleep(0.2)

    # ---- Summary ----
    print("\n" + "=" * 72)
    print("  DEMO COMPLETE - SUMMARY")
    print("=" * 72)
    total = len(trades)
    wins = sum(1 for t in trades if t["won"])
    profit = balance - config.STARTING_BALANCE
    win_rate = (wins / total * 100) if total > 0 else 0
    print(f"  Paper trades:     {total}")
    print(f"  Wins: {wins} / Losses: {total-wins} / Win Rate: {win_rate:.1f}%")
    print(f"  P&L: ${profit:+.2f} ({profit/config.STARTING_BALANCE*100:+.1f}%)")
    print(f"  Final balance:    ${balance:.2f}")
    print(f"  TimesFM signals:  {non_neutral} / {len(enriched)} markets")
    print(f"  ML model loaded:  {ml_model is not None and ml_model.is_trained}")
    print(f"  All trades are PAPER - no real orders placed.")
    print("=" * 72)


if __name__ == "__main__":
    main()
