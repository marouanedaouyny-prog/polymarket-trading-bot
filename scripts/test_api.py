#!/usr/bin/env python3
"""
Quick test to verify Polymarket market-data access.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

for proxy_var in (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
):
    os.environ.pop(proxy_var, None)

load_dotenv(PROJECT_ROOT / ".env")

from src.data.polymarket_client import PolymarketClient


def main():
    client = PolymarketClient()
    markets = client.get_markets(limit=3)
    print("API access successful")
    print("Live markets:")
    for market in markets:
        print(f"- {market.get('question', '')[:50]}... (Active: {not market.get('closed', False)})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"API access failed: {e}")
