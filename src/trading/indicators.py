"""
Technical Indicators for Polymarket Signal Generation

Inspired by AlgoTrading strategies (RSI, MACD, Bollinger Bands, ATR, Volume).
All indicators operate on price/volume arrays and return scalar signals.
"""

from __future__ import annotations

from typing import Optional
import numpy as np


def rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """
    Relative Strength Index.
    Returns 0-100. Oversold < 30 (buy bias), Overbought > 70 (sell bias).
    """
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def macd(prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
         ) -> Optional[dict]:
    """
    MACD = EMA(fast) - EMA(slow), signal = EMA(macd, signal).
    Returns {'macd': float, 'signal': float, 'histogram': float}.
    Positive histogram → bullish momentum; negative → bearish.
    """
    if len(prices) < slow + signal:
        return None

    def ema(data: list[float], n: int) -> list[float]:
        k = 2 / (n + 1)
        result = [data[0]]
        for p in data[1:]:
            result.append(p * k + result[-1] * (1 - k))
        return result

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = [f - s for f, s in zip(ema_fast[slow - fast:], ema_slow)]
    signal_line = ema(macd_line, signal)
    hist = macd_line[-1] - signal_line[-1]
    return {
        "macd": round(macd_line[-1], 6),
        "signal": round(signal_line[-1], 6),
        "histogram": round(hist, 6),
    }


def bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0
                    ) -> Optional[dict]:
    """
    Bollinger Bands: middle (SMA), upper, lower.
    %B = (price - lower) / (upper - lower): <0 oversold, >1 overbought.
    """
    if len(prices) < period:
        return None
    window = prices[-period:]
    mid = float(np.mean(window))
    std = float(np.std(window, ddof=1))
    upper = mid + num_std * std
    lower = mid - num_std * std
    price = prices[-1]
    bandwidth = (upper - lower) / mid if mid != 0 else 0
    pct_b = (price - lower) / (upper - lower) if upper != lower else 0.5
    return {
        "upper": round(upper, 6),
        "middle": round(mid, 6),
        "lower": round(lower, 6),
        "bandwidth": round(bandwidth, 6),
        "pct_b": round(pct_b, 6),
    }


def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> Optional[float]:
    """
    Average True Range — measures volatility.
    Higher ATR = more volatile market.
    """
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return float(np.mean(trs[-period:]))


def volume_spike(volumes: list[float], period: int = 20, threshold: float = 2.0
                 ) -> Optional[bool]:
    """
    True if the latest volume is > threshold × average of prior period.
    Volume spike = unusual market activity (catalysts, news, resolution).
    """
    if len(volumes) < period + 1:
        return None
    avg = np.mean(volumes[-period - 1:-1])
    return volumes[-1] > threshold * avg if avg > 0 else False


def obv(prices: list[float], volumes: list[float]) -> Optional[float]:
    """
    On-Balance Volume — cumulative volume gated by price direction.
    Rising OBV with rising price = confirmed uptrend.
    """
    if len(prices) < 2 or len(volumes) < 2:
        return None
    result = 0.0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            result += volumes[i]
        elif prices[i] < prices[i - 1]:
            result -= volumes[i]
    return float(result)


def market_score(prices: list[float], volumes: list[float]) -> dict:
    """
    Composite score combining RSI, MACD, Bollinger %B, and volume.
    Returns a dict with individual signals and a combined [-1, 1] score.
      +1 = strong buy signal, -1 = strong sell signal
    """
    signals = {}
    score = 0.0
    weight_sum = 0.0

    r = rsi(prices)
    if r is not None:
        signals["rsi"] = round(r, 1)
        # RSI oversold → buy (+1), overbought → sell (-1)
        if r < 30:
            score += 1.0
        elif r > 70:
            score -= 1.0
        weight_sum += 1.0

    m = macd(prices)
    if m is not None:
        signals["macd_hist"] = m["histogram"]
        # Positive histogram → bullish
        score += np.clip(m["histogram"] * 100, -1, 1)
        weight_sum += 1.0

    bb = bollinger_bands(prices)
    if bb is not None:
        signals["bb_pct_b"] = bb["pct_b"]
        # Below lower band → buy (+1), above upper → sell (-1)
        if bb["pct_b"] < 0:
            score += 1.0
        elif bb["pct_b"] > 1:
            score -= 1.0
        weight_sum += 1.0

    vs = volume_spike(volumes)
    if vs is not None:
        signals["volume_spike"] = vs
        # Volume spike = more conviction, amplify by 0.5 in dominant direction
        if vs and score != 0:
            score += 0.5 * np.sign(score)
            weight_sum += 0.5

    combined = float(np.clip(score / weight_sum, -1, 1)) if weight_sum > 0 else 0.0
    signals["combined"] = round(combined, 3)
    return signals
