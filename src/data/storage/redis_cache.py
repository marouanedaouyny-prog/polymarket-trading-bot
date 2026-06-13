"""
Redis cache module for fast data access.
"""

import redis
import os

class RedisCache:
    """Redis cache for storing frequently accessed data."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize Redis connection."""
        self.host = host
        self.port = port
        self.db = db
        try:
            self.client = redis.Redis(host=host, port=port, db=db)
        except:
            self.client = None

    def set(self, key: str, value: str):
        """Set a key-value pair in Redis."""
        try:
            if self.client:
                self.client.set(key, value)
                return True
        except Exception as e:
            print(f"Error setting key in Redis: {str(e)}")
            return False

    def get(self, key: str):
        """Get a value from Redis by key."""
        try:
            if self.client:
                return self.client.get(key)
            return None
        except Exception as e:
            print(f"Error getting key from Redis: {str(e)}")
            return None