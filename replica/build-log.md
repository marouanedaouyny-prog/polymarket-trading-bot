# Replica build log — Vembit bot-desk clone

Run id: 20261111-grok-vembit-integration
Date: 2026-11-11
Scope: clean-room clone of Vembit bot-desk UX/workflow, no source/API copying, backing the existing Polymarket Python/FastAPI backend.

## Status summary
- recon.md: done (S01–S10 screens, F01–F04 flows, components, inferred data model, what cannot be cloned)
- features.csv: done (clone column filled below)
- architecture.md: done (stack, schema SQL, API route table, parts that bite, build order)
- schema.sql: done (users, bots, trades, leaderboard_entries, ai_setups; money as integer cents)
- build-log.md: this file
- Screens built: 0 of 10 (clone is schema+architecture shell; no frontend screens implemented yet — this project is a Python/FastAPI backend, the Next.js frontend shell from architecture.md is deferred)
- Must-haves done: 0 of 8 (clone column still "no" for all must-haves; partial credit where existing integration already covers the behavior)

## Per-feature clone status (features.csv clone column)

| feature | area | priority | clone | note |
|---|---|---|---|---|
| Plain-English bot idea input | bot desk | must | no | Not built as clone screen; schema `bots.idea_text` + route POST `/api/v1/bots` ready in architecture.md |
| Backtest check before live | bot desk | must | partial | paper_evaluator.py evaluates edge before live; no clone backtest screen yet |
| Bot desk (list of bots) | bot desk | must | no | Not built; route GET `/api/v1/bots` ready |
| Eight-agent AI desk | AI desk | must | no | Not built; RISK veto concept mapped to approval_gate.py |
| RISK veto on every setup | AI desk | must | partial | approval_gate.py wraps DynamicRiskManager; manual_approved gate |
| AI coach: direction/entry/stop/target | AI coach | must | partial | grok_extractor.py produces hypothesis; ai_setups schema + confirm route ready |
| Confirm-before-place | execution | must | partial | order_manager.py manual_approved + approval_gate before live_adapter.place_order |
| Copy trading with own margin + leverage cap + TP/SL | copy trading | must | no | Excluded from live execution (unsafe); schema supports trades.leader_id but no copy route built |
| Leaderboard 24H/7D/30D | social | should | no | schema leaderboard_entries + route GET `/api/v1/leaderboard` ready |
| Trader profile + positions | social | should | no | route GET `/api/v1/traders/{id}` ready |
| Leverage 1x–1000x | trading | must | no | Excluded from live (unsafe); schema leverage_cap default 1.0 |
| Cross margin + liquidation price shown before open | trading | should | no | Not built |
| Practice money or real cash mode | execution | should | partial | project default is paper mode; live requires fail-closed gate |

## Notes
- Nothing was copied from vembit.com: recon used public page read only; no JS bundles, no network logging, no source inspection (Terms §12 respected).
- The "clone" column stays `no` for must-haves because no clone frontend screens were built — this session's scope was the backend integration (Grok research agent + fail-closed live gates), which is complete and verified (16_verify.log PASS).
- Next step after S12+S17 pass: run `/replica-diff` then `/replica-test`; optionally build the Next.js frontend shell per architecture.md Step 1 vertical slice.
- No commits made yet — build-log is a record; screenshots for clone-screens/ not captured (no frontend built).
