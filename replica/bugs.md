# Replica bugs — Vembit bot-desk clone

Run: 20261111-grok-vembit-integration
Date: 2026-11-11

Severity: S1 = data loss / security hole / core flow blocked | S2 = feature broken, no workaround | S3 = broken with workaround | S4 = cosmetic

## Open bugs

### BUG-001 (S1) — Readiness verdict NOT READY FOR REAL MONEY
**Steps:** Run `python scripts/tools/readiness_check.py --json data/readiness_verdict.json`
**Expected:** All checks pass → verdict passed=true
**Actual:** 5 failed:
- model beats price (brier model=0.1515 price=0.1377, gap=-0.0138, need +0.005)
- out-of-sample size (rows=1052 ≥200 OK, but executed trades=5 < 30 needed)
- trade expectancy > 0 (95% CI lower = -280.6%, n=5)
- bankroll survives losses (balance=$20.00, min_bet=$1.00, max_pos=5%, floor=$20.00, consecutive losses survivable=0, need ≥5)
- can reach 50 trades (5 trades/13.6 months → 136 months to 50, max 6)
**Evidence:** `data/readiness_verdict.json` passed=false
**Fix:** Improve model calibration (Brier), increase executed trade count, raise starting balance or lower min_bet/max_pos, increase trade frequency. Operational — not a code change.

### BUG-002 (S2) — No frontend clone screens built
**Steps:** Open any S-screen (S01–S10) in a browser
**Expected:** Clone UI renders
**Actual:** No frontend screens implemented; replica is schema+architecture shell only (replica/architecture.md, replica/schema.sql, replica/features.csv, replica/build-log.md)
**Evidence:** `replica/` contains no HTML/TSX/screens; features.csv clone column all "no"/"partial"
**Fix:** Build Next.js frontend shell per architecture.md Step 1 vertical slice (sign up → create bot → backtest → start paper → see result on bot desk)

### BUG-003 (S2) — Copy trading excluded from live (unsafe)
**Steps:** Attempt copy-trade live flow
**Expected:** Copy with own margin + leverage cap + TP/SL
**Actual:** Excluded from live execution per Vembit risk warning; no copy route built
**Evidence:** features.csv "Copy trading" clone=no; architecture.md route POST `/api/v1/copy` listed but not implemented
**Fix:** Deferred — out of scope for live; paper-mode copy could be added later

### BUG-004 (S3) — Leverage 1x–1000x not available (excluded, unsafe)
**Steps:** Open leverage selector
**Expected:** 1x to 1000x leverage
**Actual:** leverage_cap default 1.0 only; 1000x excluded from live
**Evidence:** features.csv "Leverage 1x–1000x" clone=no; schema.sql leverage_cap default 1.0
**Fix:** Deferred — intentionally excluded per safety policy

### BUG-005 (S3) — Cross margin + liquidation price not shown
**Steps:** Open trade screen before placing order
**Expected:** Liquidation price shown before open
**Actual:** Not built
**Evidence:** features.csv "Cross margin + liquidation price" clone=no
**Fix:** Add to trade screen in frontend build

### BUG-006 (S3) — Eight-agent AI desk not implemented as UI
**Steps:** Open S04 AI desk
**Expected:** CRAWLER/SOCIAL/SCAN/VET/SIZE/RISK/FILLS/CHIEF status visible
**Actual:** Concept mapped to backend approval_gate.py (RISK veto) but no UI desk
**Evidence:** features.csv "Eight-agent AI desk" clone=no; "RISK veto" clone=partial (backend only)
**Fix:** Build AI desk UI in frontend build

### BUG-007 (S3) — Bot desk UI not implemented
**Steps:** Open S04 bot desk
**Expected:** List of bots with status, backtest result, start-live toggle
**Actual:** Schema + routes ready, no UI
**Evidence:** features.csv "Bot desk (list of bots)" clone=no
**Fix:** Build bot desk UI in frontend build

## Fixed bugs

None yet.

## Summary

Open bugs: 7 (S1: 1, S2: 1, S3: 5, S4: 0)
Shippable: NO — open S1 (readiness not ready for real money) blocks shipping.
