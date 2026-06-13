import os
import aiohttp
from typing import Optional


class SlackNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')

    async def send_message(self, message: str, blocks: Optional[list] = None) -> bool:
        if not self.webhook_url:
            print("Slack webhook not configured")
            return False
        payload = {"text": message}
        if blocks:
            payload["blocks"] = blocks
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Slack send error: {e}")
            return False

    async def send_trade_alert(self, trade: dict) -> bool:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🔔 Trade Executed"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Symbol:*\n{trade.get('symbol', 'UNKNOWN')}"},
                {"type": "mrkdwn", "text": f"*Direction:*\n{trade.get('direction', 'BUY')}"},
                {"type": "mrkdwn", "text": f"*Amount:*\n${trade.get('amount', 0):.2f}"},
                {"type": "mrkdwn", "text": f"*PnL:*\n${trade.get('pnl', 0):.2f}"}
            ]}
        ]
        return await self.send_message("New trade executed", blocks)

    async def send_alert(self, title: str, message: str, severity: str = "info") -> bool:
        emoji = {"error": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {title}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message}}
        ]
        return await self.send_message(f"{emoji} {title}", blocks)