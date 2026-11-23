# S6 REASON — evidence → reasoning → decision → expected → verification

Evidence:
- /api/dashboard/data (src/api/web/dashboard.py:28-66) already returns all fields the template needs: balance, daily_pnl, win_rate, total_trades, winning/losing_trades, drawdown, max_drawdown, consecutive_losses, circuit_breaker_triggered, is_live, peak_balance, positions[{market_id,direction,entry_price,size,pnl,unrealized_pnl}], trade_history[{time,market,side,pnl}], server_time. Public route (no API key) at src/api/main.py:116.
- POST /system/stop (src/api/routers/system.py:14) exists for kill switch.
- Existing template at same path is served unchanged by src/api/web/dashboard.py:18-25.

Reasoning:
- Extending the existing HTML template is the minimal diff (one file, no new deps, no build step) vs building the empty Next.js shell (would require Node install, pages, API client, state management).
- Canvas-based equity curve avoids adding a charting library dependency (ponytail rule: stdlib/platform feature over new dependency).
- Dark theme + SIMULATED pill + kill switch satisfy "pro/trustworthy/paper-first" requirements.

Decision:
- Rewrite src/api/web/templates/dashboard.html in place (same path, same contract), single self-contained HTML + inline CSS/JS, Level L3 product dashboard (3D/motion not justified for an internal trading tool).

Expected:
- Dashboard loads at /dashboard, polls /api/dashboard/data every 5s, shows SIMULATED pill (paper) / LIVE pill (live), circuit-breaker alert + kill switch button, positions table, trades ledger, canvas equity curve, mobile-responsive.

Verification:
- compileall exit 0 (HTML not compiled, but confirms no breakage to siblings).
- Focused integration test test_full_buy_sell_pnl_flow passes (trading path unchanged).
- Manual load of /dashboard with FASTAPI_API_KEY=dev-key to confirm render + polling (requires starting uvicorn — previously blocked by classifier; noted as residual risk, see 18_learn.md).
