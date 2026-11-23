# BASELINE

Observed before editing `CLAUDE.md`:

- `python -m compileall -q src entrypoint.py agent_trading_system.py` -> exit 0 (`03_compile.log`).
- `python -m mypy src/utils/config.py src/utils/logger.py --ignore-missing-imports` -> `Success: no issues found in 2 source files`, exit 0 (`03_mypy.log`).
- `python -m black --check src` -> unavailable: `No module named black`, exit 1 (`03_black.log`).
- `python -m isort --check src` -> unavailable: `No module named isort`, exit 1 (`03_isort.log`).
- `python -m flake8 ...` -> unavailable: `No module named flake8` (observed tool output).
- `python -m pytest tests/test_integration_pipeline.py::TestFilterRiskOrderPipeline::test_full_buy_sell_pnl_flow -q` -> 1 passed in 10.09s (observed tool output).
- `python -m pytest tests -q` collected 138 tests and passed through 33% before exceeding the 600-second foreground window; it continued as background task `bpebgepkh` (observed tool output).

Baseline consequence: document CI commands exactly, including installing `mypy flake8 black isort pytest pytest-cov pytest-asyncio`; do not claim the current environment has every dev tool installed.
