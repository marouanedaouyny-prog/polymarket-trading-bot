import sqlite3
import os
from datetime import datetime
from src.utils.logger import logger

class SQLiteDB:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')), 'data', 'market_data.sqlite')
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_table()
        logger.info(f"SQLiteDB initialized at {self.db_path}")

    def _ensure_table(self):
        try:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS markets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT,
                    data TEXT,
                    fetched_at TEXT
                )
            ''')
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error creating markets table: {e}")

    def insert_market(self, market_id: str, data: str):
        try:
            self.conn.execute(
                'INSERT INTO markets (market_id, data, fetched_at) VALUES (?, ?, ?)',
                (market_id, data, datetime.utcnow().isoformat())
            )
            self.conn.commit()
            logger.info(f"Inserted market {market_id} into SQLiteDB")
        except Exception as e:
            logger.error(f"Failed to insert market {market_id}: {e}")

    def get_recent(self, limit: int = 100):
        try:
            cur = self.conn.execute(
                'SELECT market_id, data, fetched_at FROM markets ORDER BY fetched_at DESC LIMIT ?', (limit,)
            )
            rows = cur.fetchall()
            return [
                {"market_id": row[0], "data": row[1], "fetched_at": row[2]}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error retrieving recent markets: {e}")
            return []
