# 🚀 Trading Bot Dashboard - Installation & Usage

## Quick Start (3 Steps)

### 1. Install API Dependencies
```bash
# Python backend
pip install -r requirements_api.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 3. Start Everything
```bash
# Option A: Run everything together
python run_system.py

# Option B: Run separately
# Terminal 1 - API backend
python api_server.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:3000/dashboard | Main trading UI |
| API Docs | http://localhost:8000/docs | Interactive Swagger docs |
| API Status | http://localhost:8000/api/status | System health check |
| WebSocket | ws://localhost:8000/ws | Real-time data stream |

## Features

### 📊 Real-Time Dashboard
- Live balance, P&L, win rate tracking
- Equity curve with Recharts
- Recent trades activity feed
- Win/loss distribution pie chart
- Category breakdown bar chart

### 📈 Market Monitor
- 50 live markets displayed
- YES/NO prices, volume, liquidity
- Edge and confidence scoring
- Category filters (Crypto, Politics, Tech, etc.)
- One-click trade execution

### 🎯 Trading Engine
- Automated trade generation
- Realistic win probability (edge-based)
- Position sizing (20% of balance)
- Fee calculation (7% Polymarket fee)
- Instant P&L updates

### ⚙️ Configuration
- Adjustable starting balance
- Start/pause/reset controls
- Real-time risk monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                      │
│  React Dashboard + Recharts + WebSocket + Axios            │
│                    http://localhost:3000                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API / WebSocket
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  Trading State • Market Generator • Trade Engine           │
│                    http://localhost:8000                    │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Markets** → Generated with realistic prices, volumes, edge scores
2. **Client** → Connects via WebSocket, receives updates every 2s
3. **Trades** → Auto-executed based on edge > 15% + confidence > 50%
4. **State** → Broadcast to all connected clients in real-time
5. **Charts** → Updated via polling (5s) + WebSocket events

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Current bot status |
| GET | `/api/markets?limit=50&category=Crypto` | Market opportunities |
| GET | `/api/trades?limit=20` | Recent trade history |
| GET | `/api/performance` | Performance metrics |
| GET | `/api/charts/equity` | Equity curve data |
| POST | `/api/trade/execute?market_id=...&position_size_pct=0.2` | Execute trade |
| POST | `/api/reset` | Reset account |
| POST | `/api/config?starting_balance=100` | Update config |
| WS | `/ws` | Real-time updates |

## Production Deployment

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t polymarket-api -f Dockerfile.api .
docker build -t polymarket-frontend -f Dockerfile.frontend .

docker run -p 8000:8000 polymarket-api
docker run -p 3000:3000 polymarket-frontend
```

### Environment Variables
```env
# .env file
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

## Customization

### Adjust Trading Behavior
Edit `api_server.py`:
- Line 160: `position_size_pct` - Position size as % of balance
- Line 167: `win_prob` formula - Adjust win probability
- Line 177: Update interval - Change market refresh rate

### Add Real Polymarket Data
Replace `generate_markets()` with actual API calls:
```python
from polymarket_client import PolymarketClient
client = PolymarketClient()
real_markets = client.get_markets(limit=50)
```

### Custom Styling
- Global CSS: `frontend/styles/globals.css`
- Tailwind classes throughout components
- Color scheme: cyan, emerald, amber, violet

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to API" | Start `api_server.py` first |
| "ModuleNotFoundError" | `pip install -r requirements_api.txt` |
| "npm install fails" | Use Node.js 18+ |
| "Port already in use" | Kill processes on 3000/8000, or change ports |
| "No markets showing" | Check browser console, API should return JSON |

## Next Steps

1. **Connect Real Polymarket API**
   - Replace market generator with live API
   - Use actual order placement endpoints
   - Implement authentication

2. **Add Database Persistence**
   - Store trades in PostgreSQL/SQLite
   - Historical performance analysis
   - Position tracking

3. **Enhanced Risk Management**
   - Daily loss limits
   - Position correlation check
   - Stop-loss automation

4. **Advanced Analytics**
   - Sharpe/Sortino ratios
   - Win streak tracking
   - Sector performance breakdown

5. **User Management**
   - API key auth
   - Multi-user support
   - Trade history per user

## License

MIT - Use at your own risk. Not financial advice.
