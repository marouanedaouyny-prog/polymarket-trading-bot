# HONEST EXPECTATIONS — Read Before Depositing Any Money

## What This Project Actually Is

This is a **paper trading research tool** built around Polymarket's public API.
It can browse real markets, simulate trades, and track results.

It does **not** have a proven trading strategy. The "78–88% win rate" claims
in earlier docs came from simulations where the outcome was randomly generated
using hardcoded bias tables — not from real market results. Those numbers have
been removed from the codebase.

---

## If You Add $20 — Honest Scenarios

### Most Likely: You Lose It

Prediction markets are efficient. The prices already reflect the crowd's best
estimate of probability. Buying a "YES" at $0.10 means the market thinks
there is a ~10% chance. The bot has no special information the market doesn't.

Without a real statistical edge — proven on hundreds of live trades — the
expected outcome is:

| Timeframe | Expected Result |
|-----------|----------------|
| 1 week    | Small loss from trading fees |
| 1 month   | ~50% chance you lose most of it |
| 3 months  | High probability of losing the full $20 |

**$20 lost is the most likely outcome.**

### Best Realistic Case: Break-even or Small Gain

If you manually pick markets you have genuine knowledge about
(e.g. a political event you follow closely, a sports result you track),
you *might* edge out a small profit. But the bot itself does not do this —
it filters by price/volume only, which is not an edge.

### The Impossible Case: "Consistent Profits"

No bot betting on public prediction markets with $20 will return
consistent profits without a proven, validated strategy. Anyone claiming
otherwise is selling something.

---

## What You Should Actually Do

### Step 1 — Security (Do This NOW)
1. Go to [polymarket.com/profile](https://polymarket.com/profile)
2. **Revoke every API key** that was in `keys.txt` and `.env` — they were exposed
3. If your wallet had real USDC, check it and move funds to a fresh wallet
4. Generate new keys only when you are ready to trade

### Step 2 — Paper Trade First (2+ weeks)
```bash
# Keep TRADING_MODE=paper in config/.env
python agent_trading_system.py
```

Watch the signal filter find real markets:
```bash
python src/trading/signal_filter.py
```

Track whether the markets it *would* trade actually resolve correctly.
Do this for at least 50 simulated trades before touching real money.

### Step 3 — Build Real Training Data
```bash
python scripts/tools/fetch_resolved.py   # downloads real resolved markets
python src/ml/market_predictor.py        # trains model on actual outcomes
```

Only after you have real outcome data can the ML model have any meaning.

### Step 4 — If Live Trading, Start Tiny
- Minimum: $20 (understood to be at risk of total loss)
- Max per trade: 5% = $1.00
- Max per day: 3 trades
- These limits are already set in `config/.env`

---

## What Was Fixed in This Repo

| Issue | Fix Applied |
|-------|-------------|
| Real API keys in `.env` and `keys.txt` | Wiped — replace with fresh keys |
| Hardcoded fake win rates (96%, 93%, 89%…) | Replaced with honest market-implied probability |
| Training data using fabricated outcomes | Now reads real resolved market JSON |
| No live market browsing | `src/trading/signal_filter.py` added |
| `TRADING_MODE` defaulted unsafely | Locked to `paper` in both env files |

---

## Bottom Line

This project is a useful **learning tool and paper trading framework**.
It is not a money-making machine. The code architecture is reasonable.
The trading edge is not proven.

If you enjoy prediction markets and want to learn how automated trading
systems work — this is a good project to study and improve.

If you are hoping to grow $20 into significant money — that is not what
this project can do in its current state.
