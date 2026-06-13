# Interface PRD (Design)

## 1. Document Control
- Name: Polymarket Trading Interface Redesign PRD (Design)
- Date: 2026-05-11
- Status: Draft v1
- Owner: Product + Design
- Scope: Replace the current fragmented UI stack with one coherent operator interface.

## 2. Problem Statement
The current project contains multiple interface implementations with overlapping purpose and inconsistent behavior.

### 2.1 Current-State Audit (from codebase)
- Multiple UIs exist at once:
  - Next.js frontend (`frontend/pages/*`)
  - Flask dashboard (`web_dashboard.py`)
  - Static HTML dashboard (`index.html`)
  - Terminal dashboards (`dashboard.py`, `interface_demo.py`)
- Startup paths are inconsistent:
  - `run_full_stack.py` starts `api.trading_api:app`
  - `run_system.py` starts `api_server.py`
- Frontend API contracts are inconsistent with backend realities:
  - Dashboard pages call `/api/performance`, `/api/charts/equity`, `/api/trade/execute`, `/api/config`, `/ws`
  - Those endpoints exist in `api_server.py`, not in `api/trading_api.py`
- Some pages mix mock-only data with live API expectations (e.g., `trading.tsx` hardcoded demo data).
- No single source of design truth. No clear design system contract.

### 2.2 Business Impact
- Operators cannot trust what they see across pages/environments.
- Increased incident risk due to UI/API drift.
- Slower delivery because each change must be repeated across multiple interfaces.

## 3. Product Goal
Design one production operator interface for monitoring and controlling the trading system, with consistent data contracts and risk-first workflows.

## 4. Target Users
- Trader/Operator: monitors opportunities and executes/halts actions.
- Risk Owner: validates exposure, drawdown, and kill-switch state.
- Engineer/On-call: checks runtime health, stream latency, and data quality.

## 5. Product Principles
- Single source of truth: one UI, one API contract set.
- Risk-first: critical risk controls always visible and fast.
- Deterministic data: every displayed metric maps to a documented backend field.
- Progressive disclosure: high-level summary first, detailed diagnostics on demand.

## 6. Information Architecture
- Overview
- Markets
- Trades
- Risk
- System
- Settings

## 7. Screen Requirements

### 7.1 Overview
Must show:
- Bot state (`running`, `paused`, `stopped`)
- Balance, realized PnL, ROI
- Win rate, total trades, max drawdown
- Stream health (ws connected, last update age)
- Immediate controls: Start, Pause, Stop, Kill Switch

Acceptance:
- Metrics refresh <= 2s from server push or polling fallback.
- Control state reflects backend state after action in <= 1s.

### 7.2 Markets
Must show:
- Market question, category, yes/no price, volume, liquidity
- Edge and confidence with normalized scale
- Filters: category, min edge, min confidence, liquidity floor
- Trade action with confirmation

Acceptance:
- Filter changes apply client-side in <150ms for 200 rows.
- Manual trade action always requires confirmation modal.

### 7.3 Trades
Must show:
- Executed trades with timestamp, side, entry, size, pnl, status
- Search + filters (time window, result type)
- Drilldown panel for one trade

Acceptance:
- Pagination or virtualization required above 1k rows.
- Row-to-detail interaction <= 100ms perceived latency.

### 7.4 Risk
Must show:
- Current exposure by category
- Drawdown vs thresholds
- Position sizing policy summary
- Kill-switch status and trigger history

Acceptance:
- Risk breaches highlighted with strict severity levels (info/warn/critical).
- Kill-switch action requires typed confirmation.

### 7.5 System
Must show:
- API health, websocket health, update loop lag
- Error/event stream
- Component status table (data, strategy, execution, storage)

Acceptance:
- Health data timestamps are visible on every card.
- No stale value should appear without stale badge.

### 7.6 Settings
Must show:
- Starting balance (paper mode)
- API base URL/profile
- Safe reset operation
- Environment mode indicator (paper/live)

Acceptance:
- Destructive actions require explicit confirmation and backend acknowledgement.

## 8. UX and Visual Direction
- Direction: high-clarity trading ops console, dark-neutral base with cyan/amber semantic accents.
- Typography:
  - Heading: Space Grotesk
  - Numeric/telemetry: IBM Plex Mono
- Layout: dense but readable; desktop-first with responsive collapse for tablet/mobile.
- Motion:
  - Only meaningful transitions (state change, risk alert transitions, data refresh pulse).
  - Avoid decorative motion on every element.

## 9. Data Contract Requirements
- Each card/table field must map to one backend field with a field dictionary.
- No synthetic placeholder values in production routes.
- Time fields must be UTC ISO-8601 in transport and localized in UI.

## 10. Non-Functional Requirements
- First meaningful paint < 2.5s on local/dev network.
- Route-to-route navigation < 300ms after initial load.
- Accessibility baseline: keyboard navigation and contrast AA for primary surfaces.
- Error resilience: all failing API calls show explicit error states with retry.

## 11. Out of Scope (v1)
- Public marketing website
- Multi-user RBAC admin panel
- Strategy authoring IDE
- Mobile-native app

## 12. Success Metrics
- 0 conflicting interface entrypoints in repo runtime path.
- 100% of displayed metrics mapped to backend contract docs.
- <1% UI error rate (failed requests / total requests).
- Operator task completion (start/stop/inspect trade) < 20s median.

## 13. Design Deliverables
- IA sitemap
- Low-fidelity wireframes for 6 screens
- High-fidelity desktop + mobile states
- Interaction specs for control actions and alerts
- Component inventory and token spec

## 14. Risks and Mitigations
- Risk: API drift returns.
  - Mitigation: generated TypeScript API client from OpenAPI schema.
- Risk: overreliance on websocket with silent disconnect.
  - Mitigation: heartbeat + polling fallback with visible state.
- Risk: inconsistent environments.
  - Mitigation: single bootstrap profile and environment banner.

## 15. Open Questions
- Should manual trade execute be available in live mode by default?
- Which risk thresholds are hard limits vs configurable soft limits?
- Do we need audit trails for every UI control action in v1?
