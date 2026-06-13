import asyncio
import os
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

os.chdir(root)

from dotenv import load_dotenv
load_dotenv(root / "config" / ".env")

from src.notifications.telegram import TelegramNotifier

async def test():
    notifier = TelegramNotifier()
    print(f"Bot Token: {notifier.bot_token}")
    print(f"Chat ID: {notifier.chat_id}")
    result = await notifier.send_message("🤖 Polymarket Trading Bot is online!")
    print(f"Test message sent: {result}")

asyncio.run(test())