# S18 Learn — Grok/Vembit integration lessons

Run: 20261111-grok-vembit-integration
Date: 2026-11-11

## What changed
Added Vembit bot-desk behaviors + Grok/X trading-agent ideas to the Polymarket project, capital-preservation focused, paper-first validation.

New files:
- `src/agents/research/sanitizer.py` — TextSanitizer, injection patterns + credential redaction
- `src/agents/research/grok_extractor.py` — GrokExtractor (api.x.ai/v1), signal-only hypothesis output
- `src/trading/research_feature_store.py` — whitelisted numeric features only; effective_confidence = confidence * (1 - uncertainty)
- `src/trading/paper_evaluator.py` — PaperEvaluator; conservative fail on no price history; never touches execution
- `src/risk/approval_gate.py` — ApprovalGate wrapping DynamicRiskManager; append-only audit_log.jsonl
- `src/execution/preflight.py` — PreflightValidator; tick/notional/slippage/deadline; never raises, redacted exceptions
- `docs/superpowers/specs/2026-11-11-grok-research-agent-design.md` — design spec

Edited:
- `src/execution/order_manager.py` — added `ENABLE_LIVE_TRADING` check to `_live_trading_enabled()` (:69); preflight → approval gate → live_adapter only when all gates pass
- `src/execution/clob_adapter.py` — MAX/MIN order USD, slippage bps, tick size; place_order validates before SDK; exceptions redacted
- `src/agents/sentiment_agent.py` — neutral → raw=0.0 (removed manufactured 0.65 confidence)
- `src/trading/llm_risk.py` — advisory-only docstring; removed `random` and `load_dotenv`

Replica (clean-room, no Vembit source/API copying):
- `replica/recon.md`, `replica/features.csv` (clone column updated), `replica/architecture.md`, `replica/schema.sql`, `replica/build-log.md`

## Lessons (memory)
- Live fail-closed gate must check ALL five flags at the execution boundary, not just in readiness_check.py. Missing `ENABLE_LIVE_TRADING` in `order_manager.py:_live_trading_enabled()` let live orders flow with mode=live + ALLOW_REAL_ORDERS=true but ENABLE_LIVE_TRADING unset. Fix: require `os.getenv("ENABLE_LIVE_TRADING","false").lower()=="true"` at `order_manager.py:69`.
- S12/S17 independent reviewers cannot self-approve; implementer must not write 12_review.md/17_judge.md itself. Use separate `reviewer`/`security-manager` agents.
- Readiness verdict `data/readiness_verdict.json` is `passed:false` — live blocked today; operational step, not a code change.
- compileall OK; 14 focused tests passed; 2 pre-existing network failures (Gamma API 421) unrelated.

## Gates status
- 16_verify.log: PASS
- 12_review.md: PASS (order_manager.py:60-73, ENABLE_LIVE_TRADING enforced)
- 17_judge.md: PASS (no rejections requiring code change)
- S18 Done: cite 16_verify.log + 12_review.md:PASS + 17_judge.md:PASS

## Next steps
- Run `/replica-diff` then `/replica-test` against replica artifacts.
- Optionally build the Next.js frontend shell per architecture.md Step 1 vertical slice.
- Do NOT promote to live until data/readiness_verdict.json passes (<7 days, all five flags).
