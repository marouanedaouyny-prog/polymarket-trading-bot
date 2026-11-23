---
paths:
  - "src/**/*.py"
  - "agent_trading_system.py"
  - "entrypoint.py"
---

# Trading Safety

Real money is reachable from this code. These rules bind any edit that can place, size, or block an order.

## Hard rules

1. **Never enable live trading to test a change.** Leave `TRADING_MODE` at `paper` (or any non-`live` value) and `POLYMARKET_ALLOW_REAL_ORDERS=false`. Do not flip `.env` flags, even temporarily, unless the user explicitly asks for it.
2. **Never place a real order from a test, script, or benchmark.** Tests must use `OrderManager` in paper mode or a fake adapter. Do not instantiate `PolymarketCLOBAdapter` outside `OrderManager`.
3. **Route every new order path through the existing gate.** Reuse `OrderManager.place_order()` / `_live_trading_enabled()`; do not call the SDK client directly. Live execution requires all of: `TRADING_MODE == "live"`, `POLYMARKET_ALLOW_REAL_ORDERS=true`, a fresh passing readiness verdict (`src/utils/readiness_gate.py`), a constructed adapter, and a valid client.
4. **Fail closed.** If a risk check cannot be computed (missing balance, unknown price, exception), block the order. Never default an unknown to "allowed".
5. **Do not weaken risk limits** — no raised caps, removed circuit breakers, disabled stop-loss, or bypassed `should_trade()`. Tightening is allowed. Any limit change needs the user's explicit approval.
6. **Preserve startup credential validation** in `src/api/main.py:88-105`: requesting live mode with missing keys must keep raising `RuntimeError`.
7. **Never log, print, or persist** `PRIVATE_KEY`, `POLYMARKET_API_*`, or `FASTAPI_API_KEY`. Do not echo env files or remote URLs.
8. **Keep simulated results out of live paths.** Root `simulate.py`, `trusted_run.py`, `ultra_high_win_rate.py`, `high_win_rate_sim.py`, `test_100_trades.py` are throwaway. Never have a live code path read their outputs, and never hardcode a win rate or PnL.

## Gate locations

| What | Where |
|---|---|
| Mode read (at construction, not per-order) | `src/execution/order_manager.py:19-22` |
| Adapter init condition | `src/execution/order_manager.py:38` |
| Readiness verdict gate (fail-closed) | `src/utils/readiness_gate.py`, called from `order_manager.py:39-51` |
| Single source of truth for live permission | `src/execution/order_manager.py:53-60` |
| Live branch / blocked branch | `src/execution/order_manager.py:74-97` |
| Flag defaults (`ENABLE_LIVE_TRADING`, `POLYMARKET_ALLOW_REAL_ORDERS`, `POLYMARKET_SANDBOX=true`) | `src/utils/config.py:392-411` |
| Hardcoded `PRODUCTION` CLOB env | `src/execution/clob_adapter.py:27` |
| API kill-switch gate before order | `src/api/routers/trades.py:93-99` |
| Absolute / streak loss kill-switch | `src/api/routers/trades.py:38-52` |

## Known gaps — do not assume these protections exist

- **The readiness gate only checks that a fresh verdict file exists.** `OrderManager` refuses to build a live adapter unless `data/readiness_verdict.json` says `passed: true` and is under 7 days old. It cannot prove the verdict was honestly produced — regenerate it with `python scripts/tools/readiness_check.py --json data/readiness_verdict.json` rather than hand-editing. The file is a generated artifact; do not commit it.
- **The API risk manager ignores `config/.env`.** `src/api/state.py:20` builds `RiskManager()` with no args, so it uses `DynamicRiskManager._DEFAULTS` (daily loss 20%, max position 10%). Changing `DAILY_LOSS_LIMIT` or `MAX_POSITION_PCT` in `.env` changes the bot process only, not the API.
- **Default daily-loss limit disagrees across modules**: `src/utils/config.py:237` defaults to `0.05`; `src/risk/dynamic_risk.py:30` defaults to `0.20`. Do not cite one as authoritative without checking which process you are in.
- **The API's kill switch is implemented but only guards new entries.** `kill_switch_activated` is initialized in `DynamicRiskManager.__init__`, `emergency_kill_switch()` sets it, and `should_trade()` refuses while active. It does not cancel open orders or unwind positions.
- **Leakage guard is active.** `MarketPredictor.load_model()` rejects any artifact with `roc_auc >= 0.999` or `brier_score <= 0.001`, and `train()` refuses to save one. The model is trained on leak-free entry-time prices (`data/training/entry_price_dataset_v2.json`, 1,252 markets, built by `scripts/tools/build_entry_dataset.py`). Its random-split Brier `0.1186` is not an edge: price alone scores `0.1192` on the same rows, and walk-forward OOS is `0.1515` (model) vs `0.1377` (price). Do not remove the guard, and do not resurrect post-resolution prices to make the numbers look good.
- **`reset_daily()` is never called.** `src/risk/dynamic_risk.py:394` defines it, but no live caller invokes it. After the daily-loss limit trips, all new entries are refused until restart. The backtest harness calls it per calendar day; live code does not.
- **Confidence thresholds disagree.** `config/.env` sets `MIN_CONFIDENCE=70` for the research gate, while `DynamicRiskManager._DEFAULTS['min_confidence']` is `85`. 24 of 30 research-passing trades were blocked by the risk layer for this reason. Do not lower risk defaults to close the gap; reconcile upward if anything.
- **Throughput is ~5 trades per 13.5 months** across 1,052 historical candidates. A 50-trade sample cannot be produced from the current data or gate, and any 4–5 trade PnL (e.g. `+43%` driven by one 7.5¢ win) is not evidence of edge.
- **Root `.env` sets `TRADING_MODE=instant`.** It is not `live`, so `_live_trading_enabled()` still fails closed, but it disagrees with `config/.env` (`paper`). Treat any non-`paper` value as a red flag and fix it before running the bot.
- **Trade PnL must be settled on the side actually bought.** `TraderAgent` buys YES when `win_prob >= price`, otherwise NO, and computes PnL from that side's entry price. The old YES-only formula overstated NO wins by orders of magnitude.
- **$20 cannot fund 50 trades.** `RiskAgent` requires `balance >= min_bet / max_position_pct` = `1.0 / 0.05` = `$20`. At `$20`, one $1 loss drops the balance to `$19` and every subsequent trade is rejected. This is a structural floor, not a bug to patch by lowering `MIN_BET` without the user's approval.
- **`POLYMARKET_SANDBOX` default mismatch**: `src/utils/config.py:406` defaults to `true`, `src/data/polymarket_client.py:37` defaults to `false`. Data reads can hit production Gamma while config reports sandbox.
- **Mode is fixed at construction.** `OrderManager` reads `TRADING_MODE` once in `__init__`; changing the env var at runtime does nothing. Restart the process.
- **Which `.env` wins depends on the entry point.** `src/utils/config.py:21-30` loads `config/.env` (falling back to root `.env`) with `override=False`, so exported shell variables take precedence. `src/api/main.py` loads only the root `.env`. `OrderManager` uses raw `os.getenv`, so the API process sees root `.env` values, the bot process sees `config/.env` unless the shell overrides them.
- **Synthetic trade history is quarantined.** `src/data/trading.db` was moved to `data/quarantine/trading_synthetic_20261105.db` (1,209 fabricated rows, 5 questions, $1.0M fake profit). A second DB produced by diagnostics is at `data/quarantine/trading_db_from_diagnostics_20261105.db`. Never restore either or point a dashboard at it as real performance.
- **Backtests must stay out of the live path.** Use `scripts/tools/backtest_entry_dataset.py`, which stubs SQLite, the paper ledger, and risk-state persistence, and settles every trade through the real `RiskAgent`/`TraderAgent`. Results land in `data/test_runs/`.
- **Paper fills are applied to live fills too** (`order_manager.py:77` calls `_apply_simulated_fill`). Position state after a live fill is bookkeeping, not exchange truth — call `reconcile_positions()` before trusting it.

## Risk invariants

Effective defaults (`src/risk/dynamic_risk.py:_DEFAULTS`, overridden by `src/utils/config.py` in the bot process):

- Position size: max 10% of balance; half-Kelly, hard cap 20%.
- Entry filters: `min_edge` 0.08, `min_confidence` 85.
- Per-trade exits: stop loss 15%, take profit 50%.
- Circuit breakers (must all stay): 25% drawdown from start, 50% loss from peak, 10 consecutive losses, daily loss limit breached.
- API kill switch: realized PnL at or below `MAX_DAILY_LOSS_ABS` (default -20) or `MAX_CONSECUTIVE_LOSSES` (default 3).
- Risk tightens automatically with drawdown and losing streaks (`dynamic_risk.py:111-138`). Preserve that direction of travel.

## Before reporting a trading change as done

State explicitly that it was exercised in paper mode only, and name the risk checks whose behavior changed. Do not claim a live path works — it cannot be verified without real funds.
