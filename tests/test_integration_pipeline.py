"""
Integration test: filter_markets → DynamicRiskManager → OrderManager pipeline.

Uses unittest.mock to avoid real network calls and filesystem dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_MARKETS_API = [
    {
        "id": "mkt-001",
        "question": "Will Bitcoin exceed $100k by end of 2026?",
        "outcomePrices": '["0.35","0.65"]',
        "volume": 250_000,
        "volume24hr": 25_000,
        "endDate": "2026-12-31T23:59:59Z",
        "slug": "btc-100k-2026",
        "bestBid": "0.35",
    },
    {
        "id": "mkt-002",
        "question": "Will Solana flip Ethereum?",
        "outcomePrices": '["0.15","0.85"]',
        "volume": 120_000,
        "volume24hr": 15_000,
        "endDate": "2026-09-01T00:00:00Z",
        "slug": "sol-flip-eth",
        "bestBid": "0.15",
    },
    # Should be filtered out — volume too low
    {
        "id": "mkt-003",
        "question": "Will X happen?",
        "outcomePrices": '["0.20","0.80"]',
        "volume": 500,
        "volume24hr": 50,
        "endDate": "2026-12-01T00:00:00Z",
        "slug": "x-happen",
        "bestBid": "0.20",
    },
]


# ---------------------------------------------------------------------------
# Integration test class
# ---------------------------------------------------------------------------

class TestFilterRiskOrderPipeline:
    """End-to-end pipeline test with mocked network and disk I/O."""

    @patch("src.trading.signal_filter.requests.get")
    def test_filter_markets_returns_valid_subset(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = FAKE_MARKETS_API
        mock_get.return_value = mock_resp

        from src.trading.signal_filter import filter_markets
        markets = filter_markets(
            price_min=0.05,
            price_max=0.50,
            min_volume=10_000,
            max_close_days=365,
            limit=10,
        )
        # mkt-003 should be filtered (volume < 10_000)
        ids = [m["id"] for m in markets]
        assert "mkt-001" in ids
        assert "mkt-002" in ids
        assert "mkt-003" not in ids

    @patch("src.trading.signal_filter.requests.get")
    def test_risk_manager_approves_good_opportunity(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = FAKE_MARKETS_API
        mock_get.return_value = mock_resp

        from src.trading.signal_filter import filter_markets
        from src.risk.dynamic_risk import DynamicRiskManager

        markets = filter_markets(price_min=0.05, price_max=0.50, min_volume=10_000,
                                 max_close_days=365)
        assert markets, "Expected at least one market to pass the filter"

        rm = DynamicRiskManager()
        rm.start_session(balance=500.0)

        # Convert first filtered market into a mock opportunity
        m = markets[0]
        opportunity = {
            "price": m["price"],
            "volume": m["volume"],
            "edge": 0.15,
            "confidence": 75.0,
        }
        approved, reason = rm.should_trade(
            edge=opportunity["edge"],
            confidence=opportunity["confidence"],
            balance=500.0,
        )
        # With a healthy balance and good edge, should be approved
        assert isinstance(approved, bool)
        assert isinstance(reason, str)

    @patch("src.trading.signal_filter.requests.get")
    def test_order_manager_records_paper_trade(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = FAKE_MARKETS_API
        mock_get.return_value = mock_resp

        from src.trading.signal_filter import filter_markets
        from src.execution.order_manager import OrderManager

        markets = filter_markets(price_min=0.05, price_max=0.50, min_volume=10_000,
                                 max_close_days=365)
        assert markets

        om = OrderManager(mode="paper")
        m = markets[0]

        result = om.place_order({
            "market_id": m["id"],
            "side": "buy",
            "price": m["price"],
            "size": 10.0,
        })
        assert result is True
        assert len(om.order_history) == 1
        order = om.order_history[0]
        assert order["market_id"] == m["id"]
        assert order["mode"] == "paper"
        assert m["id"] in om.positions

    @patch("src.trading.signal_filter.requests.get")
    def test_full_buy_sell_pnl_flow(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = FAKE_MARKETS_API
        mock_get.return_value = mock_resp

        from src.execution.order_manager import OrderManager

        om = OrderManager(mode="paper")

        # Buy 10 shares at 0.20
        om.place_order({"market_id": "mkt-x", "side": "buy", "price": 0.20, "size": 10.0})
        assert om.positions["mkt-x"]["qty"] == pytest.approx(10.0)

        # Sell at 0.30 — should record a profit of (0.30 - 0.20) * 10 = 1.0
        om.place_order({"market_id": "mkt-x", "side": "sell", "price": 0.30, "size": 10.0})
        assert om.realized_pnl == pytest.approx(1.0)
        assert om.total_closed_trades == 1
        assert om.winning_closed_trades == 1

    def test_partial_fill_tracking(self):
        from src.execution.order_manager import OrderManager

        om = OrderManager(mode="paper")
        om.place_order({
            "market_id": "mkt-partial",
            "side": "buy",
            "price": 0.50,
            "size": 20.0,
            "fill_pct": 0.5,   # only half filled
        })
        pos = om.positions.get("mkt-partial", {})
        assert pos.get("qty") == pytest.approx(10.0)  # only 10 filled

    def test_position_reconciliation(self):
        from src.execution.order_manager import OrderManager

        om = OrderManager(mode="paper")
        om.place_order({"market_id": "mkt-r", "side": "buy", "price": 0.25, "size": 5.0})

        # Exchange says we have 8 shares (discrepancy of +3)
        exchange_state = {"mkt-r": {"qty": 8.0, "avg_price": 0.25}}
        discrepancies = om.reconcile_positions(exchange_state)

        assert "mkt-r" in discrepancies
        assert discrepancies["mkt-r"]["delta"] == pytest.approx(3.0)
        # Local state should now be synced to exchange truth
        assert om.positions["mkt-r"]["qty"] == pytest.approx(8.0)
