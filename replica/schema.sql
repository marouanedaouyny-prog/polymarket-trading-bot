-- Replica schema for Vembit bot-desk clone (clean-room, SQLite-compatible)
-- Money stored as integer cents + currency. Status fields use check constraints.

create table if not exists users (
    id text primary key,
    created_at timestamptz not null default (datetime('now'))
);

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
