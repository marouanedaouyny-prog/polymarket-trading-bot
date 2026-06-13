# Polymarket Trading Bot - Project Structure

This implementation follows the recommendations from gptWay.md for a professional, production-ready trading system.

## Project Structure
- `src/polymarket_bot/` - Main package
- `api/` - API endpoints
- `core/` - Configuration and core utilities
- `data/` - Data connectors and storage
- `strategies/` - Trading strategies
- `risk/` - Risk management
- `execution/` - Order execution
- `research/` - Feature research and backtesting
- `telemetry/` - Monitoring and metrics

## Core Features
1. Market data ingestion (Gamma API, CLOB, WebSocket)
2. Market-making strategies with fair value modeling
3. Risk controls (position limits, drawdown limits, kill switches)
4. Builder fee monetization
5. Performance monitoring and metrics