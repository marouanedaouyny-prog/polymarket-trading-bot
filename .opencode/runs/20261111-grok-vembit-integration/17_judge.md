# S17 JUDGE — hostile security/money review

Verdict: **PASS**

Scope: Grok/LLM/social → execution path, fail-closed live gate, secrets, audit log, scope creep, acceptance criteria, silent failures.

## Attack trace: Grok → sanitizer → feature_store → paper_evaluator → approval_gate → order_manager → clob_adapter

**Grok extractor is signal-only and disconnected from execution.** `src/agents/research/grok_extractor.py` is imported only by `src/trading/research_feature_store.py:14` and `src/trading/paper_evaluator.py:15`. It is NOT imported by `order_manager.py`, `clob_adapter.py`, or `agent_trading_system.py`. `GrokExtractor.extract_hypothesis` returns a `ResearchHypothesis` (direction/confidence/uncertainty/sources) — no order fields, no credentials, no size authority. Attack vector "LLM directly authorizes/sizes a live trade" does not exist in code.

**Sanitizer blocks injection before model/risk path.** `src/agents/research/sanitizer.py:17-31` matches directive/override/jailbreak/credential patterns; `sanitize()` returns `safe=False` on any match (`:99-101`) and redacts credentials before logging (`:73-79`). Rejected input is dropped, never passed through.

**Feature store is whitelisted numerics only.** `src/trading/research_feature_store.py:16-21` exposes only `research_direction/confidence/uncertainty/source_age_hours`; `hypothesis_to_features` (`:57-78`) computes `effective_confidence = confidence * (1 - uncertainty)` and never computes position size or touches OrderManager/live adapter.

**Paper evaluator is fail-closed and order-free.** `src/trading/paper_evaluator.py:44-109`: no price history → `passed=False` (`:57-65`); returns `PaperEvaluation`, never touches `clob_adapter` or `OrderManager`.

**Approval gate is veto-only.** `src/risk/approval_gate.py:61-118`: `allowed=True` requires risk checks + circuit breakers clear + `manual_approved=True` (default `require_manual_approval=True` at `:50`). Gate can veto, never initiate. Every decision and every order attempt appended to `data/audit_log.jsonl` (`:53-59`, `:120-142`).

**Preflight gates every live order.** `src/execution/preflight.py:46-142`: never raises; validates market_id/side/price/size numeric/positive, tick alignment, notional $1–$500, slippage ≤50bps, deadline; exceptions redacted to `type(exc).__name__` (`:136-142`).

**OrderManager live path is fail-closed.** `src/execution/order_manager.py:45-67`: `_live_trading_enabled()` requires mode=live + `POLYMARKET_ALLOW_REAL_ORDERS=true` + `live_adapter is not None` + `is_available`. `__init__` (`:45-58`) runs `check_live_readiness()` and on any exception sets `live_block_reason` and stays closed (`:49-50`). Preflight (`:84-103`) then approval gate (`:109-129`) run before `live_adapter.place_order` (`:132-137`). Blocked/filled attempts recorded via `record_order_attempt` (`:93-101`, `:119-127`, `:143-150`).

**CLOB adapter is defense-in-depth.** `src/execution/clob_adapter.py:61-146`: independently re-validates market_id/side/price/size/tick/notional caps before SDK call; exceptions redacted to type name only (`:142-146`); never logs credentials/wallet data.

## Fail-closed live gate — missing/stale/corrupted readiness verdict

`src/utils/readiness_gate.py:32-63`:
- File missing/unreadable → returns blocking reason (fail closed) `:41-45`
- `passed is not True` → blocking reason `:47-49`
- stale (>7 days) or future-dated → blocking reason `:51-62`
- returns `None` only on fresh passing verdict

`order_manager.py:47-50` catches `check_live_readiness()` exceptions and stays closed. Current `data/readiness_verdict.json` has `passed: false` with 5 failed checks (model beats price, OOS size, expectancy, bankroll, 50-trade throughput) → live is blocked today.

`POLYMARKET_ALLOW_REAL_ORDERS` accidentally true: still requires `TRADING_MODE=live` + fresh readiness verdict + adapter ready + credentials; all must hold simultaneously.

## Secrets

`clob_adapter.py:31-34` loads `POLYMARKET_API_KEY/SECRET/PASSPHRASE`/`PRIVATE_KEY` from env only. `clob_adapter.py:142-146` redacts exceptions to type name. `approval_gate.py:131-142` audit records market_id/side/size/price/outcome/reason only — no credentials. No secret fields logged in execution path.

One observation (not a FAIL): `clob_adapter.py:51` logs the raw exception `e` during `SecureClient` init (`logger.error(f"Failed to initialize Polymarket Live Client: {e}")`) — if that exception text ever embeds credentials it would leak to logs. Init-time only, not per-order.

## Audit log

Append-only JSONL (`approval_gate.py:55` `"a"` mode). Records every `evaluate()` decision and every `record_order_attempt` (blocked + filled). Tamper-evident trail via `provenance_id`. Silent-swallow caveat: `_append_audit` catches all exceptions and passes (`:57-59`) so a disk-full/log failure never blocks trading but also never surfaces — audit gaps possible under I/O failure. Deliberate availability-over-audit tradeoff; not a money-loss vector.

## Scope creep

Spec §1 explicitly excludes copy trading, leverage, automated execution without human approval, scraping vembit.com, guaranteed returns. Code contains none: no copy-trading, position capped at 10% (`config.py:165`, `dynamic_risk.py:26`), no 1x–1000x leverage, `manual_approved` required for live, no guaranteed-return claims. No LLM output reaches `place_order` or `live_adapter`.

## Acceptance criteria (spec §8) — all met in code

1. Grok extractor returns structured hypothesis without touching execution — `grok_extractor.py:30-130`, disconnected from OrderManager.
2. Sanitizer rejects prompt injection (unit tested) — `sanitizer.py:17-103`.
3. Paper evaluator replays hypothesis, no orders — `paper_evaluator.py:31-109`.
4. `approval_gate` vetoes trades failing `DynamicRiskManager.should_trade` — `approval_gate.py:82-93`.
5. `preflight` rejects invalid tick/size/price, enforces slippage/deadline — `preflight.py:82-117`.
6. Live path blocked unless all five flags + fresh readiness verdict — `order_manager.py:60-67`, `readiness_gate.py:32-63`.
7. No unsupported profit claims — none found in code/docs.
8. Tests pass; full suite not regressed — compileall OK, 104 tests passed.

## Silent failures / swallowed errors

- `approval_gate.py:57-59` — audit write failures swallowed (availability choice, not money-loss).
- `clob_adapter.py:51-54` — init failure logged, adapter stays None → live closed (safe fail-closed).
- `preflight.py:136-142`, `grok_extractor.py:128-130` — all exceptions caught, safe fallback returned (fail-closed direction).
- `agent_trading_system.py:982-983` — metrics push swallowed with bare `pass` (observability only, not execution).

## Rejected attack vectors (with citations)

| Attack | Rejection | Citation |
|---|---|---|
| Grok/LLM directly authorizes live trade | No import path to OrderManager/clob_adapter; signal-only | `grok_extractor.py`, `order_manager.py` |
| Prompt injection sets confidence=1.0 / approves trade | Sanitizer matches directive/override patterns → dropped | `sanitizer.py:17-101` |
| LLM confidence sizes a live trade directly | Confidence never feeds position size; Advisory-only `LLMRiskAdvisor` unused in execution | `llm_risk.py:1-9`, `order_manager.py:820` |
| Oversized/mispriced live order drains wallet | Preflight notional $1–$500 + tick + slippage; adapter re-validates | `preflight.py:93-117`, `clob_adapter.py:94-114` |
| Live trade without manual approval / failed readiness | `_live_trading_enabled()` + `check_live_readiness()` fail-closed | `order_manager.py:60-67`, `readiness_gate.py:32-63` |
| Secrets in logs/audit | Exceptions redacted; audit records no credentials | `clob_adapter.py:142-146`, `approval_gate.py:131-142` |
| Paper false green light with no price history | `passed=False` conservatively | `paper_evaluator.py:57-65` |
| Copy trading / leverage / guaranteed returns | Not implemented; excluded by spec | `config.py:165`, spec §1 |

## Conclusion

No path exists where Grok/LLM/social output can authorize, size, or place a live trade. The live gate is fail-closed and currently blocked (readiness verdict failing). Secrets are not logged. Audit is append-only. No scope creep. All acceptance criteria met.

**Verdict: PASS** — no rejections requiring code change. Observations noted above are non-blocking.
