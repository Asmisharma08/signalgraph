-- SignalGraph Database Schema
-- Run this once in the Supabase SQL editor.
-- Safe to re-run: every statement uses IF NOT EXISTS.

-- ============================================================
-- 1. instruments — the fixed 20-stock NSE demo universe
-- ============================================================
create table if not exists instruments (
  id uuid primary key default gen_random_uuid(),
  ticker text unique not null,
  name text,
  sector text
);

-- ============================================================
-- 2. watchlists — one per user (could have many, but demo = 1)
-- ============================================================
create table if not exists watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  name text default 'My Watchlist',
  created_at timestamptz default now()
);

-- ============================================================
-- 3. watchlist_items — per-instrument user settings
--    priority: NORMAL | HIGH
--    muted: user chose to suppress this instrument
--    notifications_enabled: per-instrument push toggle
-- ============================================================
create table if not exists watchlist_items (
  watchlist_id uuid references watchlists(id) on delete cascade,
  instrument_id uuid references instruments(id),
  priority text default 'NORMAL',
  notifications_enabled boolean default true,
  muted boolean default false,
  primary key (watchlist_id, instrument_id)
);

-- ============================================================
-- 4. market_events — every price/volume tick received
--    source: 'replay' or 'yahoo'
--    sequence_number: assigned by SignalGraph at ingestion
--    data_quality: 'OK' | 'STALE'
-- ============================================================
create table if not exists market_events (
  id uuid primary key default gen_random_uuid(),
  instrument_id uuid references instruments(id),
  price numeric not null,
  volume bigint,
  event_time timestamptz not null,
  ingested_at timestamptz default now(),
  source text not null,
  sequence_number bigint not null,
  data_quality text default 'OK'
);

-- ============================================================
-- 5. instrument_stats — rolling statistics per instrument
--    Updated incrementally via EMA (alpha=0.15)
-- ============================================================
create table if not exists instrument_stats (
  instrument_id uuid primary key references instruments(id),
  rolling_avg_return numeric default 0,
  rolling_std_return numeric default 0,
  rolling_avg_volume numeric default 0,
  last_price numeric,
  last_event_time timestamptz,
  updated_at timestamptz default now()
);

-- ============================================================
-- 6. signals — detected anomalies with severity >= 20
-- ============================================================
create table if not exists signals (
  id uuid primary key default gen_random_uuid(),
  instrument_id uuid references instruments(id),
  signal_type text not null,
  severity numeric not null,
  event_time timestamptz not null,
  explanation jsonb,
  dedupe_key text unique,
  created_at timestamptz default now()
);

-- ============================================================
-- 7. user_instrument_state — feed read-cursor per user+instrument
--    last_seen_at: guards against stale overwrites
-- ============================================================
create table if not exists user_instrument_state (
  user_id uuid references auth.users(id),
  instrument_id uuid references instruments(id),
  last_seen_at timestamptz,
  last_seen_price numeric,
  primary key (user_id, instrument_id)
);

-- ============================================================
-- 8. notification_log — audit trail of notification decisions
-- ============================================================
create table if not exists notification_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id),
  signal_id uuid references signals(id),
  channel text,
  sent_at timestamptz default now()
);

-- ============================================================
-- Indexes for the three hottest query patterns
-- ============================================================
create index if not exists idx_market_events_instrument_time
  on market_events (instrument_id, event_time desc);

create index if not exists idx_signals_instrument_time
  on signals (instrument_id, event_time desc);

create index if not exists idx_notification_log_user_time
  on notification_log (user_id, sent_at desc);
