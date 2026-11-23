# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Use Python 3.11 (the CI and container version). Run commands from the repository root.

```bash
# Install runtime and CI/development dependencies
python -m pip install -r requirements.txt
python -m pip install mypy flake8 black isort pytest pytest-cov pytest-asyncio

# Run the FastAPI service (FASTAPI_API_KEY is required at import time)
FASTAPI_API_KEY=dev-key python entrypoint.py
# Windows PowerShell: $env:FASTAPI_API_KEY='dev-key'; python entrypoint.py

# Run the finite synthetic paper-trading loop
python -m src.polymarket_bot.scripts.run_paper

# Build/syntax smoke check
python -m compileall -q src entrypoint.py agent_trading_system.py

# Tests
python -m pytest tests
python -m pytest tests/test_integration_pipeline.py::TestFilterRiskOrderPipeline::test_full_buy_sell_pnl_flow
python -m pytest tests --cov=src --cov-report=term-missing

# CI checks
python -m flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
python -m mypy src/utils/config.py src/utils/logger.py --ignore-missing-imports
python -m black --check src
python -m isort --check src
python -m flake8 src --max-line-length=120

# Container
docker build -t polymarket-bot .
docker compose up
```

`pytest.ini` is the active pytest configuration; it overrides the pytest table in `pyproject.toml`. Some older tests call the public Polymarket API and can be slow or network-dependent; prefer focused mocked tests while iterating, then run the full suite.

## Architecture

This repository has two primary runtime entrypoints:

- `entrypoint.py` imports `src.api.main:app` and starts Uvicorn on port 7860. `src/api/main.py` owns middleware, API-key authentication, startup safety checks, and router registration. Routers under `src/api/routers/` use process-local managers from `src/api/state.py`.
- `agent_trading_system.py` is the standalone orchestration path. `TradingAgentSystem` composes the market client, calibrated predictor, dynamic risk manager, SQLite persistence, paper ledger, optional MiroFish intelligence, and session reporting.

The core trading flow is:

1. `src/data/` fetches and normalizes Gamma/CLOB market data and stores price history/state.
2. `src/trading/signal_filter.py`, `src/trading/strategies.py`, and `src/ml/` filter markets and produce model/strategy signals. Untrained `MarketPredictor` falls back to market price rather than inventing confidence.
3. `src/risk/` enforces position, drawdown, daily-loss, and kill-switch limits.
4. `src/execution/order_manager.py` tracks orders, fills, positions, and realized P&L. Paper mode simulates fills; live mode delegates to `src/execution/clob_adapter.py` only after all safety gates pass.
5. Runtime artifacts are written under `data/` and `models/`; SQLite persistence is initialized by `src/data/sqlite_db.py`.

The tree also contains parallel/legacy implementations (`legacy/`, older `src/core/`, `src/polymarket_bot/`, and duplicate storage/risk modules). Before changing one, trace imports from the active entrypoint or router and update callers/tests for the wired implementation only.

## Configuration and Safety Invariants

- `src/utils/config.py` is the central trading configuration. Process environment variables take precedence; it then loads `config/.env`, falling back to root `.env`.
- Paper/sandbox behavior is the default. Do not weaken the live-order gates: live execution requires `TRADING_MODE=live`, `ENABLE_LIVE_TRADING=true`, `POLYMARKET_ALLOW_REAL_ORDERS=true`, all credentials, an available CLOB adapter, and a fresh passing `data/readiness_verdict.json` from `python scripts/tools/readiness_check.py --json data/readiness_verdict.json`.
- The API fails at import when `FASTAPI_API_KEY` is missing. Protected routes require the `X-API-Key` header; health/docs/dashboard routes are public.
- Treat model metrics as evidence, not guaranteed performance. Preserve chronological validation, calibration checks, leakage rejection, and fail-closed fallbacks in money paths.

## Repository Conventions

- Keep changes minimal and validate inputs at API, connector, and execution boundaries.
- Read files before editing. Keep source files under 500 lines where practical; do not place new scripts, tests, or generated output at repository root—use `scripts/`, `tests/`, `src/`, `config/`, or `docs/`.
- Do not rewrite generated trading data, model artifacts, or the user's unrelated worktree changes unless the task explicitly requires it.
- After code changes, run the narrowest affected test first, then the full applicable CI checks above.
