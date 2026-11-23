# Grok Research Agent — Design Spec

**Date:** 2026-11-11
**Status:** Draft (pending user review)
**Project:** Polymarket trading automation

## 1. Problem and intent

Add externally observable Vembit bot-desk behaviors (plain-English bot idea input, backtest-then-live flow, AI desk with a RISK veto) and Grok/X trading-agent ideas to this Polymarket project, optimized for capital preservation ("be sure from its not losing money easily"). Paper-first validation; live trading remains fail-closed and disabled by default.

**Not in scope:** copy-trading automation, leverage (1x–1000x style), automated execution without human approval, scraping/reverse-engineering vembit.com (forbidden by its Terms of Service section 12), any claim of guaranteed returns.

## 2. Constraints (verified from sources)

- Vembit Terms §12: no scraping, reverse-engineering, or automated interference with the service. Clean-room public-behavior analysis only; no JS bundles, private APIs, or network-call logging.
- Grok API (`api.x.ai/v1`, `XAI_API_KEY`): X Search, web search, structured outputs, function calling are documented capabilities. All Grok output is untrusted signal; it never authorizes or sizes live trades.
- Polymarket CLOB docs: API-key auth at 100 req/10s, per-signer token buckets for orders, `py-clob-client`. **No documented paper/sandbox environment**, so paper validation stays in-process against historical price history.
- Existing weaknesses to address: `sentiment_agent.py:49-50` manufactures neutral→0.65 confidence; `llm_risk.py` recommends position sizes directly (must not be execution authority); `clob_adapter.py` lacks preflight simulation, price/size/tick validation, slippage/deadline controls, redaction of exceptions.

## 3. Security boundary (data flow)

```
External/X/Web data
  → Sanitizer + provenance/timestamp checks (reject prompt-injection patterns,
    unverified claims, credential-like text)
  → Grok/provider research extractor (structured hypothesis + uncertainty +
    sources; untrusted signal only)
  → Deterministic feature store (whitelisted numeric features only)
  → Offline/paper evaluator (replay on historical prices; no execution)
  → Independent risk policy (DynamicRiskManager + circuit breakers)
  → Manual approval (human-in-the-loop; recorded in audit log)
  → Execution preflight (simulate fill; tick/size/price/slippage/deadline
    validation; redacted exceptions)
  → Limited wallet/order (dedicated funds; per-order cap)
LLM output → hypothesis only. Never authorizes or sizes live trades.
```

## 4. Component responsibilities

| Component | Responsibility | Authority boundary |
|---|---|---|
| `src/agents/research/grok_extractor.py` | Grok API calls (X Search + web search + structured outputs). Returns structured hypothesis + uncertainty + sources. | Signal generation only. No order access, no credentials. |
| `src/agents/research/sanitizer.py` | Strips prompt-injection patterns and unverified claims from Grok/feed text before it enters model/risk path. | Defensive filter — can drop/flag, never execute. |
| `src/trading/research_feature_store.py` | Converts sanitized hypothesis into whitelisted numeric features (direction, confidence, source-age). | Read-only features; no position sizing. |
| `src/trading/paper_evaluator.py` | Replays hypotheses against historical price history in-process; reports expected edge/win-rate. | Paper only — no live adapter. |
| `src/risk/approval_gate.py` | Independent risk policy (DynamicRiskManager + circuit breakers) + manual approval recording. | Can veto any trade; cannot initiate one. |
| `src/execution/preflight.py` | Pre-send simulation: tick/size/price validation, slippage/deadline controls, redacted exceptions. Fixes `clob_adapter.py` gaps. | Gates every live order before `place_order`. |

## 5. Paper-to-live gating (fail-closed)

Live execution requires ALL of:
- `TRADING_MODE=live`
- `ENABLE_LIVE_TRADING=true`
- `POLYMARKET_ALLOW_REAL_ORDERS=true`
- Required venue credentials present
- CLOB adapter available and initialized
- Fresh passing `data/readiness_verdict.json` from `scripts/tools/readiness_check.py` (younger than 7 days)

Paper validation is in-process against historical price history (no Polymarket sandbox exists). Paper-to-live promotion requires a passing read-only paper run + explicit user approval — never automatic.

`sentiment_agent.py` and `llm_risk.py` are isolated from live execution: they feed the research feature store only, never `OrderManager` or `DynamicRiskManager` directly.

## 6. Circuit breakers (existing, preserved)

`DynamicRiskManager.check_circuit_breakers` halts on:
- 25% drawdown from session start
- 50% loss from peak balance
- 10 consecutive losses
- Daily-loss-limit breach

These are independent of any LLM output.

## 7. Audit and error handling

- Every Grok call, hypothesis, sanction, approval, rejection, and order attempt logged with timestamp + provenance ID to `data/audit_log.jsonl` (append-only).
- LLM exceptions are redacted before logging (no credentials, keys, or wallet data).
- No secrets stored in code or logs; keys come from environment only.

## 8. Acceptance criteria

- Grok extractor returns structured hypothesis (direction, confidence, uncertainty, sources) without touching execution.
- Sanitizer rejects prompt-injection patterns (unit tested).
- Paper evaluator replays a hypothesis and reports edge without placing orders.
- `approval_gate.py` vetoes trades that fail `DynamicRiskManager.should_trade`.
- `preflight.py` rejects invalid tick/size/price and enforces slippage/deadline before any live `place_order`.
- Live path blocked unless all five live flags + fresh readiness verdict pass (fail-closed).
- No unsupported profit claims anywhere in code or docs.
- Focused tests pass; full suite not regressed by new modules.