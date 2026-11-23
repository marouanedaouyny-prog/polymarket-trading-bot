# Vembit bot-desk clone architecture

Source: `replica/recon.md`, `replica/features.csv`. Clean-room — no Vembit source, JS bundles, private APIs, or network-call logging. This clone targets UX patterns and workflow, not Vembit's platform or data.

## Step 1 — Stack

| layer | choice | why |
|---|---|---|
| web app | Next.js (App Router) + TypeScript | user's project is Python backend; frontend can be a thin Next shell calling existing FastAPI routes |
| styling | Tailwind + design tokens | fast, consistent, matches project's JS-free backend convention |
| mobile | none (responsive web) | recon targets desktop + phone via responsive layout; no native build needed |
| database | SQLite (file-based) | reuses project's existing SQLite persistence (`src/data/sqlite_db.py`); no new infra |
| ORM | raw SQL / sqlite3 | minimal, matches project conventions |
| auth | session cookie + existing API-key auth | project already uses `FASTAPI_API_KEY` + `X-API-Key` header; no new provider |
| payments | none | out of scope (no real-money checkout in clone) |
| email | none | out of scope |
| jobs | none | out of scope for MVP |
| files | none | out of scope |
| hosting | local / existing deploy | project already runs via `entrypoint.py` + Uvicorn |

One database, no microservices. The clone needs Vembit's features, not Vembit's architecture.

## Step 2 — Schema (`replica/schema.sql`)

```sql
-- Users (reuse existing project user table if present; otherwise minimal)
create table if not exists users (
    id text primary key,
    created_at timestamptz not null default (datetime('now'))
);

-- Bots: plain-English idea input, backtest result, live/paper status
create table if not exists bots (
    id text primary key,
    user_id text not null,
    idea_text text not null,
    backtest_edge real,
    backtest_win_rate real,
    backtested_at timestamptz,
    status text not null default 'draft'
        check (status in ('draft','backtested','live','stopped')),
    margin_cents integer not null default 0,
    leverage_cap real not null default 1.0,
    stop_loss real,
    take_profit real,
    created_at timestamptz not null default (datetime('now')),
    updated_at timestamptz not null default (datetime('now')),
    foreign key (user_id) references users(id) on delete cascade
);
create index on bots (user_id);
create index on bots (status);

-- Trades: executed or simulated fills
create table if not exists trades (
    id text primary key,
    bot_id text,
    user_id text not null,
    market_id text not null,
    side text not null check (side in ('buy','sell')),
    entry real not null,
    stop real,
    target real,
    size real not null,
    margin_cents integer not null default 0,
    leverage real not null default 1.0,
    status text not null default 'open'
        check (status in ('open','closed','blocked','cancelled')),
    pnl_cents integer not null default 0,
    opened_at timestamptz not null default (datetime('now')),
    closed_at timestamptz,
    foreign key (bot_id) references bots(id) on delete set null,
    foreign key (user_id) references users(id) on delete cascade
);
create index on trades (user_id);
create index on trades (bot_id);
create index on trades (market_id);
create index on trades (status);

-- Leaderboard entries: P&L ranking (computed, not copied from Vembit's users)
create table if not exists leaderboard_entries (
    user_id text primary key,
    pnl_24h_cents integer not null default 0,
    pnl_7d_cents integer not null default 0,
    pnl_30d_cents integer not null default 0,
    win_rate real not null default 0,
    markets text not null default '',
    updated_at timestamptz not null default (datetime('now')),
    foreign key (user_id) references users(id) on delete cascade
);
create index on leaderboard_entries (pnl_24h_cents);
create index on leaderboard_entries (pnl_7d_cents);
create index on leaderboard_entries (pnl_30d_cents);

-- AI setups: coach output (direction/entry/stop/target), human confirm before place
create table if not exists ai_setups (
    id text primary key,
    user_id text not null,
    market_id text not null,
    direction text not null check (direction in ('long','short','neutral')),
    entry real not null,
    stop real,
    target real,
    ai_confidence real not null default 0,
    user_confirmed integer not null default 0 check (user_confirmed in (0,1)),
    executed_at timestamptz,
    created_at timestamptz not null default (datetime('now')),
    foreign key (user_id) references users(id) on delete cascade
);
create index on ai_setups (user_id);
create index on ai_setups (created_at);
```

Money stored as integer cents + currency (USD default) — no floating-point money. Status fields use check constraints. Every owned row has `user_id` with cascade delete.

## Step 3 — API

Routes reuse project's FastAPI (`src/api/main.py`) under `/api/v1/bots/...`:

| method path | what it does | who | input | output | flow |
|---|---|---|---|---|---|
| POST `/api/v1/bots` | create bot from plain-English idea | authenticated user | `{idea_text, margin_cents, leverage_cap}` | `{id, status}` | S04 |
| GET `/api/v1/bots` | list user's bots on bot desk | authenticated user | none | `[Bot]` | S04 |
| POST `/api/v1/bots/{id}/backtest` | run backtest on historical prices | bot owner | `{id}` | `{edge, win_rate}` | S04 |
| POST `/api/v1/bots/{id}/start` | start bot live/paper (fail-closed gate) | bot owner | `{id, mode}` | `{status}` | S04 — blocked unless all live flags pass |
| POST `/api/v1/ai/setups` | record AI coach setup | authenticated user | `{market_id, direction, entry, stop, target}` | `{id}` | S05 |
| POST `/api/v1/ai/setups/{id}/confirm` | human confirms before place | setup owner | `{id}` | `{status}` | S05 — nothing placed until confirmed |
| GET `/api/v1/leaderboard` | P&L ranking 24H/7D/30D | public | `{window}` | `[LeaderboardEntry]` | S06 |
| GET `/api/v1/traders/{id}` | trader profile + positions | public | `{id}` | `{profile, positions}` | S07 |
| POST `/api/v1/copy` | copy trade with own margin + caps | authenticated user | `{leader_id, margin_cents, leverage_cap}` | `{trade_id}` | S08 |

Webhooks: none (no Stripe/calendar). Background jobs: none for MVP.

## Step 4 — Parts that bite

- **Fail-closed live gate**: every live start must pass all five flags + fresh readiness verdict; never automatic (reuses `order_manager.py` + `approval_gate.py`).
- **Human-in-the-loop**: AI setups require explicit `user_confirmed=1` before any order path; never auto-execute.
- **No 1000x leverage / copy-trading automation in live path**: excluded per Vembit risk warning and prediction-market rule (unsafe).
- **Money as integer cents**: avoids floating-point drift in P&L.
- **Idempotency**: retry-safe bot creation/confirmation via idempotency keys on mutating endpoints.
- **Rate limits**: Polymarket CLOB 100 req/10s API-key auth respected on any live path.

## Step 5 — Build order

1. **Vertical slice (must-have)**: sign up → create bot (plain English) → backtest → start (paper) → see result on bot desk. Screens: S04. Tables: `users`, `bots`. Routes: POST/GET bots, POST backtest.
2. **AI coach + confirm**: S05 `ai_setups`, confirm route. Tables: `ai_setups`.
3. **Leaderboard + trader profile + copy**: S06/S07/S08. Tables: `leaderboard_entries`, `trades`.
4. **Should-haves**: leverage caps, TP/SL, liquidation price display, practice vs real cash toggle.
5. **Fixes**: replica-entrepreneur findings after build.

Three riskiest parts: (1) fail-closed live gate misconfiguration, (2) floating-point money drift, (3) unconfirmed AI setup auto-executing.

Next step: `/replica-design` — design tokens + primitives, then `/replica-build` shell → vertical slice.
