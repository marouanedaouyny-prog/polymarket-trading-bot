# Project Improvement Requirements

Current rating: **6.2 / 10**
Target rating: **8.5 / 10**

---

## P0 — Critical (blocks real trading)

### 1. Fix the ML model (4/10 → 7/10)
- [ ] Remove circular features: `edge` is derived from `price`, so the model is partially fitting tautologies
- [ ] Add genuinely predictive features: days-to-close, market category, recent price velocity, liquidity depth, social sentiment score
- [ ] Train on a proper time-split (train on T-90d, validate on T-30d, test on T-0) — never shuffle prediction markets because future leaks into past
- [ ] Replace LogisticRegression with a calibrated model (e.g. `CalibratedClassifierCV` wrapping GradientBoosting) so probabilities are trustworthy
- [ ] Log feature importance so you can audit what the model is actually learning
- [ ] Target: Brier score < 0.15 on held-out future markets

### 2. Fix the backtest engine position tracking (5/10 → 7/10)
- [ ] Track open positions separately from closed ones — currently every `buy` is counted as a "loss" and every `sell` as a "win"
- [ ] Implement a proper P&L calculation: `(sell_price - buy_price) * amount - fees`
- [ ] Add slippage model tied to order size vs. available liquidity (not a flat percentage)
- [ ] Load real historical resolved market data into `src/backtesting/data/` so the engine has something to run on

### 3. Remove `keys.txt` from the repo
- [ ] Delete `keys.txt` from root immediately — it likely contains real credentials
- [ ] Add `keys.txt` to `.gitignore`
- [ ] Rotate any credentials that were in it

---

## P1 — High priority (significant quality improvements)

### 4. Fix the 5 failing tests
- [ ] `TestConfig::test_config_starting_balance` — config value drifted; pin test to env-variable defaults not hardcoded numbers
- [ ] `TestConfig::test_config_max_position_pct` — same issue
- [ ] `TestSecurityFixes::test_input_validation` — assertion is `0 == 1`, test logic is wrong
- [ ] `TestRiskManagementEnhancements::test_slippage_simulation` — add the missing `_log_execution` method or remove the test
- [ ] `TestIntegrationSafety::test_configuration_safety` — export `TradingConfig` from `src.utils.config`

### 5. Clean up root directory
- [ ] Move all loose diagnostic scripts (`diagnose_markets.py`, `deep_diagnostic.py`, `reality_check.py`, `debug_market_ids.py`, etc.) into `scripts/tools/`
- [ ] Delete or archive dead files: `127` (empty file), `live_sim_50.py`, `auto_learning_flywheel.py`
- [ ] Root should contain only: `agent_trading_system.py`, `README.md`, config files, Docker files

### 6. Strategy layer — real price history
- [ ] Fetch and cache per-market price history from the Gamma API (`/markets/{id}/prices-history`)
- [ ] Store as time-series in SQLite so indicators (RSI, MACD) compute on real data instead of synthetic flat arrays
- [ ] Without real history, `MomentumStrategy` and `MeanReversionStrategy` will always return flat signals

### 7. Order execution — partial fills & reconciliation
- [ ] Handle partial fills: track `filled_amount` vs `requested_amount` on each order
- [ ] Add order status polling loop in `OrderManager` for live mode
- [ ] Implement position reconciliation: on startup, fetch open positions from CLOB and sync with local state

---

## P2 — Medium priority (robustness & observability)

### 8. Add a proper metrics dashboard
- [ ] Prometheus metrics already configured (`config/prometheus.yml`) but nothing exposes them
- [ ] Expose via FastAPI `/metrics` endpoint: current balance, open positions, daily P&L, win rate, drawdown
- [ ] Wire Grafana dashboard (`config/grafana/`) with those metrics

### 9. Duplicate code — consolidate trading bots
- [ ] There are 4+ independent implementations of "paper trading bot" across `scripts/bots/`, `bots/`, `src/trading/`
- [ ] Pick one (`src/trading/paper_trading.py`) as canonical and delete the rest
- [ ] All scripts should call the canonical implementation, not reimplement it

### 10. Add integration tests
- [ ] Mock the Gamma API with `pytest-httpx` or `responses` library
- [ ] Test the full path: `filter_markets → score_markets → DynamicRiskManager.calculate_position → OrderManager.place_order`
- [ ] Add a test that runs the backtest engine end-to-end with a synthetic dataset

### 11. API security hardening
- [ ] Replace hardcoded `dev_api_key_12345` with a secret loaded from env
- [ ] Add rate limiting per IP (e.g. `slowapi`)
- [ ] Add request logging middleware with redacted sensitive fields

---

## P3 — Nice to have (polish)

### 12. Type completeness
- [ ] Add `py.typed` marker and run `mypy --strict` on `src/`
- [ ] Currently mypy passes with `--ignore-missing-imports` only — too lenient

### 13. Async execution pipeline
- [ ] `signal_filter.py` fetches markets synchronously — switch to `httpx.AsyncClient` so the API server doesn't block
- [ ] `OrderManager.place_order` blocks on simulated latency with `time.sleep` — use `asyncio.sleep`

### 14. Strategy evaluation with real outcomes
- [ ] After a market resolves, log the signal that was generated vs. the actual outcome
- [ ] Build a signal accuracy table: per-strategy win rate over last 30/60/90 days
- [ ] Use this to weight the `evaluate_all()` consensus (higher weight to strategies with better recent accuracy)

---

## Success Criteria

| Metric | Current | Target |
|---|---|---|
| Test pass rate | 95.9% (116/121) | 100% (all fixed) |
| ML Brier score | unknown | < 0.15 |
| Backtest P&L accuracy | broken | matches manual calculation |
| Root directory files | 30+ loose scripts | < 10 |
| Failing security checks | 3 | 0 |
| Live trading readiness | paper only | validated on 200+ paper trades |
