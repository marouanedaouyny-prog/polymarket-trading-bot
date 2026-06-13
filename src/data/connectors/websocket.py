"""
WebSocket connector for real-time market data streaming.
"""

import asyncio
import websockets
from typing import Dict, Callable
import json
import aiohttp

class WebSocketConnector:
    """WebSocket connector for real-time market data."""

    def __init__(self, url: str = "wss://stream.polymarket.com"):
        """Initialize the WebSocket connector."""
        self.url = url
        self.websocket = None

    async def connect(self):
        """Connect to the WebSocket."""
        try:
            self.websocket = await websockets.connect(self.url)
            print("WebSocket connection established")
        except Exception as e:
            print(f"Failed to connect to WebSocket: {str(e)}")

    async def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a WebSocket channel."""
        if not self.websocket:
            await self.connect()

        try:
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "topic": channel
            }
            await self.websocket.send(json.dumps(subscribe_msg))

            # Listen for messages
            async for message in self.websocket:
                data = json.loads(message)
                await callback(data)
        except Exception as e:
            print(f"Error in WebSocket subscription: {str(e)}")

    async def disconnect(self):
        """Disconnect from the WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None