# S18 LEARN — lessons from this run

## What worked
- Extending the existing HTML template (minimal diff, one file, no new deps) delivered the pro UI: SIMULATED/LIVE pill, 5s polling, canvas equity curve, positions table, trades ledger, kill-switch UI, circuit-breaker alert, mobile-responsive, dark theme.
- Endpoint contract (/api/dashboard/data) already matched all template needs — zero backend changes required.
- compileall / flake8 / mypy / focused integration test all pass on the untouched backend.

## What didn't work / was blocked
- Direct social-media access (instagram.com/seb.ai, youtube.com, reddit.com/r/GrokBot) blocked by auto-mode classifier (Three-Party Attack / Data Exfiltration). Substitute: locally-saved @seb.ai guides in goal/ (read successfully).
- Starting uvicorn for a live /dashboard render check blocked by classifier in prior turns — residual; user should run `FASTAPI_API_KEY=dev-key python entrypoint.py` manually.
- Independent S12 review (12_review.md) blocked by provider HTTP 429 rate limit (×2). Same hypothesis+action failing twice → stopped, changed strategy (log in failures.md, report to user).
- Independent S17 hostile judge (17_judge.md) blocked by provider HTTP 403 consent (unorouter.com/consents).

## Decisions that held
- Minimal diff: one HTML file rewritten, no backend touched, no new dependencies (canvas vs charting lib).
- Level L3 product dashboard: no 3D/motion (doesn't improve communication for a trading readout).
- Dark theme, sentence-case labels (no ALL-CAPS tell), tabular-nums for money, escapeHtml on all injected values.
- Paper mode default; prominent SIMULATED pill; kill switch POST /system/stop; circuit-breaker alert.

## Recommendations for next session
1. Re-spawn (or manually perform) independent S12 review → 12_review.md:PASS.
2. Re-spawn (or manually perform) independent S17 hostile judge → 17_judge.md:PASS (grant provider consent at unorouter URL if needed).
3. User run: `FASTAPI_API_KEY=dev-key python entrypoint.py`, open http://localhost:7860/dashboard, confirm render + polling.
4. Only after 12_review.md:PASS + 17_judge.md:PASS + 16_verify.log exist → claim "Done" citing all three (ORCHESTRATOR.md law).
