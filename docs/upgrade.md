# Upgrade Plan – Making Polymarket AI Trading System Future‑Proof

## 1. Persistent Market Data Store
- **Problem** – `DataIngestionPipeline` only keeps data in‑memory, losing it on crash/restart.
- **Solution** – Implement a lightweight SQLite storage (`src/data/storage/sqlite_db.py`) and have the pipeline write each fetched market to the DB and read recent rows on startup.

## 2. Robust Configuration & Secrets
- **Problem** – API keys accessed directly via `os.getenv` scattered throughout the code.
- **Solution** – Centralise env loading in `src/utils/config.py` (loads `.env` from `config/`). Import `POLYMARKET_API_KEY` and `FASTAPI_API_KEY` where needed (e.g., `PolymarketClient`, FastAPI auth).

## 3. Secure FastAPI Access
- **Problem** – API endpoints were publicly exposed.
- **Solution** – Add an API‑key dependency (`_require_api_key`) on `/markets` and `/opportunities` in `main.py`. Require `X‑API‑Key` header matching `FASTAPI_API_KEY`.

## 4. Unified Logging
- **Problem** – Numerous `print` statements produce noisy output and are hard to monitor.
- **Solution** – Use the shared logger (`src/utils/logger.py`) throughout the project. Replace remaining `print` calls with `logger.info` / `logger.error`.

## 5. Real Machine‑Learning Model
- **Problem** – `MarketPredictor` used a random weight matrix; predictions were meaningless.
- **Solution** – Replace with a scikit‑learn `LogisticRegression` trained on engineered features. Persist the model with `pickle` and load it at runtime.

## 6. Test Coverage
- **Problem** – Core components lack automated tests.
- **Solution** – Add pytest‑asyncio tests for `ArbitrageScanner` (already added), plus unit tests for `RiskManager`, `PortfolioRebalancer`, `DataIngestionPipeline`, and the new SQLite storage. Aim for ≥80% coverage.

## 7. Type‑Checking & Linting
- **Problem** – Missing type hints can hide bugs.
- **Solution** – Run `mypy .` and `flake8`. Add type hints to all functions/classes lacking them. Include a `pyproject.toml` or `setup.cfg` with linting config.

## 8. CI/CD Pipeline
- **Problem** – No automated verification on push.
- **Solution** – Create GitHub Actions workflow (`.github/workflows/ci.yml`) that:
  1. Installs `requirements.txt`.
  2. Runs `mypy` and `flake8`.
  3. Executes `pytest --cov=src`.
  4. (Optional) Builds a Docker image and pushes to a registry.

## 9. Dockerisation
- **Problem** – Manual setup on new machines is error‑prone.
- **Solution** – Write a `Dockerfile` that copies the repo, installs dependencies, sets required env vars, and runs `uvicorn main:app`. Provide a `docker-compose.yml` that also starts a Redis container if needed.

## 10. Enhanced Risk & Position Management
- **Problem** – `RiskManager` only checks static limits.
- **Solution** – Add dynamic risk metrics:
  - Real‑time drawdown tracking (peak‑to‑trough).
  - Volatility‑adjusted position sizing (e.g., Kelly criterion).
  - Adaptive daily loss limit that tightens after consecutive losses.

## 11. Reliable Order Execution
- **Problem** – `ExecutionManager.place_order` only simulates orders.
- **Solution** – Integrate a real exchange SDK or REST API, add retry with exponential back‑off, and store order results in SQLite for audit.

## 12. Monitoring & Alerting
- **Problem** – No observability of system health.
- **Solution** – Export Prometheus metrics (`src/monitoring/metrics.py`) and set up alerts for:
  - Excessive drawdown.
  - Order placement failures.
  - API latency spikes.

## 13. Documentation
- **Problem** – README is outdated.
- **Solution** – Update `README.md` with architecture diagram, setup steps (env, Docker, CI), how to run tests, and a link to this upgrade plan.

## 14. Upgrade Execution Order
1. Add SQLite storage (`sqlite_db.py`) and integrate it into `data_pipeline.py`.
2. Consolidate configuration (`src/utils/config.py`) and replace direct `os.getenv` usage.
3. Verify FastAPI API‑key protection works.
4. Ensure all modules use the shared logger.
5. Replace placeholder ML model with `LogisticRegression`.
6. Expand test suite and run them.
7. Run `mypy`/`flake8` and fix any type errors.
8. Add CI workflow and Docker files.
9. Implement dynamic risk management features.
10. Hook up real order execution and monitoring.

Following this roadmap will make the system resilient to crashes, secure, well‑tested, and ready for production‑grade trading.
