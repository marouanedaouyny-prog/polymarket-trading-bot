import os
import aiohttp
from typing import Optional


class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        if not self.bot_token or not self.chat_id:
            print("Telegram credentials not configured")
            return False
        url = f"{self.api_url}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": parse_mode}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False

    async def send_trade_alert(self, trade: dict) -> bool:
        symbol = trade.get('symbol', 'UNKNOWN')
        direction = trade.get('direction', 'BUY')
        amount = trade.get('amount', 0)
        price = trade.get('price', 0)
        pnl = trade.get('pnl', 0)
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        msg = f"""
{emoji} *Trade Executed*

*Symbol:* `{symbol}`
*Direction:* {direction}
*Amount:* ${amount:.2f}
*Price:* ${price:.4f}
*PnL:* ${pnl:.2f}
"""
        return await self.send_message(msg)

    async def send_stop_loss(self, trade: dict, loss: float) -> bool:
        msg = f"🛑 *Stop Loss Triggered*\n\nLoss: ${loss:.2f}\nSymbol: {trade.get('symbol')}"
        return await self.send_message(msg)

    async def send_daily_summary(self, stats: dict) -> bool:
        msg = f"""
📊 *Daily Trading Summary*

*Trades:* {stats.get('total_trades', 0)}
*Win Rate:* {stats.get('win_rate', 0):.1f}%
*Total PnL:* ${stats.get('total_pnl', 0):.2f}
*Volume:* ${stats.get('total_volume', 0):.2f}
"""
        return await self.send_message(msg)