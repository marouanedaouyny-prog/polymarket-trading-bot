import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import random
from src.utils.logger import logger


@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread: float
    profit_potential: float
    timestamp: datetime


class ArbitrageScanner:
    def __init__(
        self,
        min_spread: float = 0.02,
        min_profit: float = 0.01,
        check_interval: float = 5.0
    ):
        self.min_spread = min_spread
        self.min_profit = min_profit
        self.check_interval = check_interval
        self.markets: Dict[str, Dict[str, float]] = {}
        self.opportunities: List[ArbitrageOpportunity] = []
        self._running = False

    def add_market_price(self, symbol: str, exchange: str, price: float):
        if symbol not in self.markets:
            self.markets[symbol] = {}
        self.markets[symbol][exchange] = price

    async def scan(self) -> List[ArbitrageOpportunity]:
        opportunities = []
        
        for symbol, exchanges in self.markets.items():
            if len(exchanges) < 2:
                continue
            
            prices = sorted(exchanges.items(), key=lambda x: x[1])
            lowest = prices[0]
            highest = prices[-1]
            
            spread = (highest[1] - lowest[1]) / lowest[1]
            profit = spread - 0.01  # Subtract estimated fees
            
            if spread >= self.min_spread and profit >= self.min_profit:
                opp = ArbitrageOpportunity(
                    symbol=symbol,
                    buy_exchange=lowest[0],
                    sell_exchange=highest[0],
                    buy_price=lowest[1],
                    sell_price=highest[1],
                    spread=spread,
                    profit_potential=profit,
                    timestamp=datetime.now()
                )
                opportunities.append(opp)
                self.opportunities.append(opp)
        
        return opportunities

    async def run(self, symbols: List[str]):
        self._running = True
        logger.info(f"Arbitrage scanner started for {len(symbols)} symbols")
        
        while self._running:
            for symbol in symbols:
                base_price = 0.5 + random.uniform(-0.2, 0.2)
                self.add_market_price(symbol, "polymarket", base_price)
                self.add_market_price(symbol, "exchange_b", base_price * (1 + random.uniform(-0.03, 0.03)))
                self.add_market_price(symbol, "exchange_c", base_price * (1 + random.uniform(-0.03, 0.03)))
            
            await self.scan()
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._running = False

    def get_opportunities(self, since_minutes: int = 60) -> List[ArbitrageOpportunity]:
        cutoff = datetime.now().timestamp() - (since_minutes * 60)
        return [o for o in self.opportunities if o.timestamp.timestamp() > cutoff]

    def get_stats(self) -> dict:
        recent = self.get_opportunities()
        if not recent:
            return {"total_opportunities": 0, "avg_spread": 0, "avg_profit": 0}
        
        return {
            "total_opportunities": len(recent),
            "avg_spread": sum(o.spread for o in recent) / len(recent),
            "avg_profit": sum(o.profit_potential for o in recent) / len(recent),
            "best_opportunity": max(recent, key=lambda x: x.profit_potential).symbol if recent else None
        }