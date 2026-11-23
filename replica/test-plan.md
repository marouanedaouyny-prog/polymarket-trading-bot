# Replica test plan — Vembit bot-desk clone

Run: 20261111-grok-vembit-integration
Date: 2026-11-11
Source flows: `replica/recon.md` F01–F04

This plan tests the **clone**, not the original vembit.com. Per replica-test rules: never load-test, fuzz, or script the original app's servers.

## Flows under test

| ID | Flow | Screens |
|----|------|---------|
| F01 | Build and start a bot (plain English) | S04 bot desk |
| F02 | Get AI coaching on a market | S05 AI coach |
| F03 | Copy a top trader | S06 → S07 → S08 |
| F04 | Monitor AI desk (eight agents) | S04 AI desk |

## F01 — Build and start a bot (plain English)

Happy path:
- F01-H1: Open S04 bot desk → see empty state (no bots) → click "Create bot" → enter plain-English idea → click "Backtest" → see backtest result (edge/win-rate) → click "Start (paper)" → bot appears on desk with status=paper → stop bot → status=stopped

Edge cases:
- F01-E1: Empty idea text → validation error, cannot submit
- F01-E2: Very long idea (>200 chars) → accepted, truncated display
- F01-E3: Emoji and accents in idea → accepted and stored correctly
- F01-E4: Double-click "Start" → idempotent, single bot started
- F01-E5: Backtest fails → error shown, cannot start live
- F01-E6: Slow network → loading skeleton displayed
- F01-E7: Offline → error toast, offline state preserved
- F01-E8: Refresh mid-flow → bot state persisted (seed data / SQLite)
- F01-E9: Mobile width (390px) → all inputs reachable, keyboard works
- F01-E10: Keyboard only → can complete create→backtest→start flow

Negative cases:
- F01-N1: Start live without passing backtest → blocked (fail-closed gate)
- F01-N2: Start live without ENABLE_LIVE_TRADING=true → blocked

## F02 — Get AI coaching on a market

Happy path:
- F02-H1: Open S05 AI coach → enter "Should I buy X?" → AI returns direction/entry/stop/target → user clicks Confirm → ai_setup recorded with user_confirmed=1 → nothing placed until confirmed

Edge cases:
- F02-E1: Empty question → validation error
- F02-E2: AI says "no setup" → empty state, no Confirm button
- F02-E3: Market data stale → warning shown, no AI setup generated
- F02-E4: User cancels → ai_setup recorded with user_confirmed=0, no order
- F02-E5: Long market name (60 chars) → layout doesn't break

Negative cases:
- F02-N1: Confirm without human confirmation flag → order blocked (approval_gate requires manual_approved)
- F02-N2: AI confidence below threshold → setup rejected by risk gate

## F03 — Copy a top trader

Happy path:
- F03-H1: Open S06 leaderboard → view top traders 24H/7D/30D → open S07 trader profile → view positions + thesis → click Copy → S08 copy flow → enter own margin + leverage cap + optional TP/SL → confirm → trade recorded with leader_id

Edge cases:
- F03-E1: Insufficient margin → validation error
- F03-E2: Leverage cap > 1.0 → accepted but capped at 1.0 for live (unsafe leverage excluded)
- F03-E3: Leader closes trade → copy position closes too (if wired)
- F03-E4: Second user's data invisible → profile shows only own positions unless public leaderboard

Negative cases:
- F03-N1: Copy without confirmation → blocked
- F03-N2: Copy a deleted trader → permission denied / not found

## F04 — Monitor AI desk (eight agents)

Happy path:
- F04-H1: Open S04 AI desk → see CRAWLER/SOCIAL/SCAN/VET/SIZE/RISK/FILLS/CHIEF status → RISK vetoes a bad setup → FILLS places order after approval

Edge cases:
- F04-E1: RISK vetoes → setup blocked, no order placed
- F04-E2: Agent state stale → refresh/loading state

Negative cases:
- F04-N1: RISK agent down → all setups blocked (fail-closed)

## Automation

No frontend clone screens were built in this session (replica is schema+architecture shell only). Automation via Playwright is deferred until frontend shell exists (see architecture.md Step 1 vertical slice).

## Backend integration tests (passing)

- `python -m pytest tests/test_readiness_gate.py tests/test_integration_pipeline.py` → 14 passed
- `python -m compileall -q src entrypoint.py agent_trading_system.py` → OK
- `python check_config.py` → ALL CHECKS PASSED
- `python scripts/tools/readiness_check.py --json data/readiness_verdict.json` → NOT READY (5 failed)

## Bugs

See `replica/bugs.md`.

## Summary

Cases planned: 28 (F01: 10, F02: 7, F03: 7, F04: 4)
Cases automated: 0 (no frontend built yet)
Backend integration: passing
Readiness verdict: NOT READY FOR REAL MONEY — 5 failed checks (model beats price, out-of-sample size, trade expectancy > 0, bankroll survives losses, can reach 50 trades)
