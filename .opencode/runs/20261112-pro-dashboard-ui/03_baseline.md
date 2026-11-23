# S3 BASELINE — pre-change verification (all pass)

- `python -m compileall -q src entrypoint.py agent_trading_system.py` → exit 0, no output (all modules parse).
- `python -m pytest tests/test_integration_pipeline.py::TestFilterRiskOrderPipeline::test_full_buy_sell_pnl_flow -q` → 1 passed, exit 0 (8.08s).
- `python -m flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` → 0 errors (clean).
- `python -m mypy src/utils/config.py src/utils/logger.py --ignore-missing-imports` → "Success: no issues found in 2 source files".
- `python -m black --check src` → 105 files would be reformatted, ALL pre-existing Python files I did NOT touch (black doesn't cover HTML). Minimal-diff rule: not reformatting unrelated code.
- `python -m isort --check src` → errors only in pre-existing Python files I did NOT touch (incl. encoding warnings on → chars). Not my change.

Baseline established: the codebase was green (modulo pre-existing unrelated black/isort/network-test noise) before my single HTML change.
