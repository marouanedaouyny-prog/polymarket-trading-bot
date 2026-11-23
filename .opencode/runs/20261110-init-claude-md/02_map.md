# MAP

## Touched
- `CLAUDE.md`: replace generic Ruflo configuration with repository-specific operating guidance.
- `.opencode/runs/20261110-init-claude-md/`: mandatory evidence ledger only.

## Entrypoints and data flow
- API: `entrypoint.py` -> `src.api.main` -> routers -> shared `src.api.state`.
- Trading: Gamma/CLOB connectors and market clients -> signal/strategy and ML scoring -> risk gates -> `OrderManager` -> paper ledger or live CLOB adapter.
- Standalone agent: `agent_trading_system.py` composes market client, predictor, dynamic risk, SQLite, optional MiroFish, and reporting.
- Persistence: SQLite under `src/data/trading.db`; models/metrics under `models/`; generated logs/results under `data/`.

## Conventions
- Environment-driven configuration in `src/utils/config.py`.
- Paper mode and sandbox defaults; real orders require explicit gates and a fresh readiness verdict.
- Tests live primarily in `tests/`; `pytest.ini` is the active pytest configuration.

## Blast radius
Documentation-only. No application API, trading logic, configuration default, generated data, or user worktree change is altered.
