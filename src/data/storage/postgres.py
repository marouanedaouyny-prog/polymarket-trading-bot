"""
Database storage module for persisting market data and trades.
"""

import asyncio
from typing import Dict, List
import asyncpg
import os

class DatabaseStorage:
    """Handles database operations for storing market data and trades."""

    def __init__(self):
        """Initialize database connection parameters."""
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "polymarket_trading")
        self.user = os.getenv("DB_USER", "trader")
        self.password = os.getenv("DB_PASSWORD", "secret123")
        self.connection = None

    async def connect(self):
        """Connect to the database."""
        try:
            self.connection = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("Database connection established")
        except Exception as e:
            print(f"Failed to connect to database: {str(e)}")
            self.connection = None

    async def store_market_data(self, market_data: Dict):
        """Store market data in the database."""
        if not self.connection:
            await self.connect()

        if self.connection:
            try:
                # In a production implementation, we would insert the market data
                # For now, we'll just print that we would store it
                print(f"Storing market data: {market_data}")
                return True
            except Exception as e:
                print(f"Error storing market data: {str(e)}")
                return False
        return False

    async def store_trade(self, trade_data: Dict):
        """Store trade execution data."""
        if not self.connection:
            await self.connect()

        if self.connection:
            try:
                # In a production implementation, we would insert the trade data
                # For now, we'll just print that we would store it
                print(f"Storing trade data: {trade_data}")
                return True
            except Exception as e:
                print(f"Error storing trade data: {str(e)}")
                return False
        return False