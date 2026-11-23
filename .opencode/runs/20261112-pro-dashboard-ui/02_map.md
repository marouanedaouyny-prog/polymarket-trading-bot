# S2 MAP — files & callers touched

Files changed:
- src/api/web/templates/dashboard.html — wholesale rewrite (pro dashboard UI). Same path, same endpoint contract.

Callers / consumers:
- src/api/web/dashboard.py:18-25 — dashboard_page reads HERE/templates/dashboard.html and returns it as HTMLResponse at /dashboard. Unchanged; contract (template path) preserved.
- src/api/main.py:279 — app.include_router(web_router). Unchanged.
- src/api/routers/system.py:14 — POST /system/stop kill switch. Template POSTs here. Unchanged.
- src/api/state.py — get_dashboard_state() returns the JSON the template consumes. Unchanged.
- src/api/web/dashboard.py:28-66 — dashboard_data builds positions/trade_history arrays matching template field names (market_id, direction, entry_price, size, pnl, unrealized_pnl, time, market, side). Unchanged; contract preserved.

Files NOT touched (no change needed):
- src/api/main.py, src/api/state.py, src/api/routers/system.py, src/api/web/dashboard.py — all contracts already match what the new template reads.
- frontend/ — empty Next.js shell left as-is (minimal diff; not part of this task).
