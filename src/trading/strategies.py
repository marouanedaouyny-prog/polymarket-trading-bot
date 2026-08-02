"""
Strategy Pattern for Polymarket Trading

Base class + 3 concrete strategies inspired by StockSharp/AlgoTrading patterns:
  1. MomentumStrategy   — RSI + MACD trend following (like 0009_MACD_Trend)
  2. MeanReversionStrategy — Bollinger Band reversion (like 0027_Bollinger_Reversion)
  3. VolumeSpikeStrategy — OBV + volume breakout (like 0046_Volume_Spike)

Each strategy receives a MarketSnapshot and returns a Signal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from src.trading.indicators import rsi, macd, bollinger_bands, obv, volume_spike, market_score


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class MarketSnapshot:
    """Input to every strategy — normalised market state."""
    market_id: str
    prices: list[float]          # closing price history, most-recent last
    volumes: list[float]         # volume history, same length as prices
    current_price: float
    days_left: int
    question: str = ""


@dataclass
class Signal:
    """Output from a strategy."""
    action: Action
    confidence: float            # 0.0 – 1.0
    reason: str
    market_id: str
    price: float
    metadata: dict = field(default_factory=dict)

    @property
    def is_tradeable(self) -> bool:
        return self.action != Action.HOLD and self.confidence >= 0.6


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseStrategy(ABC):
    """
    All strategies implement generate_signal().
    Concrete strategies are stateless; call them repeatedly on new snapshots.
    """

    name: str = "base"

    @abstractmethod
    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        ...

    def _hold(self, snapshot: MarketSnapshot, reason: str) -> Signal:
        return Signal(
            action=Action.HOLD,
            confidence=0.0,
            reason=reason,
            market_id=snapshot.market_id,
            price=snapshot.current_price,
        )


# ---------------------------------------------------------------------------
# Strategy 1 — Momentum (MACD + RSI)
# Inspired by AlgoTrading/0009_MACD_Trend and 0016_RSI_Divergence
# ---------------------------------------------------------------------------

class MomentumStrategy(BaseStrategy):
    """
    Enter when MACD histogram crosses positive AND RSI is not overbought.
    Exit when RSI > 70 or MACD histogram turns negative.

    Best for markets with clear price momentum (e.g. a candidate surging in polls).
    """

    name = "momentum"

    def __init__(self, rsi_overbought: float = 70.0, rsi_oversold: float = 30.0):
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        prices = snapshot.prices
        if len(prices) < 30:
            return self._hold(snapshot, "not enough history")

        r = rsi(prices)
        m = macd(prices)
        if r is None or m is None:
            return self._hold(snapshot, "indicator computation failed")

        hist = m["histogram"]
        meta = {"rsi": r, "macd_hist": hist}

        # Strong buy: MACD histogram > 0 + RSI not overbought + enough days
        if hist > 0 and r < self.rsi_overbought and snapshot.days_left >= 3:
            conf = min(0.5 + abs(hist) * 50 + (self.rsi_overbought - r) / 200, 0.95)
            return Signal(
                action=Action.BUY,
                confidence=round(conf, 3),
                reason=f"MACD bullish (hist={hist:.4f}), RSI={r:.1f}",
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata=meta,
            )

        # Sell signal: MACD histogram < 0 or RSI overbought
        if hist < 0 or r > self.rsi_overbought:
            conf = min(0.5 + abs(hist) * 50, 0.90)
            return Signal(
                action=Action.SELL,
                confidence=round(conf, 3),
                reason=f"MACD bearish or RSI overbought (hist={hist:.4f}, RSI={r:.1f})",
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata=meta,
            )

        return self._hold(snapshot, f"no clear momentum (hist={hist:.4f}, RSI={r:.1f})")


# ---------------------------------------------------------------------------
# Strategy 2 — Mean Reversion (Bollinger Bands)
# Inspired by AlgoTrading/0027_Bollinger_Reversion
# ---------------------------------------------------------------------------

class MeanReversionStrategy(BaseStrategy):
    """
    Buy when price drops below the lower Bollinger Band (oversold).
    Sell when price exceeds the upper band (overbought).

    Works well in range-bound markets (stable probability markets).
    Pairs nicely with a short days_left filter to avoid open-ended markets.
    """

    name = "mean_reversion"

    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        prices = snapshot.prices
        if len(prices) < self.period:
            return self._hold(snapshot, "not enough history for Bollinger Bands")

        bb = bollinger_bands(prices, self.period, self.num_std)
        if bb is None:
            return self._hold(snapshot, "Bollinger calculation failed")

        pct_b = bb["pct_b"]
        bw = bb["bandwidth"]
        meta = {"pct_b": pct_b, "bandwidth": bw, **bb}

        # Price below lower band → mean reversion buy
        if pct_b < 0:
            # Stronger signal if price is far below the band
            conf = min(0.55 + abs(pct_b) * 0.4, 0.92)
            return Signal(
                action=Action.BUY,
                confidence=round(conf, 3),
                reason=f"Price below lower BB (%B={pct_b:.2f})",
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata=meta,
            )

        # Price above upper band → mean reversion sell
        if pct_b > 1:
            conf = min(0.55 + (pct_b - 1) * 0.4, 0.92)
            return Signal(
                action=Action.SELL,
                confidence=round(conf, 3),
                reason=f"Price above upper BB (%B={pct_b:.2f})",
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata=meta,
            )

        return self._hold(snapshot, f"price within bands (%B={pct_b:.2f})")


# ---------------------------------------------------------------------------
# Strategy 3 — Volume Spike / OBV Breakout
# Inspired by AlgoTrading/0046_Volume_Spike and 0047_OBV_Breakout
# ---------------------------------------------------------------------------

class VolumeSpikeStrategy(BaseStrategy):
    """
    Detect abnormal volume relative to baseline — indicates an imminent
    resolution or news catalyst. Confirm direction with OBV slope.

    On Polymarket, a sudden volume spike near expiry often precedes a
    correct-side bet opportunity.
    """

    name = "volume_spike"

    def __init__(self, spike_threshold: float = 2.5, obv_lookback: int = 5):
        self.spike_threshold = spike_threshold
        self.obv_lookback = obv_lookback

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        prices = snapshot.prices
        volumes = snapshot.volumes

        if len(prices) < 22 or len(volumes) < 22:
            return self._hold(snapshot, "not enough history")

        spike = volume_spike(volumes, period=20, threshold=self.spike_threshold)
        if not spike:
            return self._hold(snapshot, "no volume spike detected")

        # Determine direction using OBV over the lookback window
        obv_recent = obv(prices[-self.obv_lookback:], volumes[-self.obv_lookback:])
        obv_prior = obv(prices[-self.obv_lookback * 2:-self.obv_lookback],
                        volumes[-self.obv_lookback * 2:-self.obv_lookback])

        if obv_recent is None or obv_prior is None:
            return self._hold(snapshot, "OBV computation failed")

        vol_ratio = volumes[-1] / (sum(volumes[-21:-1]) / 20)
        meta = {"vol_ratio": round(vol_ratio, 2), "obv_recent": obv_recent, "obv_prior": obv_prior}

        # OBV rising → volume driven by buyers → BUY
        if obv_recent > obv_prior:
            conf = min(0.55 + (vol_ratio - self.spike_threshold) * 0.1, 0.93)
            return Signal(
                action=Action.BUY,
                confidence=round(conf, 3),
                reason=f"Volume spike ({vol_ratio:.1f}x avg) with rising OBV",
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata=meta,
            )

        # OBV falling → volume driven by sellers → SELL
        conf = min(0.55 + (vol_ratio - self.spike_threshold) * 0.1, 0.93)
        return Signal(
            action=Action.SELL,
            confidence=round(conf, 3),
            reason=f"Volume spike ({vol_ratio:.1f}x avg) with falling OBV",
            market_id=snapshot.market_id,
            price=snapshot.current_price,
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# Composite: run all strategies, pick highest-confidence agreeing signal
# ---------------------------------------------------------------------------

class TimesFMStrategy(BaseStrategy):
    name = "timesfm"

    def __init__(self, horizon: int = 12, min_confidence: float = 0.55):
        self.horizon = horizon
        self.min_confidence = min_confidence

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        prices = snapshot.prices
        if len(prices) < 20:
            return self._hold(snapshot, "not enough history for TimesFM")

        from src.ml.timesfm_predictor import TimesFMPredictor
        predictor = TimesFMPredictor()
        signal = predictor.get_trend_signal(prices, horizon=self.horizon)

        if signal["confidence"] < self.min_confidence or signal["direction"] == 0:
            return self._hold(snapshot, signal.get("reason", "no clear trend"))

        action = Action.BUY if signal["direction"] > 0 else Action.SELL
        return Signal(
            action=action,
            confidence=round(signal["confidence"], 3),
            reason=f"TimesFM: {signal['reason']}",
            market_id=snapshot.market_id,
            price=snapshot.current_price,
            metadata={
                "forecast_end": signal.get("forecast_end"),
                "weighted_forecast": signal.get("weighted_forecast"),
                "uncertainty": signal.get("uncertainty", 0.0),
                "forecast_series": signal.get("forecast_series", []),
            },
        )


# ---------------------------------------------------------------------------
# Strategy 5 — News / LLM Sentiment Analysis
# ---------------------------------------------------------------------------

class NewsSentimentStrategy(BaseStrategy):
    """
    Analyzes market question text using keyword-based sentiment signals.
    Detects bullish/bearish patterns in prediction market questions.

    Trigger words for bullish: 'approve', 'pass', 'win', 'success', 'reach',
    'launch', 'positive', 'growth', 'break', 'succeed', 'majority'
    Trigger words for bearish: 'fail', 'reject', 'lose', 'decline', 'drop',
    'negative', 'crisis', 'ban', 'defeat', 'against', 'violate'

    Blended with LLM-based analysis when available.
    """

    name = "news_sentiment"

    def __init__(self, min_keyword_matches: int = 2,
                 llm_weight: float = 0.3,
                 nlp_model: str = None):
        self.min_keyword_matches = min_keyword_matches
        self.llm_weight = llm_weight
        self.nlp_model = nlp_model

        self.bullish_keywords = {
            'approve', 'pass', 'win', 'success', 'reach',
            'launch', 'positive', 'growth', 'break', 'succeed',
            'majority', 'higher', 'increase', 'surpass', 'achieve',
            'adopt', 'legalize', 'support', 'breakthrough',
        }
        self.bearish_keywords = {
            'fail', 'reject', 'lose', 'decline', 'drop',
            'negative', 'crisis', 'ban', 'defeat', 'against',
            'violate', 'lower', 'decrease', 'revoke', 'oppose',
            'sanction', 'restrict', 'crash', 'halt',
        }

    def _keyword_sentiment(self, question: str) -> tuple:
        """Score sentiment using keyword matching. Returns (score, count, details)."""
        q_lower = question.lower()
        bullish_matches = [kw for kw in self.bullish_keywords if kw in q_lower]
        bearish_matches = [kw for kw in self.bearish_keywords if kw in q_lower]

        total_matches = len(bullish_matches) + len(bearish_matches)
        if total_matches < self.min_keyword_matches:
            return 0.0, 0, {"reason": "insufficient keyword matches"}

        net = len(bullish_matches) - len(bearish_matches)
        score = net / max(total_matches, 1)
        # Normalize to [-1, 1] with diminishing returns on many matches
        score = max(-1.0, min(1.0, score * (1 - 1 / max(total_matches, 2))))

        return score, total_matches, {
            "bullish": bullish_matches,
            "bearish": bearish_matches,
        }

    def _llm_sentiment(self, question: str) -> float:
        """Try LLM-based sentiment analysis when available."""
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "Return a single float between -1.0 (very bearish) "
                        "and 1.0 (very bullish) for this prediction market question. "
                        "Return only the number, no other text."
                    )
                }, {
                    "role": "user",
                    "content": question
                }],
                max_tokens=10,
                temperature=0.1,
            )
            return float(resp.choices[0].message.content.strip())
        except Exception:
            return 0.0

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        question = snapshot.question or ""
        if not question:
            return self._hold(snapshot, "no question text")

        kw_score, kw_count, kw_details = self._keyword_sentiment(question)

        # Try LLM enrichment if available
        llm_score = self._llm_sentiment(question) if kw_count >= self.min_keyword_matches else 0.0

        # Blend scores
        if llm_score != 0.0:
            blended = kw_score * (1 - self.llm_weight) + llm_score * self.llm_weight
        else:
            blended = kw_score

        # Confidence based on match quality and LLM availability
        confidence_base = min(0.5 + abs(blended) * 0.3, 0.85)
        if llm_score != 0.0 and abs(llm_score) > 0.5:
            confidence_base = min(confidence_base + 0.10, 0.92)

        if blended > 0.2:
            return Signal(
                action=Action.BUY,
                confidence=round(confidence_base, 3),
                reason=(f"Bullish sentiment ({kw_count} keywords, "
                        f"kw={kw_score:.2f}, llm={llm_score:.2f})"),
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata={"kw_score": kw_score, "llm_score": llm_score, **kw_details},
            )
        elif blended < -0.2:
            return Signal(
                action=Action.SELL,
                confidence=round(confidence_base, 3),
                reason=(f"Bearish sentiment ({kw_count} keywords, "
                        f"kw={kw_score:.2f}, llm={llm_score:.2f})"),
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata={"kw_score": kw_score, "llm_score": llm_score, **kw_details},
            )

        return self._hold(snapshot, f"neutral sentiment (blended={blended:.2f})")


# ---------------------------------------------------------------------------
# Strategy 6 — On-Chain Activity Analysis
# ---------------------------------------------------------------------------

class OnChainAnalysisStrategy(BaseStrategy):
    """
    Analyzes on-chain signals for Polymarket prediction markets.
    Uses volume patterns, whale activity proxies, and market depth
    to detect informed trading.

    Key signals:
    - Volume concentration: large trades relative to average
    - Price-volume divergence: price moving without volume support
    - Bid-ask spread tightening: narrowing spread signals impending move
    - Time-to-resolve pressure: activity spike near resolution
    """

    name = "onchain"

    def __init__(self, large_trade_multiplier: float = 3.0,
                 volume_anomaly_window: int = 10):
        self.large_trade_multiplier = large_trade_multiplier
        self.volume_anomaly_window = volume_anomaly_window

    def _detect_volume_concentration(self, volumes: list[float]) -> dict:
        """Detect if recent volume is concentrated (whale activity)."""
        if len(volumes) < self.volume_anomaly_window:
            return {"concentration": 0.0, "whale_detected": False}

        recent = volumes[-min(len(volumes), 5):]
        baseline = volumes[-self.volume_anomaly_window:-min(len(volumes), 5)] or [1]
        avg_baseline = sum(baseline) / len(baseline)

        if avg_baseline <= 0:
            return {"concentration": 0.0, "whale_detected": False}

        recent_avg = sum(recent) / len(recent)
        concentration = recent_avg / avg_baseline
        whale = concentration >= self.large_trade_multiplier

        return {
            "concentration": round(concentration, 2),
            "whale_detected": whale,
            "recent_avg_vol": round(recent_avg, 2),
            "baseline_avg_vol": round(avg_baseline, 2),
        }

    def _detect_price_volume_divergence(self, prices, volumes) -> float:
        """Detect price move without volume support -> weak signal."""
        if len(prices) < 5 or len(volumes) < 5:
            return 0.0

        price_change = (prices[-1] - prices[-5]) / max(prices[-5], 0.001)
        avg_vol = sum(volumes[-5:]) / 5
        prior_vol = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else avg_vol

        if prior_vol <= 0:
            return 0.0

        vol_change = avg_vol / prior_vol
        # Large price move with low volume = divergence (negative signal)
        if abs(price_change) > 0.05 and vol_change < 1.0:
            divergence = abs(price_change) * (1 - vol_change)
            return -min(divergence * 5, 0.5)  # Negative score, capped
        return 0.0

    def generate_signal(self, snapshot: MarketSnapshot) -> Signal:
        prices = snapshot.prices
        volumes = snapshot.volumes

        if len(prices) < 10 or len(volumes) < 10:
            return self._hold(snapshot, "not enough history for on-chain analysis")

        # Volume concentration (whale detection)
        vol_conc = self._detect_volume_concentration(volumes)

        # Price-volume divergence
        divergence = self._detect_price_volume_divergence(prices, volumes)

        # Time pressure — activity spike near expiry
        days_left = snapshot.days_left
        time_pressure = max(0, (7 - days_left) / 7) if days_left > 0 else 1.0

        # Composite score
        score = 0.0
        reasons = []

        if vol_conc["whale_detected"]:
            # Whale buying — could be informed
            # Check if price is moving up with the volume
            if len(prices) >= 3 and prices[-1] > prices[-3]:
                score += 0.3
                reasons.append(f"whale volume ({vol_conc['concentration']}x)")
            else:
                score -= 0.1
                reasons.append(f"whale selling ({vol_conc['concentration']}x)")

        if divergence < 0:
            score += divergence
            reasons.append("price-volume divergence")

        if time_pressure > 0.5 and vol_conc["concentration"] > 1.5:
            score += 0.15 * time_pressure
            reasons.append(f"late activity spike (T-{days_left}d)")

        if not reasons:
            return self._hold(snapshot, "no significant on-chain signals")

        confidence = min(0.5 + abs(score) * 0.4, 0.88)

        if score > 0.15:
            return Signal(
                action=Action.BUY,
                confidence=round(confidence, 3),
                reason="On-chain: " + ", ".join(reasons),
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata={"vol_concentration": vol_conc, "divergence": divergence, "time_pressure": time_pressure},
            )
        elif score < -0.15:
            return Signal(
                action=Action.SELL,
                confidence=round(confidence, 3),
                reason="On-chain: " + ", ".join(reasons),
                market_id=snapshot.market_id,
                price=snapshot.current_price,
                metadata={"vol_concentration": vol_conc, "divergence": divergence, "time_pressure": time_pressure},
            )

        return self._hold(snapshot, f"on-chain signals weak (score={score:.2f})")


# ---------------------------------------------------------------------------
# Strategy Registration
# ---------------------------------------------------------------------------

STRATEGIES: list[BaseStrategy] = [
    MomentumStrategy(),
    MeanReversionStrategy(),
    VolumeSpikeStrategy(),
    TimesFMStrategy(),
    NewsSentimentStrategy(),
    OnChainAnalysisStrategy(),
]


def evaluate_all(snapshot: MarketSnapshot) -> Optional[Signal]:
    """
    Run all strategies, log every signal to the accuracy tracker,
    and return the best tradeable signal when strategies agree.
    """
    try:
        from src.trading.signal_accuracy import get_tracker
        tracker = get_tracker()
    except Exception:
        tracker = None

    signals = [s.generate_signal(snapshot) for s in STRATEGIES]

    # Log all signals for accuracy tracking
    if tracker:
        for sig, strat in zip(signals, STRATEGIES):
            if sig.action != Action.HOLD:
                try:
                    tracker.log_signal(
                        strategy=strat.name,
                        market_id=snapshot.market_id,
                        action=sig.action.value,
                        confidence=sig.confidence,
                        price=snapshot.current_price,
                    )
                except Exception:
                    pass

    tradeable = [s for s in signals if s.is_tradeable]
    if not tradeable:
        return None

    # Mixed signals — don't trade
    if len({s.action for s in tradeable}) > 1:
        return None

    return max(tradeable, key=lambda s: s.confidence)
