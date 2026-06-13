# Complete Steps to Run the Polymarket Trading Bot Project

## System Requirements

### 1. Software Requirements

- **Python 3.8 or higher**
- **Required Python packages:**
  - `aiohttp` - for API requests
  - `fastapi` - for the web API
  - `websockets` - for real-time data streaming
  - `asyncpg` - for PostgreSQL database connections
  - `redis` - for caching
  - `pydantic` - for data validation
  - `uvicorn` - for running the API server

### 2. External Services

#### Database Services Required:
- **PostgreSQL** (version 12 or higher)
- **Redis** (version 5.0 or higher)

#### API Access Required:
- **Polymarket API key** and secret from your Polymarket developer account

## Installation Steps

### Step 1: Install Python Dependencies

```bash
# Navigate to the project directory
cd polymarket

# Install required packages
pip install -r src/polymarket_bot/requirements.txt
```

### Step 2: Set Up Database Services

#### Option A: Using Docker (Recommended)

```bash
# Start PostgreSQL database
docker run --name polymarket-postgres \
    -e POSTGRES_DB=polymarket_trading \
    -e POSTGRES_USER=trader \
    -e POSTGRES_PASSWORD=secret123 \
    -p 5432:5432 \
    -d postgres:13

# Start Redis
docker run --name polymarket-redis \
    -p 6379:6379 \
    -d redis:alpine
```

#### Option B: Local Installation

1. **Install PostgreSQL:**
   - **Windows:** Download from https://www.postgresql.org/download/windows/
   - **macOS:** `brew install postgresql`
   - **Linux:** `sudo apt-get install postgresql`

2. **Install Redis:**
   - **Windows:** Download from https://redis.io/download/
   - **mac3. **Linux:** `sudo apt-get install redis-server`

### Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp src/polymarket_bot/.env.example .env
   ```

2. Update `.env` with your actual values:
   ```env
   POLYMARKET_API_KEY=your_actual_api_key_here
   POLYMARKET_API_SECRET=your_actual_api_secret_here
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
   ```

### Step 4: Database Setup

Create the required database and user in PostgreSQL:

```sql
CREATE DATABASE polymarket_trading;
CREATE USER trader WITH PASSWORD 'secret123';
GRANT ALL PRIVILEGES ON DATABASE polymarket_trading TO trader;
```

### Step 5: Verify Setup

```bash
python verify_setup.py
```

### Step 6: Run Unit Tests

```bash
cd src/polymarket_bot
python -m pytest tests/
```

### Step 7: Test Individual Components

```bash
python test_market_making.py
python test_spread_optimizer.py
python test_market_making_components.py
```

### Step 8: Start the API Server

```bash
# Navigate to the API directory and start the server
cd src/polymarket_bot
uvicorn api.main:app --reload
```

Or run the main application:
```bash
python src/polymarket_bot/main.py
```

### Step 9: Access the API

1. Start the server:
   ```bash
   uvicorn src.polymarket_bot.api.main:app --reload
   ```

2. Visit `http://localhost:8000` to see the API documentation
3. Test endpoints like:
   - `http://localhost:8000/health`
   - `http://localhost:8000/markets`
   - `http://localhost:8000/performance`

### Step 10: Run Paper Trading

Before going live, test with paper trading:

```bash
python src/polymarket_bot/scripts/run_paper.py
```

### Step 11: Monitor the System

1. Check the performance dashboard at the `/performance` endpoint
2. Monitor PnL, fill rates, and other metrics
3. Verify all risk controls are working properly

### Step 12: Production Deployment

1. **Final testing:**
   - Run full system tests
   - Verify all risk controls work
   - Check all API endpoints

2. **Go live:**
   ```bash
   # required safety gate
   # ENABLE_LIVE_TRADING=true in .env
   python src/polymarket_bot/scripts/run_live.py
   ```

## Running the Complete System

### Development Mode:
```bash
# Start the API server
uvicorn src.polymarket_bot.api.main:app --reload

# In another terminal, run the main bot
python src/polymarket_bot/main.py
```

### Production Mode:
```bash
# Using Docker
cd src/polymarket_bot/docker
docker-compose up
```

## Troubleshooting

### Common Issues:

1. **Database Connection Errors:**
   - Ensure PostgreSQL and Redis are running
   - Check connection parameters in `.env` file
   - Verify database user permissions

2. **API Key Issues:**
   - Verify your Polymarket API credentials
   - Check if your API key has the correct permissions

3. **Missing Dependencies:**
   - Run `pip install -r requirements.txt` to install all packages

## Testing the Implementation

1. **Run all tests:**
   ```bash
   cd src/polymarket_bot
   python -m pytest tests/
   ```

2. **Test individual components:**
   ```bash
   python test_market_making.py
   python test_spread_optimizer.py
   python test_market_making_components.py
   ```

3. **Run the setup verification:**
   ```bash
   python verify_setup.py
   ```

## Monitoring and Maintenance

1. **Set up monitoring:**
   - Check `src/polymarket_bot/telemetry/metrics.py` for monitoring configuration
   - Configure alerting system for system health

2. **Check system health:**
   - Monitor the performance dashboard
   - Check PnL, fill rates, and other metrics regularly

3. **Regular maintenance:**
   - Keep dependencies updated
   - Monitor API rate limits
   - Ensure database backups are configured
