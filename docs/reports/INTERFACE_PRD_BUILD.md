# Interface PRD (Build)

## 1. Document Control
- Name: Polymarket Trading Interface Rebuild PRD (Build)
- Date: 2026-05-11
- Status: Draft v1
- Owner: Engineering
- Scope: Build one production-ready interface aligned with backend contracts.

## 2. Build Objective
Implement a single frontend application and unified API integration layer to replace the previously fragmented interface paths.

## 3. Baseline Findings from Existing Code
- Multiple UI stacks existed simultaneously (`frontend/*`, `web_dashboard.py`, `index.html`, `dashboard.py`).
- Backend path mismatch:
  - `api_server.py` exposes dashboard-compatible endpoints and `/ws`.
  - `api/trading_api.py` exposes a smaller, incompatible subset.
- Startup inconsistency caused runtime drift (`run_full_stack.py` vs `run_system.py`).

## 4. Target Technical Architecture
- Frontend: Next.js (TypeScript) single app, one entrypoint.
- Backend source for UI: `api_server.py` (or equivalent unified router if migrated later).
- Real-time:
  - Primary: WebSocket `/ws`
  - Fallback: polling every 5s when socket unavailable.
- API consumption:
  - Generated typed client from OpenAPI (`/openapi.json`) or strict shared TS types.

## 5. Required Backend Contract (v1)
Required routes for interface v1:
- `GET /api/status`
- `GET /api/markets`
- `GET /api/trades`
- `GET /api/performance`
- `GET /api/charts/equity`
- `POST /api/trade/execute`
- `POST /api/reset`
- `POST /api/config`
- `WS /ws`

Contract rules:
- Stable response envelopes (no shape drift between runs).
- ISO timestamps.
- Consistent numeric precision rules for money/percent fields.

## 6. Repo Changes Required

### 6.1 Decommissioning (done in this change set)
- Remove frontend service from `docker-compose.yml` runtime.
- Convert startup scripts to backend-only.
- Decommission legacy interface entrypoints with explicit deprecation notices.

### 6.2 Rebuild Structure (new work)
Proposed structure:
- `frontend/app/*` or `frontend/pages/*` (single framework style only)
- `frontend/lib/api-client.ts`
- `frontend/lib/ws-client.ts`
- `frontend/components/*`
- `frontend/state/*` (query/cache + UI state)
- `frontend/tests/*`

## 7. Implementation Plan

### Phase 0: Foundation (1-2 days)
- Recreate frontend scaffold cleanly.
- Add linting, formatting, strict TS config.
- Add environment config (`NEXT_PUBLIC_API_BASE_URL`).

### Phase 1: Data and Contracts (2-3 days)
- Implement typed API client.
- Implement ws client with reconnect + heartbeat.
- Add error normalization and retry policy.

### Phase 2: Core Screens (4-6 days)
- Build Overview, Markets, Trades.
- Add loading/empty/error states for every section.
- Add route-level integration tests.

### Phase 3: Risk/System/Settings (3-4 days)
- Build Risk, System, Settings screens.
- Implement destructive-action safeguards.
- Implement environment and stale-data banners.

### Phase 4: Hardening (2-3 days)
- Performance pass (virtualized tables, memoized charts).
- Accessibility pass.
- Browser/device smoke tests.
- Production build + deployment docs.

## 8. Testing Strategy
- Unit tests:
  - formatters
  - derived metrics
  - risk badge mapping
- Integration tests:
  - API client + mock server
  - websocket reconnect behavior
- E2E tests:
  - startup flow, trade action flow, reset flow, kill-switch confirmation flow
- Contract tests:
  - compare frontend expected schema against backend OpenAPI snapshot

## 9. Observability Requirements
- Frontend logs for:
  - API failures
  - ws disconnect/reconnect
  - user control actions (non-sensitive)
- Metrics:
  - request error rate
  - websocket uptime
  - median action completion latency

## 10. Security and Safety
- No secrets in frontend bundle.
- CSRF/CORS model validated for deployment origin(s).
- Confirmation guards for high-risk actions (`reset`, `trade execute`, `kill-switch`).

## 11. Performance Targets
- Initial route render under 2.5s local baseline.
- Chart render under 200ms for 100 points.
- Table interactions under 150ms for 200 rows.

## 12. Release Plan
- Milestone A: Foundation + contracts
- Milestone B: Core operations screens
- Milestone C: Risk/system hardening
- Milestone D: Production rollout

Rollout pattern:
1. Internal dry run in paper mode
2. Shadow mode with real backend stream
3. Controlled enablement for operators

## 13. Acceptance Criteria
- Exactly one maintained UI entrypoint for operators.
- `docker-compose` default path runs backend without UI dependency.
- All v1 screens implemented with explicit loading/error/empty states.
- UI actions map to documented API routes and are tested.
- Deprecated legacy interface files contain clear decommission notices.

## 14. Risks and Mitigations
- Risk: backend schema drift during build.
  - Mitigation: schema snapshot tests in CI.
- Risk: websocket instability.
  - Mitigation: automatic reconnect + polling fallback + health indicator.
- Risk: operator misuse of destructive actions.
  - Mitigation: typed confirmations + audit logging.

## 15. Definition of Done
- Product signoff on Design PRD requirements.
- Engineering signoff on build milestones and tests.
- CI green for unit/integration/E2E suites.
- Runtime docs updated for backend-only default and new UI startup path.
