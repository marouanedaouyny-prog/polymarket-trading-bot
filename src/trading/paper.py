import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import random


@dataclass
class PaperPosition:
    symbol: str
    direction: str
    amount: float
    entry_price: float
    current_price: float
    opened_at: datetime
    pnl: float = 0.0


@dataclass
class PaperTrade:
    id: str
    symbol: str
    direction: str
    amount: float
    price: float
    timestamp: datetime
    pnl: float = 0.0


class PaperTradingEngine:
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[PaperTrade] = []
        self.pending_orders: List[dict] = []

    def open_position(self, symbol: str, direction: str, amount: float, price: float) -> bool:
        cost = amount * price
        if cost > self.balance:
            return False
        
        self.balance -= cost
        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            direction=direction,
            amount=amount,
            entry_price=price,
            current_price=price,
            opened_at=datetime.now()
        )
        return True

    def close_position(self, symbol: str, current_price: float, reason: str = "manual") -> Optional[float]:
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        pos.current_price = current_price
        
        if pos.direction == "BUY":
            pnl = (current_price - pos.entry_price) * pos.amount
        else:
            pnl = (pos.entry_price - current_price) * pos.amount
        
        self.balance += (pos.amount * current_price) + pnl
        
        trade = PaperTrade(
            id=f"paper_{len(self.trade_history) + 1}",
            symbol=symbol,
            direction=pos.direction,
            amount=pos.amount,
            price=current_price,
            timestamp=datetime.now(),
            pnl=pnl
        )
        self.trade_history.append(trade)
        
        del self.positions[symbol]
        return pnl

    def update_prices(self, prices: Dict[str, float]):
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price

    def get_unrealized_pnl(self) -> float:
        total = 0.0
        for pos in self.positions.values():
            if pos.direction == "BUY":
                pnl = (pos.current_price - pos.entry_price) * pos.amount
            else:
                pnl = (pos.entry_price - pos.current_price) * pos.amount
            total += pnl
        return total

    def get_total_equity(self) -> float:
        return self.balance + self.get_unrealized_pnl()

    def get_stats(self) -> dict:
        closed_trades = [t for t in self.trade_history if t.pnl != 0]
        wins = sum(1 for t in closed_trades if t.pnl > 0)
        total_pnl = sum(t.pnl for t in closed_trades)
        
        return {
            "balance": self.balance,
            "equity": self.get_total_equity(),
            "unrealized_pnl": self.get_unrealized_pnl(),
            "total_trades": len(self.trade_history),
            "winning_trades": wins,
            "losing_trades": len(closed_trades) - wins,
            "win_rate": (wins / len(closed_trades) * 100) if closed_trades else 0,
            "total_pnl": total_pnl,
            "return_pct": ((self.get_total_equity() - self.initial_balance) / self.initial_balance) * 100
        }

    def reset(self):
        self.balance = self.initial_balance
        self.positions.clear()
        self.trade_history.clear()


class SimulatedMarket:
    def __init__(self, volatility: float = 0.02):
        self.volatility = volatility
        self.prices: Dict[str, float] = {}
        self._running = False

    def set_price(self, symbol: str, price: float):
        self.prices[symbol] = price

    async def simulate(self, symbol: str) -> float:
        current = self.prices.get(symbol, 0.5)
        change = random.uniform(-self.volatility, self.volatility)
        new_price = max(0.01, min(0.99, current * (1 + change)))
        self.prices[symbol] = new_price
        return new_price

    async def run(self, symbols: List[str], interval: float = 1.0):
        self._running = True
        while self._running:
            for symbol in symbols:
                await self.simulate(symbol)
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False