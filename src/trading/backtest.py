import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass


@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_pnl: float
    equity_curve: List[float]
    trades: List[dict]


class Backtester:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, dict] = {}
        self.trades: List[dict] = []
        self.equity_curve: List[float] = []

    def run(
        self,
        data: pd.DataFrame,
        strategy: Callable[[pd.DataFrame, dict], dict],
        fees: float = 0.0,
        slippage: float = 0.0
    ) -> BacktestResult:
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.initial_balance]

        df = data.copy()
        
        for i in range(len(df)):
            current_bar = df.iloc[i]
            timestamp = current_bar.get('timestamp', datetime.now())
            
            signal = strategy(df.iloc[:i+1], self.positions)
            
            if signal.get('action') == 'buy' and 'symbol' in signal:
                symbol = signal['symbol']
                price = current_bar.get('close', current_bar.get('price', 0.5))
                amount = signal.get('amount', self.balance * 0.1)
                
                cost = amount * price * (1 + fees + slippage)
                if cost <= self.balance:
                    self.balance -= cost
                    self.positions[symbol] = {
                        'entry_price': price,
                        'amount': amount,
                        'timestamp': timestamp
                    }
                    self.trades.append({
                        'timestamp': timestamp,
                        'action': 'buy',
                        'symbol': symbol,
                        'price': price,
                        'amount': amount
                    })

            elif signal.get('action') == 'sell' and 'symbol' in signal:
                symbol = signal['symbol']
                if symbol in self.positions:
                    price = current_bar.get('close', current_bar.get('price', 0.5))
                    pos = self.positions[symbol]
                    pnl = (price - pos['entry_price']) * pos['amount']
                    pnl -= pnl * (fees + slippage)
                    
                    self.balance += pos['amount'] * price + pnl
                    self.trades.append({
                        'timestamp': timestamp,
                        'action': 'sell',
                        'symbol': symbol,
                        'price': price,
                        'amount': pos['amount'],
                        'pnl': pnl
                    })
                    del self.positions[symbol]

            equity = self.balance + sum(
                p['amount'] * (df.iloc[i].get('close', p['entry_price']) - p['entry_price'])
                for p in self.positions.values()
            )
            self.equity_curve.append(equity)

        return self._calculate_results()

    def _calculate_results(self) -> BacktestResult:
        closed_trades = [t for t in self.trades if t['action'] == 'sell']
        pnl_values = [t.get('pnl', 0) for t in closed_trades]
        
        total_return = (self.equity_curve[-1] - self.initial_balance) / self.initial_balance
        
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 and np.std(returns) > 0 else 0
        
        peak = self.equity_curve[0]
        max_dd = 0
        for value in self.equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd

        wins = sum(1 for p in pnl_values if p > 0)
        
        return BacktestResult(
            total_return=total_return * 100,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd * 100,
            win_rate=wins / len(pnl_values) * 100 if pnl_values else 0,
            total_trades=len(closed_trades),
            avg_trade_pnl=np.mean(pnl_values) if pnl_values else 0,
            equity_curve=self.equity_curve,
            trades=self.trades
        )

    def generate_historical_data(
        self,
        symbols: List[str],
        days: int = 30,
        start_price: float = 0.5
    ) -> pd.DataFrame:
        dates = pd.date_range(end=datetime.now(), periods=days * 24, freq='h')
        data = []
        
        for symbol in symbols:
            price = start_price
            for date in dates:
                change = np.random.randn() * 0.02
                price = max(0.01, min(0.99, price + change))
                data.append({
                    'timestamp': date,
                    'symbol': symbol,
                    'open': price,
                    'high': price + abs(np.random.randn() * 0.01),
                    'low': price - abs(np.random.randn() * 0.01),
                    'close': price,
                    'volume': np.random.randint(1000, 100000)
                })
        
        return pd.DataFrame(data)