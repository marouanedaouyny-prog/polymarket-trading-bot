# RESEARCH

1. **Commands** -> checked `.github/workflows/ci.yml:30-77`, `requirements.txt:38-49`, `pytest.ini:1-17`, `entrypoint.py:7-15`, `Dockerfile:38-44` -> Python install/test/lint/type/format/API commands are authoritative; there is no npm build in the verified path -> verified with compile, mypy, and single-test runs.
2. **Runtime architecture** -> checked `src/api/main.py:268-279`, `src/api/state.py:18-21,91-100`, `src/api/routers/trades.py:84-175`, `src/trading/signal_filter.py:138-294`, `agent_trading_system.py:256-389` -> API and standalone-agent entrypoints compose data, scoring, risk, execution, and persistence layers -> verified by import tracing.
3. **Safety** -> checked `src/execution/order_manager.py:35-60`, `src/utils/readiness_gate.py:32-70`, `src/api/main.py:88-110` -> live orders fail closed unless explicit flags, credentials, adapter, and fresh verdict are present -> verified by `tests/test_readiness_gate.py:1-80` anchors.
4. **Foreign configs** -> existence checks found `~/.codex/config.toml` and `~/.gemini/settings.json`; contents intentionally not read -> offer `/import` per init contract.
