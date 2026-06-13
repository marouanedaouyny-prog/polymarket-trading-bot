"""
Prometheus metrics for production monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest

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

ACTIVE_TRADES = Gauge(
    'active_trades',
    'Number of currently active trades'
)

BALANCE = Gauge(
    'account_balance',
    'Current account balance'
)

WIN_RATE = Gauge(
    'win_rate',
    'Current session win rate'
)

TRADES_COUNT = Counter(
    'trades_total',
    'Total number of trades',
    ['result']
)

def get_metrics():
    """Return all metrics in Prometheus format."""
    return generate_latest()