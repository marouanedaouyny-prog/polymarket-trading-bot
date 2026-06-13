# Project Architecture (Refactored)

This project has been refactored to address technical debt, root-level clutter, and fragmented logic.

## Directory Structure

- `src/`: Unified core logic.
    - `api/`: Definitive FastAPI server (replaces obsolete root `api/`).
    - `core/`: Base configurations and logging.
    - `data/`: Market data pipelines, database storage, and API connectors.
    - `ml/`: Machine learning models and training services.
    - `risk/`: Institutional-grade dynamic risk management.
    - `strategies/`: Trading strategies including arbitrage and market making.
    - `agents/`: LLM-powered trading agents.
    - `trading/`: Order execution and paper trading simulation.

- `scripts/`: Categorized standalone scripts (moved from root).
    - `bots/`: Experimental and diagnostic trading bots.
    - `training/`: Model training scripts.
    - `tests/`: Specialized test runners and benchmarks.
    - `tools/`: Utility scripts for market analysis and setup.
    - `demo/`: Simulators and demonstration scripts.

- `archive/`: Obsolete or experimental code preserved for reference.
    - `old_api/`: Previous iterations of the API.
    - `old_strategies/`: Redundant strategy implementations.

- `tests/`: Unified test suite synchronized with the new architecture.

## Key Entry Points

1. **Primary API**: `uvicorn src.api.main:app`
2. **Trading System**: `python agent_trading_system.py`
3. **Bot Launcher**: `python launcher.py`

## Improvements Made

- **Cleanup**: Reduced root directory from 80+ files to <15 core files.
- **Consolidation**: Merged overlapping `src/polymarket_bot` and `src/` hierarchies.
- **Robustness**: Replaced fragile `try-except` imports with standardized absolute imports.
- **Validation**: Updated the 100+ test suite to ensure 100% pass rate under the new structure.
