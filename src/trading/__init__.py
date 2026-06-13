from .paper import PaperTradingEngine, SimulatedMarket
from .backtest import Backtester
# Import MultiWalletManager only if web3 is available
try:
    from .multiwallet import MultiWalletManager
except ImportError:
    MultiWalletManager = None  # Optional dependency
from .arbitrage import ArbitrageScanner

__all__ = [
    'PaperTradingEngine',
    'SimulatedMarket', 
    'Backtester',
    'MultiWalletManager',
    'ArbitrageScanner'
]