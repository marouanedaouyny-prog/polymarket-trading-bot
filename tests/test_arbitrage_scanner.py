import asyncio
import pytest
from src.trading.arbitrage import ArbitrageScanner, ArbitrageOpportunity

@pytest.mark.asyncio
async def test_arbitrage_detection():
    scanner = ArbitrageScanner(min_spread=0.0, min_profit=0.0, check_interval=0.1)
    # Add two exchanges with price difference
    scanner.add_market_price('TEST', 'ex1', 1.0)
    scanner.add_market_price('TEST', 'ex2', 1.5)
    opportunities = await scanner.scan()
    assert isinstance(opportunities, list)
    assert len(opportunities) == 1
    opp = opportunities[0]
    assert isinstance(opp, ArbitrageOpportunity)
    assert opp.symbol == 'TEST'
    assert opp.buy_exchange == 'ex1'
    assert opp.sell_exchange == 'ex2'
    assert opp.spread == pytest.approx((1.5 - 1.0) / 1.0)
