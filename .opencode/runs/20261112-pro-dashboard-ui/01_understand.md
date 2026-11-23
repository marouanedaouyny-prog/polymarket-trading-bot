# S1 UNDERSTAND — current state & gap

Current state:
- Core trading system already built and functional: compileall passes (exit 0). TradingAgentSystem (lead/research/risk/trader/monitor agents), paper ledger, SQLite, dynamic risk, ML model, FastAPI app with API-key auth, audit logging, slowapi rate limiting, security headers, IP whitelisting, request-size limiting.
- Shared runtime state in src/api/state.py: ORDER_MANAGER (mode=paper), RISK_MANAGER, push_trading_state/update_dashboard_state/get_dashboard_state.
- Dashboard endpoint contract: GET /api/dashboard/data (public route, src/api/main.py:116) returns balance, daily_pnl, win_rate, total_trades, winning/losing_trades, drawdown, max_drawdown, consecutive_losses, circuit_breaker_triggered, is_live, peak_balance, positions[{market_id,direction,entry_price,size,pnl,unrealized_pnl}], trade_history[{time,market,side,pnl}], server_time.
- Kill-switch endpoint: POST /system/stop (src/api/routers/system.py:14).
- Existing frontend: basic dark HTML dashboard at src/api/web/templates/dashboard.html (served by src/api/web/dashboard.py at /dashboard); stats cards, positions table, trades table, circuit-breaker alert, 5s polling. No equity curve, no prominent SIMULATED label, no kill-switch UI, no mobile-responsive polish, no high-trust aesthetic.
- frontend/ Next.js shell is empty (package.json only) — no source files.

Gap: the UI is functional but basic; not "pro"/trustworthy. Need pro interface consuming /api/dashboard/data.

Constraints:
- Minimal diff; extend existing HTML template rather than building empty Next.js shell (per ponytail ultra + prior decision).
- Single self-contained HTML file; canvas equity curve (no external chart deps); polls /api/dashboard/data every 5s.
- Prominent SIMULATED/PAPER label; kill switch UI hitting POST /system/stop; circuit-breaker alert; mobile-responsive; dark theme.
- No new dependencies; no social-media access.
