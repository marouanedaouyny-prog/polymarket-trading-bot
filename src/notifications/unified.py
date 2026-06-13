import os
import asyncio
from typing import Optional
from .telegram import TelegramNotifier
from .slack import SlackNotifier
from .local import LocalNotifier, WindowsToastNotifier


class NotificationManager:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.slack = SlackNotifier()
        self.local = LocalNotifier()
        self.toast = WindowsToastNotifier()
        
        self.telegram_enabled = bool(self.telegram.bot_token and self.telegram.chat_id)
        self.slack_enabled = bool(self.slack.webhook_url)

    async def send_all(self, message: str, title: str = None):
        results = {}
        
        if self.telegram_enabled:
            results['telegram'] = await self.telegram.send_message(message)
        else:
            results['telegram'] = 'disabled'
        
        if self.slack_enabled:
            results['slack'] = await self.slack.send_message(message)
        else:
            results['slack'] = 'disabled'
        
        results['local'] = self.local.send_message(message)
        
        if title:
            self.toast.send(title, message)
        
        return results

    async def send_trade_alert(self, trade: dict):
        symbol = trade.get('symbol', 'UNKNOWN')
        direction = trade.get('direction', 'BUY')
        amount = trade.get('amount', 0)
        pnl = trade.get('pnl', 0)
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        msg = f"{emoji} {direction} {symbol} ${amount:.2f} | PnL: ${pnl:.2f}"
        
        return await self.send_all(msg, "Trade Alert")

    async def send_stop_loss(self, trade: dict, loss: float):
        msg = f"🛑 Stop Loss: ${loss:.2f} | {trade.get('symbol')}"
        return await self.send_all(msg, "Stop Loss!")

    async def send_daily_summary(self, stats: dict):
        msg = f"📊 Trades: {stats.get('total_trades')} | Win Rate: {stats.get('win_rate', 0):.1f}% | PnL: ${stats.get('total_pnl', 0):.2f}"
        return await self.send_all(msg, "Daily Summary")

    def get_local_logs(self, count: int = 10):
        return self.local.get_recent(count)


_notifier: Optional[NotificationManager] = None

def get_notifier() -> NotificationManager:
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
    return _notifier