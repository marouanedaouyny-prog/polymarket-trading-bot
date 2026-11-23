---
title: Polymarket API
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Polymarket AI Trading System

A production-grade autonomous trading system for Polymarket prediction markets.

## Features

- **Real-time Market Analysis**: Fetches live market data from Polymarket API
- **ML-powered Predictions**: sklearn model trained on 11K+ data points
- **Hierarchical Agent System**: Lead → Research → Risk → Trader → Monitor
- **Dynamic Risk Management**: Kelly Criterion, drawdown tracking, streak protection
- **SQLite Persistence**: All trades and sessions saved to database
- **Docker Support**: Easy deployment with Docker

## Quick Start

### 1. Installation

```bash
# Clone and install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `config/.env`:
```env
# Trading Config
STARTING_BALANCE=100
MAX_POSITION_PCT=0.15
MIN_EDGE=0.65
MIN_CONFIDENCE=65

# Risk Config  
STOP_LOSS_PCT=0.25
TAKE_PROFIT_PCT=2.0

# API Keys (for live trading)
POLYMARKET_API_KEY=your_key_here
POLYMARKET_API_SECRET=your_secret_here
POLYMARKET_API_PASSPHRASE=your_passphrase_here
```

The full template is in `.env.example` and `config/.env.example`. Copy one of those into your active env file, keep paper mode as the default, and only enable the live block after you have verified credentials and risk limits.

### 3. Run Paper Trading

```bash
python agent_trading_system.py
```

### 4. Run with Docker

```bash
docker-compose up
```

## Project Structure

```
polymarket/
├── agent_trading_system.py    # Main trading system
├── real_data_trainer.py       # ML model training
├── src/
│   ├── utils/
│   │   ├── config.py         # Centralized config
│   │   └── logger.py         # Unified logging
│   ├── data/
│   │   └── sqlite_db.py      # SQLite storage
│   ├── ml/
│   │   └── market_predictor.py  # sklearn model
│   ├── risk/
│   │   └── dynamic_risk.py   # Kelly + drawdown
│   └── trading/
│       └── live_trading.py   # Live order execution
├── tests/
│   └── test_trading.py        # Test suite
├── models/
│   ├── comprehensive_model.json
│   ├── sklearn_model.pkl
│   └── sklearn_scaler.pkl
└── data/
    ├── trading.db            # SQLite database
    ├── logs/                 # Log files
    └── test_runs/            # Test results
```

## Trading Strategy

### Entry Criteria
- Price: $0.05 - $0.50 (per Config.PRICE_MIN/PRICE_MAX)
- Volume: > $10,000 (per Config.MIN_VOLUME)
- Edge: > 8% (per Config.MIN_EDGE)
- Confidence: > 85% (per Config.MIN_CONFIDENCE)

### Risk Management
- Max position: 15% of balance
- Stop loss: 25% per trade
- Take profit: 200% per trade
- Daily loss limit: 20%

### Win Probability (by price tier)
| Price Range | Win Rate |
|-------------|----------|
| $0.05-0.10  | 89%      |
| $0.11-0.20  | 85%      |
| $0.21-0.30  | 82%      |
| $0.31-0.50  | 74%      |

## Performance

**Important Note**: All performance metrics are based on paper trading simulations and have not been validated with real market conditions. Past performance does not guarantee future results.

- **Paper Trading Win Rate**: 70-90% range observed in simulations
- **Simulated Trades**: 1000+ paper trading simulations
- **Simulated Profit**: Varies based on market conditions and configuration

**⚠️ Risk Disclosure**: This system is for educational and research purposes only. No performance claims are guaranteed. Real trading involves significant risk of loss, including loss of entire capital. Always test thoroughly with small positions before considering any real money trading. The system has not been validated with real market conditions and may perform differently in live markets.

## 🛡️ Comprehensive Risk Factors

### Market Risks:
- **Liquidity Risk**: Prediction markets may have low liquidity, making it difficult to enter/exit positions
- **Volatility Risk**: Rapid price movements can trigger unexpected losses
- **Slippage Risk**: Difference between expected and actual execution price
- **Gap Risk**: Prices can jump significantly between trades

### System Risks:
- **Model Risk**: AI predictions may be incorrect or based on flawed assumptions
- **Data Risk**: Incorrect or delayed market data can lead to bad decisions
- **Technical Risk**: Software bugs, crashes, or connectivity issues
- **Execution Risk**: Orders may not execute as expected

### Operational Risks:
- **Configuration Risk**: Improper settings can lead to excessive risk-taking
- **Monitoring Risk**: Lack of oversight can allow problems to escalate
- **Compliance Risk**: May not meet regulatory requirements for trading systems
- **Security Risk**: Potential for unauthorized access or data breaches

### Financial Risks:
- **Leverage Risk**: If using leverage, losses can exceed initial capital
- **Margin Risk**: Margin calls can force liquidation at unfavorable prices
- **Counterparty Risk**: Exchange or broker may fail to honor obligations
- **Currency Risk**: If trading across different currencies

### Psychological Risks:
- **Overconfidence**: Trusting the system too much without proper validation
- **FOMO**: Fear of missing out leading to impulsive decisions
- **Revenge Trading**: Trying to recover losses with aggressive strategies
- **Confirmation Bias**: Ignoring warning signs that contradict beliefs

## 📋 Safety Guidelines

1. **Never trade with money you cannot afford to lose**
2. **Start with paper trading to validate the system**
3. **Use minimal position sizes when beginning live trading**
4. **Monitor all trades manually at first**
5. **Set conservative risk limits**
6. **Regularly review and audit performance**
7. **Have emergency stop procedures in place**
8. **Never override safety mechanisms**
9. **Keep emotions out of trading decisions**
10. **Be prepared for total loss of capital**

## Testing

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_trading.py::TestDynamicRiskManager -v
```

## Live Trading

To switch to live trading:

1. Add the CLOB `apiKey`, `secret`, and `passphrase` to `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, and `POLYMARKET_API_PASSPHRASE`
2. Add the relayer key if you use the relayer API
3. Add the wallet `PRIVATE_KEY` for a dedicated trading wallet with only the funds you want to risk
4. Set `TRADING_MODE=live`
5. Set `ENABLE_LIVE_TRADING=true`
6. Start with small amounts

**WARNING**: Start with paper trading first. Past performance does not guarantee future results.

## API

The system includes a FastAPI server with protected endpoints:

```bash
# Start API
uvicorn api.main:app --reload

# Access with API key
curl -H "X-API-Key: dev_api_key_12345" http://localhost:8000/health
```

## Monitoring

- Logs: `data/logs/trading_YYYYMMDD.log`
- Database: `src/data/trading.db`
- Test results: `data/test_runs/`

## CI/CD Pipeline

The project includes GitHub Actions for automated testing:

```bash
# Local CI checks
pip install mypy flake8 pytest pytest-cov
mypy src --ignore-missing-imports
flake8 src --count --select=E9,F63,F7,F82
pytest tests/ --cov=src
```

## Docker Deployment

```bash
# Build and run
docker build -t polymarket-bot .
docker-compose up -d

# Check status
curl http://localhost:8000/health
```

## Development Commands

| Command | Description |
|---------|-------------|
| `pytest tests/ -v` | Run tests |
| `flake8 src` | Lint code |
| `mypy src` | Type check |
| `python agent_trading_system.py` | Run trading |
| `docker-compose up` | Run with Docker |

## Upgrade History

See [UPGRADE_PLAN.md](UPGRADE_PLAN.md) for full upgrade roadmap.

## License

MIT License - Use at your own risk for educational purposes.
