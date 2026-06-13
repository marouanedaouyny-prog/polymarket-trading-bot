#!/usr/bin/env python3
"""
Quick start script for the Polymarket trading bot.
"""

import os
import sys
import subprocess

def main():
    """Main function to start the bot."""
    print("Starting Polymarket Trading Bot...")

    # Check if required files exist
    if not os.path.exists('.env'):
        print("Creating default .env file...")
        with open('.env', 'w') as f:
            f.write("""POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_API_SECRET=your_api_secret_here
POLYMARKET_API_PASSPHRASE=your_api_passphrase_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=polymarket_trading
DB_USER=trader
DB_PASSWORD=secret123
REDIS_HOST=localhost
REDIS_PORT=6379
MAX_POSITION_SIZE=0.05
DAILY_LOSS_LIMIT=0.05
MAX_DRAWDOWN=0.10
ENVIRONMENT=development
DEBUG=True""")
        print("   Created .env file - please update with your actual values")

    # Start the bot
    print("Starting the Polymarket trading bot...")

    # You can add code here to start the bot components
    # For now, we'll just print instructions
    print("To start the bot, run:")
    print("   python src/polymarket_bot/main.py")
    print("Or to start the API server:")
    print("   uvicorn src.polymarket_bot.api.main:app --reload")

if __name__ == "__main__":
    main()
