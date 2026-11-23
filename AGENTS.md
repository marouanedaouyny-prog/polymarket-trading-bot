# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

Autonomous trading bot for Polymarket prediction markets: hierarchical agents (Lead → Research → Risk → Trader → Monitor), ML predictions, Kelly/drawdown risk, SQLite persistence, FastAPI service.

## Environment

- **Python 3.11** — Docker uses `python:3.11-slim` and `requirements.txt` deps (`timesfm[torch]`, `lightgbm`) are unreliable on newer interpreters.
- **Use `.venv311`.** The original `.venv` / `.venv312` are unusable: `.venv` has no packages, and `.venv312`'s base interpreter (`AppData\...\Python312`) no longer exists, so its `python.exe` fails with "Permission denied" / "cannot execute". `.venv311` (Python 3.11.15) has sklearn 1.9.1, pandas, requests, pytest and torch; the system `C:\Python314\python` also runs the stack (torch 2.10.0+cpu) after installing `requests` and `pytest`.
- **Windows**: `python3` is a Microsoft Store stub that errors; `python` is 3.14.x; `py -3.11` reports "No suitable Python runtime found" even though `py -0` lists a 3.11 entry. Point the venv at a real 3.11 binary explicitly.
- **Install**: `pip install -r requirements.txt`, not `pip install -e .`. `pyproject.toml` lists `sqlite3` as a dependency (not a PyPI package), so editable install fails. Install needs network because `autopredict` comes from GitHub.
- **Tests require `FASTAPI_API_KEY` in the shell.** `src/api/main.py` raises `ValueError` at import time and `tests/test_security_fixes.py` imports it at module level; `main.py` loads only the root `.env`, which does not define it.
- **Env precedence**: `src/utils/config.py` loads `config/.env` with `override=False`, so exported shell variables win. `src/api/main.py` loads only the root `.env`, without override. The two files hold different keys, so check which entry point you are in.
- **The ML model only reproduces the market price.** Retrained on real entry-time prices (`data/training/entry_price_dataset_v3.json`, 1,321 markets, sampled 7 days before `closedTime`; v2 has 1,252): `models/metrics.json` reports Brier `0.1186` / AUC `0.9316` on a random split, which *looks* like it beats the 0.15 target. It does not: the raw price baseline scores Brier `0.1192` / AUC `0.9321` on the same rows. Walk-forward out-of-sample Brier is `0.1515` for the model versus `0.1377` for price alone, and the net return of the model-selected trades (`+29.6%` over 30 rows) matches the return of simply buying every in-range market (`+30.2%` over 442 rows). There is no informational edge. The leakage guard in `MarketPredictor` rejects any saved model with AUC ≥ 0.999 or Brier ≤ 0.001; fix the data, not the guard.
- **Momentum is not a usable feature.** `scripts/tools/analyze_velocity_feature.py` trains with the real 24h `price_velocity` versus forcing it to 0: OOS Brier `0.1542` with momentum vs `0.1535` without, both worse than price (`0.1377`). Correlation between momentum and the outcome-minus-price residual is `-0.044`. Do not wire `oneDayPriceChange` into inference expecting an edge.
- **Order flow is not a usable feature either.** `scripts/tools/fetch_order_flow.py` pulls pre-entry fills from the Data API v2 feed (`https://data-api.polymarket.com/v2/trades`) and `scripts/tools/analyze_order_flow_feature.py` scores them walk-forward: price `0.1504`, price+base features `0.1542`, price+base+24h flow `0.1569`; the month-clustered 95% CI on the delta is `[-0.0111, +0.0206]`. Correlation of YES-flow, big-trade flow and trade-VWAP gap with the outcome-minus-price residual is `+0.007`, `-0.045`, `-0.026`. Adding flow makes the model slightly worse.
- **`timestamp` in the entry datasets is `closedTime`, not entry time.** `build_entry_dataset.py` samples the price at `closedTime - 7d` but stores `closedTime` in `timestamp`. Any feature that windows on "entry" must subtract 7 days first — using `timestamp` directly pulls the final 24h before resolution and produces a fake Brier near `0.03`.
- **The Data API v2 `start`/`end` filters are ignored on the market shape.** `/v2/trades?condition=...&start=...&end=...` returns the same page as no filter; only the `user` shape honors the window, and `/v2/activity` requires `user`. Historical flow must be paged backwards with `cursor`. Coverage starts around 2025; pre-2025 markets return zero rows.
- **The 5–10¢ longshot band is suggestive but not significant.** Over 1,321 markets, buying YES at 0.05–0.10 returning to resolution gives `+127%` per trade (n=136, naive t=2.88), but quarterly-clustered t is `1.96` (10 clusters) and 3 of 10 quarters are negative, two at `-100%`. Treat it as an untested hypothesis, not an edge.
- **Headline "profit" from the walk-forward is one longshot, not a strategy.** Over 1,052 out-of-sample candidates (2025-09 → 2026-11) only 5 trades ever execute: 2 wins, 3 losses, `+$8.64` on $20 (`+43%`). Remove the single 7.5¢ Netherlands election win (13.3× payout) and the run is negative. All 5 trades fall in a 2.5-week window; the 25 later research-passing candidates return `-3.2%`.
- **The bot cannot produce 50 trades on this data.** Of 1,052 OOS candidates: 610 fail the price cap, 910 fail confidence, 616 fail EV, 776 fail edge; only 30 pass research, and the risk layer then rejects 24 of those (`min_confidence` is 85 inside `DynamicRiskManager._DEFAULTS` but 70 in `config/.env`). Effective throughput is ~5 trades per 13.5 months, so 50 trades needs ~11 years of history.
- **`DynamicRiskManager.reset_daily()` is dead code.** It is defined at `src/risk/dynamic_risk.py:394` and never called by `agent_trading_system.py` or the API. Once the daily-loss limit trips, every later entry is refused until the process restarts.
- **Never re-introduce post-resolution price as a feature.** `scripts/tools/fetch_resolved.py` stores the final `yes_price`, which is the label. Use `scripts/tools/build_entry_dataset.py` (CLOB `prices-history` sampled before close) instead.
- **Trade accounting is side-aware.** `TraderAgent` buys YES when `win_prob >= price`, otherwise NO, and settles PnL on the entry price of the side actually bought. Do not revert to the old YES-only PnL formula.
- **$20 cannot support 50 trades.** With `MIN_BET=1.0` and `MAX_POSITION_PCT=0.05`, `RiskAgent` requires a balance of at least `min_bet / max_position_pct = $20`. One loss takes the balance to $19 and every later trade is rejected with "Balance too low".

## Commands

| Task | Command |
|------|---------|
| Tests | `pytest tests/ -v` |
| Single test | `pytest tests/test_trading.py::TestRiskManager::test_name -v` |
| Type check | `mypy src/utils/config.py src/utils/logger.py --ignore-missing-imports` (what CI actually runs; a bare `mypy src` is noisy) |
| Lint | `flake8 src --max-line-length=120` (CI gate is only `--select=E9,F63,F7,F82`) |
| Format check | `black --check src && isort --check src` (advisory in CI) |
| Paper trading | `python agent_trading_system.py` |
| API (local) | `uvicorn src.api.main:app --port 8000` |
| API (Docker/HF) | `python entrypoint.py` (serves `$PORT`, default 7860) |
| Full stack | `docker-compose up`; `docker compose --profile full up` adds Postgres, Prometheus, Grafana |

**Always run `pytest tests/`, never `pytest .`** — root-level `test_100_trades.py`, `test_mocked_sim.py`, `test_simulation.py` plus `simulate.py`, `trusted_run.py`, `high_win_rate_sim.py`, `ultra_high_win_rate.py` are throwaway simulations, not pytest tests, and are unmaintained.

## Configuration and security

- `src/utils/config.py` is the single source of truth for settings; `src/core/config.py` is a re-export shim. Never hardcode thresholds — read them from config.
- **Trust `src/utils/config.py` and `config/.env` over `README.md`.** The README's `MIN_EDGE` / `MIN_CONFIDENCE` values are stale (code defaults 0.08 / 85; local `.env` 0.08 / 70).
- **Live orders need three independent switches in three files**: `TRADING_MODE`, `ENABLE_LIVE_TRADING` (`src/utils/config.py`), and `POLYMARKET_ALLOW_REAL_ORDERS` (`src/execution/order_manager.py`). `POLYMARKET_SANDBOX` defaults `true`. Docs mentioning only two flags are incomplete. Keep paper mode the default for any change.
- **Live mode is additionally gated by a readiness verdict.** `OrderManager` builds the CLOB adapter only if `data/readiness_verdict.json` has `passed: true` and a `checked_at` under 7 days old (`src/utils/readiness_gate.py`). Generate it with `python scripts/tools/readiness_check.py --json data/readiness_verdict.json`; the current verdict fails 5 checks, so live orders are blocked end-to-end. The gate is fail-closed, paper mode is unaffected, and the file is a generated artifact (do not commit it). `READINESS_VERDICT_PATH` overrides the path; `tests/test_readiness_gate.py` covers missing/failing/stale/future verdicts plus both OrderManager modes.
- **Never print, paste, or commit remote URLs.** The `hf` / `hf-old` git remotes embed a live Hugging Face access token in the URL.

## Stale or duplicate paths — do not trust

- `src/pyproject.toml`, `src/requirements.txt` — stale nested mini-project (`requires-python >=3.8`). Never `pip install -e src/`.
- `src/polymarket_bot/` — standalone nested copy with its own Docker/CI/scripts. Not the running app.
- `package.json` — not real tooling (lists Python packages as npm deps; `main.py` does not exist). `npm start` / `npm test` are broken.
- `Dockerfile.api` — references `api_server.py`, which does not exist.
- `docker-compose.mirofish.yml` — builds `./mirofish`, which is gitignored and absent.
- `CLAUDE.md` — generic Claude-Flow/ruflo boilerplate (`npx @claude-flow/...`, `npm run build`); none of it applies to this Python repo.
- `legacy/`, `scripts/legacy/` — archived; do not wire into new code.

## Layout

`agent_trading_system.py` is the real entry point. `src/` holds the packages (`agents`, `api`, `backtesting`, `core`, `data`, `events`, `execution`, `ml`, `prediction`, `risk`, `strategies`, `trading`, `utils`). `tests/` is the collected pytest suite; `src/tests/` has two extra tests that are **not** collected. `frontend/` is a Next.js dashboard on port 3333.

## Conventions

- Absolute imports from `src` (`from src.utils.config import config`).
- Logging via `get_logger(name)` from `src/utils/logger.py`; JSON logs land in `data/logs/trading_YYYYMMDD.log`.
- Black + isort, line length 120, isort profile `black`. Type hints enforced by mypy with `ignore_missing_imports = true`.
- `asyncio_mode = auto` comes from `pytest.ini`, which takes precedence over `pyproject.toml`; most async tests need no decorator.
- Dev SQLite DB is **`src/data/trading.db`**; `data/price_history.db` is separate. `data/trading.db` does not exist. Postgres only exists under the `full` compose profile.

## Repo etiquette

- `master` is the working branch. `.github/workflows/ci.yml` triggers on `main`/`develop`, so **CI does not run on `master` pushes** — run the checks locally before claiming a change passes.
- Generated/ignored: `*.db`, `*.log`, `models/*.pkl`, `data/test_runs/`, `data/identity/`, `config/.env`. `ruvector.db` is tracked despite the ignore rule — do not add more like it.
- Ports: API 8000 local / 7860 Docker+HF, frontend 3333, Redis 6379, Postgres 5432, Prometheus 9090, Grafana 3000.
