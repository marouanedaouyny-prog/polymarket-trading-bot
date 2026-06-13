# Database Integration Module
# Handles storage of historical data and trade history

import asyncio
import asyncpg
from typing import Dict, List, Optional
import pandas as pd

class DatabaseManager:
    def __init__(self, host: str = "localhost", port: int = 5432,
                 database: str = "polymarket_trading", user: str = "trader",
                 password: str = "secret123"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    async def connect(self):
        """Establish database connection"""
        try:
            self.connection = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            print("Database connection established")
        except Exception as e:
            print(f"Failed to connect to database: {e}")

    async def disconnect(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            print("Database connection closed")

    async def create_tables(self):
        """Create required database tables"""
        if not self.connection:
            await self.connect()

        # Create market data table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                market_id VARCHAR(100),
                price NUMERIC,
                volume NUMERIC,
                bid_price NUMERIC,
                ask_price NUMERIC,
                bid_size NUMERIC,
                ask_size NUMERIC
            )
        """)

        # Create trades table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                order_id VARCHAR(100),
                symbol VARCHAR(50),
                quantity NUMERIC,
                price NUMERIC,
                side VARCHAR(10),
                status VARCHAR(20)
            )
        """)

        print("Database tables created")

    async def store_market_data(self, data: Dict):
        """Store market data in database"""
        if not self.connection:
            await self.connect()

        try:
            await self.connection.execute("""
                INSERT INTO market_data (
                    timestamp, market_id, price, volume,
                    bid_price, ask_price, bid_size, ask_size
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            data.get('timestamp'), data.get('market_id'), data.get('price'),
            data.get('volume'), data.get('bid_price'), data.get('ask_price'),
            data.get('bid_size'), data.get('ask_size')
            )
            print("Market data stored successfully")
        except Exception as e:
            print(f"Error storing market data: {e}")

    async def store_trade(self, trade_data: Dict):
        """Store trade execution in database"""
        if not self.connection:
            await self.connect()

        try:
            await self.connection.execute("""
                INSERT INTO trades (
                    timestamp, order_id, symbol, quantity, price, side, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            trade_data.get('timestamp'), trade_data.get('order_id'),
            trade_data.get('symbol'), trade_data.get('quantity'),
            trade_data.get('price'), trade_data.get('side'), trade_data.get('status')
            )
            print("Trade data stored successfully")
        except Exception as e:
            print(f"Error storing trade data: {e}")