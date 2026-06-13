# Polymarket Trading Bot

A professional market-making bot for Polymarket prediction markets.

## Features
- Market data ingestion from Polymarket APIs
- Real-time order book analysis
- Market-making strategies with fair value modeling
- Risk management and position limits
- Performance monitoring and metrics
- Builder fee monetization capabilities

## Installation
```bash
pip install -e .
```

## Configuration
Create a `.env` file with your configuration:
```
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_API_SECRET=your_api_secret_here
POLYMARKET_API_PASSPHRASE=your_api_passphrase_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=polymarket_trading
DB_USER=trader
DB_PASSWORD=secret123
```

The complete paper/live template is in `src/.env.example`. Use that as the source of truth if you are running the `src/` layout directly.

## Usage
```bash
python src/polymarket_bot/scripts/run_paper.py
```

Live mode is protected by a safety gate and will only start when:
```bash
POLYMARKET_API_PASSPHRASE=your_api_passphrase_here
PRIVATE_KEY=your_wallet_private_key
ENABLE_LIVE_TRADING=true
```
