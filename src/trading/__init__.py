from .paper import PaperTradingEngine, SimulatedMarket
from .backtest import Backtester
from .signal_filter import filter_markets, score_markets
from .strategies import (
    BaseStrategy, MomentumStrategy, MeanReversionStrategy,
    VolumeSpikeStrategy, NewsSentimentStrategy, OnChainAnalysisStrategy,
    MarketSnapshot, Signal, Action, evaluate_all,
)
from .indicators import rsi, macd, bollinger_bands, atr, volume_spike, obv, market_score
from .signal_accuracy import SignalAccuracyTracker, get_tracker

try:
    from .multiwallet import MultiWalletManager
except ImportError:
    MultiWalletManager = None

from .arbitrage import ArbitrageScanner

__all__ = [
    "PaperTradingEngine", "SimulatedMarket", "Backtester",
    "filter_markets", "score_markets",
    "BaseStrategy", "MomentumStrategy", "MeanReversionStrategy",
    "VolumeSpikeStrategy", "MarketSnapshot", "Signal", "Action", "evaluate_all",
    "rsi", "macd", "bollinger_bands", "atr", "volume_spike", "obv", "market_score",
    "SignalAccuracyTracker", "get_tracker",
    "MultiWalletManager", "ArbitrageScanner",
]
