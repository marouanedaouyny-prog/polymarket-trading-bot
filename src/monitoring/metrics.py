"""
Prometheus metrics for production monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# --- HTTP instrumentation ---
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# --- Trading gauges (updated by update_trading_metrics) ---
BALANCE = Gauge('trading_balance_usd', 'Current account balance in USD')
DRAWDOWN = Gauge('trading_drawdown_pct', 'Current drawdown as a fraction (0-1)')
WIN_RATE = Gauge('trading_win_rate', 'Session win rate (0-1)')
OPEN_POSITIONS = Gauge('trading_open_positions', 'Number of open positions')
DAILY_PNL = Gauge('trading_daily_pnl_usd', 'Realised P&L since midnight UTC')
ACTIVE_TRADES = Gauge('trading_active_trades', 'Number of currently active trades')
TRADES_COUNT = Counter('trades_total', 'Total number of trades', ['result'])


def update_trading_metrics(
    balance: float,
    drawdown: float,
    win_rate: float,
    open_positions: int,
    daily_pnl: float,
) -> None:
    """Push current trading state into Prometheus gauges."""
    BALANCE.set(balance)
    DRAWDOWN.set(drawdown)
    WIN_RATE.set(win_rate)
    OPEN_POSITIONS.set(open_positions)
    DAILY_PNL.set(daily_pnl)


def get_metrics() -> bytes:
    """Return all metrics in Prometheus text format."""
    return generate_latest()
