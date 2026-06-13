# Data Ingestion Pipeline
# Handles real-time and historical data collection from multiple sources

import asyncio
import json
from typing import Dict, List
from data.polymarket_client import PolymarketClient
from datetime import datetime

from src.utils.logger import logger

class DataIngestionPipeline:
    def __init__(self, api_key: str = None):
        self.polymarket_client = PolymarketClient(api_key)
        self.data_buffer = []
        self.is_running = False

    async def start_data_collection(self):
        """Start the data collection process"""
        self.is_running = True
        async with self.polymarket_client as client:
            while self.is_running:
                try:
                    # Fetch markets data
                    markets = await client.get_markets()
                    self.process_markets_data(markets)

                    # Wait before next collection cycle
                    await asyncio.sleep(1)  # Adjust frequency as needed
                except Exception as e:
                    print(f"Error in data collection: {e}")
                    await asyncio.sleep(10)  # Wait before retrying

    def process_markets_data(self, markets: List[Dict]):
        """Process incoming markets data"""
        # Process and store market data
        for market in markets:
            # Add timestamp
            market['timestamp'] = datetime.utcnow().isoformat()
            self.data_buffer.append(market)

            # Keep only recent data (last 1000 entries)
            if len(self.data_buffer) > 1000:
                self.data_buffer = self.data_buffer[-1000:]

        logger.info(f"Processed {len(markets)} markets")

    def stop_data_collection(self):
        """Stop the data collection process"""
        self.is_running = False

    def get_recent_data(self, limit: int = 100) -> List[Dict]:
        """Get recent market data"""
        return self.data_buffer[-limit:] if self.data_buffer else []