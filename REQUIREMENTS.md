# SignalGraph — Requirements Traceability

Every requirement extracted from `signalgraph_execplan.md`, mapped to its status and the file(s) that implement it. Updated continuously as work progresses.

**Legend:** ✅ Done | 🔧 In Progress | ⬜ Not Started

---

## Milestone 1 — Schema and Empty End-to-End Skeleton

### Database
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 1.1 | Create `instruments` table (id, ticker unique, name, sector) | ✅ | `db/schema.sql` |
| 1.2 | Create `watchlists` table (id, user_id → auth.users, name, created_at) | ✅ | `db/schema.sql` |
| 1.3 | Create `watchlist_items` table (watchlist_id, instrument_id, priority, notifications_enabled, muted; composite PK) | ✅ | `db/schema.sql` |
| 1.4 | Create `market_events` table (id, instrument_id, price, volume, event_time, ingested_at, source, sequence_number, data_quality) | ✅ | `db/schema.sql` |
| 1.5 | Create `instrument_stats` table (instrument_id PK, rolling_avg_return, rolling_std_return, rolling_avg_volume, last_price, last_event_time, updated_at) | ✅ | `db/schema.sql` |
| 1.6 | Create `signals` table (id, instrument_id, signal_type, severity, event_time, explanation JSONB, dedupe_key unique, created_at) | ✅ | `db/schema.sql` |
| 1.7 | Create `user_instrument_state` table (user_id, instrument_id, last_seen_at, last_seen_price; composite PK) | ✅ | `db/schema.sql` |
| 1.8 | Create `notification_log` table (id, user_id, signal_id, channel, sent_at) | ✅ | `db/schema.sql` |
| 1.9 | Index on market_events(instrument_id, event_time DESC) | ✅ | `db/schema.sql` |
| 1.10 | Index on signals(instrument_id, event_time DESC) | ✅ | `db/schema.sql` |
| 1.11 | Index on notification_log(user_id, sent_at DESC) | ✅ | `db/schema.sql` |
| 1.12 | All DDL uses `IF NOT EXISTS` for idempotent re-runs | ✅ | `db/schema.sql` |
| 1.13 | Seed 20 demo instruments (5 IT, 5 Banking, 4 Energy, 3 Consumer, 3 Automotive) | ✅ | `backend/app/main.py` (startup seed) |

### Backend Skeleton
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 1.14 | FastAPI app with health-check at GET /api/health | ✅ | `backend/app/main.py` |
| 1.15 | CORS restricted to FRONTEND_ORIGIN | ✅ | `backend/app/main.py` |
| 1.16 | Config from environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET, FRONTEND_ORIGIN, REPLAY_MODE, POLL_INTERVAL_SECONDS) | ✅ | `backend/app/config.py` |
| 1.17 | Supabase client created once, imported where needed | ✅ | `backend/app/db.py` |
| 1.18 | Auth dependency extracts user_id from verified JWT, never from client body | ✅ | `backend/app/auth.py` |
| 1.19 | Pydantic request/response models | ✅ | `backend/app/models/schemas.py` |
| 1.20 | File structure: ingestion/ (pipeline, replay_source, yahoo_source), signals/ (detectors, scoring), relevance/ (feed), notifications/ (decision), routes/ (watchlists, feed, signals) | ✅ | All stub files created |
| 1.21 | requirements.txt with all dependencies | ✅ | `backend/requirements.txt` |
| 1.22 | Route modules mounted on the app | ✅ | `backend/app/main.py` |

### Frontend Skeleton
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 1.23 | Vite React project initialized | ✅ | `frontend/` (scaffolded via create-vite) |
| 1.24 | Supabase browser client (anon key, single instance) | ✅ | `frontend/src/lib/supabaseClient.js` |
| 1.25 | Login.jsx — magic-link sign-in page | ✅ | `frontend/src/pages/Login.jsx` |
| 1.26 | Watchlist.jsx — list/edit watchlist page (stub) | ✅ | `frontend/src/pages/Watchlist.jsx` |
| 1.27 | Feed.jsx — hero screen, polls /api/feed (stub) | ✅ | `frontend/src/pages/Feed.jsx` |
| 1.28 | SignalDetail.jsx — single instrument severity breakdown (stub) | ✅ | `frontend/src/pages/SignalDetail.jsx` |
| 1.29 | FreshnessBadge.jsx — live/delayed/stale indicator | ✅ | `frontend/src/components/FreshnessBadge.jsx` |
| 1.30 | Frontend calls backend health-check and shows result | ✅ | `frontend/src/App.jsx` |
| 1.31 | Frontend dependencies: react, react-dom, @supabase/supabase-js | ✅ | `frontend/package.json` |

### Deployment (Deferred)
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 1.32 | Deploy backend to Render as long-running web service | ⬜ | Deferred per user decision |
| 1.33 | Deploy frontend to Vercel | ⬜ | Deferred per user decision |
| 1.34 | Two live URLs talking to each other | ⬜ | Deferred per user decision |

### Milestone 1 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A1.1 | Backend health route reachable | ✅ |
| A1.2 | Frontend renders successful response from backend | ✅ |

---

## Milestone 2 — Watchlist CRUD and Login

### Authentication
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 2.1 | Supabase Auth magic-link flow in Login.jsx | ✅ | `frontend/src/pages/Login.jsx` |
| 2.2 | Session token read from supabaseClient.auth.getSession() | ✅ | `frontend/src/lib/api.js` (`apiFetch`) |
| 2.3 | Unauthenticated requests redirect to Login, never sent to backend | ✅ | `frontend/src/App.jsx` (renders Login when no session), `frontend/src/lib/api.js` (`apiFetch` throws if no session) |

### Watchlist API
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 2.4 | POST /api/watchlists — create watchlist, returns {id, name} | ✅ | `backend/app/routes/watchlists.py` |
| 2.5 | GET /api/watchlists — list user's watchlists with items (instrument_id, ticker, priority, muted, notifications_enabled) | ✅ | `backend/app/routes/watchlists.py` |
| 2.6 | POST /api/watchlists/{id}/items — add by ticker (must be one of 20 seeded), returns 201 or 404 | ✅ | `backend/app/routes/watchlists.py` |
| 2.7 | PATCH /api/watchlists/{id}/items/{instrument_id} — update priority/muted, returns 200 | ✅ | `backend/app/routes/watchlists.py` |
| 2.8 | DELETE /api/watchlists/{id}/items/{instrument_id} — remove, returns 204 | ✅ | `backend/app/routes/watchlists.py` |
| 2.9 | All routes use get_current_user_id dependency | ✅ | `backend/app/routes/watchlists.py` |
| 2.10 | Watchlist queries scoped to verified user_id at DB level | ✅ | `backend/app/routes/watchlists.py` (`_get_owned_watchlist`) |

### Watchlist UI
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 2.11 | Watchlist.jsx — list/add/remove instruments from fixed 20-stock universe | ✅ | `frontend/src/pages/Watchlist.jsx`, `frontend/src/lib/instruments.js` |
| 2.12 | Data persists across full browser refresh (Supabase is source of truth) | ✅ | Verified via headless-Chromium screenshot after full reload |

### Milestone 2 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A2.1 | Create watchlist, add 3 instruments, full refresh, same 3 still present | ✅ |

---

## Milestone 3 — Ingestion Pipeline (Replay Mode)

### Pipeline Logic
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 3.1 | process_event(instrument_id, price, volume, event_time, source) → ProcessedEvent or None | ✅ | `backend/app/ingestion/pipeline.py` |
| 3.2 | Validation: reject malformed events | ✅ | `backend/app/ingestion/pipeline.py` (price > 0, volume >= 0) |
| 3.3 | Self-assigned sequence numbering per instrument | ✅ | `backend/app/ingestion/pipeline.py` (`_next_sequence_number`) |
| 3.4 | Deduplication by key: source:instrument_id:event_time_iso | ✅ | `backend/app/ingestion/pipeline.py` (`_is_duplicate`, existence check — see Decision Log re: no `dedupe_key` column on `market_events`) |
| 3.5 | Out-of-order detection: compare event_time against instrument's last_event_time | ✅ | `backend/app/ingestion/pipeline.py` |
| 3.6 | Late events stored but don't overwrite instrument_stats last_price/last_event_time | ✅ | `backend/app/ingestion/pipeline.py` |
| 3.7 | Rolling-stats EMA update (alpha=0.15): avg_return, std_return, avg_volume | ✅ | `backend/app/ingestion/pipeline.py` |
| 3.8 | EMA formula: new_avg = old * 0.85 + new * 0.15; new_std = sqrt(old_std² * 0.85 + (return - new_avg)² * 0.15); same for volume | ✅ | `backend/app/ingestion/pipeline.py` — verified by hand against actual stored values (rolling_avg_volume matched the formula exactly for TCS.NS) |

### Replay Source
| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 3.9 | Hardcoded event sequence: baseline for 20 stocks → normal updates → TCS.NS volume spike → TCS.NS price move → duplicate TCS.NS → late INFY.NS → RELIANCE.NS structural | ✅ | `backend/app/ingestion/replay_source.py` |
| 3.10 | Events paced 3–5 seconds apart | ✅ | `backend/app/ingestion/replay_source.py` (`_pace`) |
| 3.11 | Auto-runs on startup when REPLAY_MODE=true | ✅ | `backend/app/main.py` (background daemon thread in `lifespan`) |
| 3.12 | Manually runnable via `python -m app.ingestion.replay_source` | ✅ | `backend/app/ingestion/replay_source.py` (`if __name__ == "__main__"`) |

### Milestone 3 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A3.1 | Duplicate TCS.NS event does NOT create a second market_events row | ✅ — verified: exactly 3 rows for TCS.NS (baseline, spike, price-move), duplicate rejected |
| A3.2 | Late INFY.NS event stored but doesn't overwrite instrument_stats last_price | ✅ — verified: INFY.NS has 3 market_events rows including the late one, but instrument_stats.last_price stayed 1554.65 |

---

## Milestone 4 — Live Yahoo Finance Poller

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 4.1 | apscheduler job fetches price/volume for all 20 instruments | ✅ | `backend/app/ingestion/yahoo_source.py` (`poll_once`, `start_scheduler`) |
| 4.2 | Each instrument's fetch wrapped individually — one failure ≠ all fail | ✅ | `backend/app/ingestion/yahoo_source.py` (`poll_once`'s per-ticker try/except) |
| 4.3 | Failed instrument marked STALE, others continue as OK | ✅ | No stored STALE flag exists on `instrument_stats` in the fixed schema — staleness is derived from `last_event_time` age instead (see Decision Log, 2026-09-04); a failed fetch simply leaves the row untouched, satisfying "last known price still returned rather than omitted" |
| 4.4 | Feeds through same pipeline.process_event() as replay | ✅ | `backend/app/ingestion/yahoo_source.py` calls `app.ingestion.pipeline.process_event` |
| 4.5 | Starts when REPLAY_MODE=false; mutually exclusive with replay | ✅ | `backend/app/main.py` (`lifespan`'s `if REPLAY_MODE / else` branch) |

### Milestone 4 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A4.1 | instrument_stats update with real changing prices over several cycles | ✅ — verified: 3 real polling cycles on TCS.NS, `last_event_time` and `rolling_avg_volume` advanced each cycle; 10 real NSE tickers polled successfully in a full server run |
| A4.2 | Invalid ticker doesn't halt the other 19 instruments | ✅ — verified: temporarily seeded `FAKEXYZ.NS` between two real tickers in the poll list; its fetch failed and was skipped, both real tickers on either side still landed in `market_events` |

---

## Milestone 5 — Signal Detection and Severity Scoring

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 5.1 | price_anomaly_score(return_pct, rolling_avg_return, rolling_std_return) → 0–100 | ⬜ | — |
| 5.2 | volume_anomaly_score(volume, rolling_avg_volume) → 0–100 | ⬜ | — |
| 5.3 | sector_divergence_score(instrument_return, sector_basket_return) → 0–100 | ⬜ | — |
| 5.4 | structural_trigger_score(price, historical_high, historical_low) → 0–100 | ⬜ | — |
| 5.5 | compute_severity: weights 0.40 price, 0.25 volume, 0.15 sector, 0.20 structural | ⬜ | — |
| 5.6 | Severity bands: HIGH ≥ 70, MEDIUM ≥ 40, LOW ≥ 20, IGNORE < 20 | ⬜ | — |
| 5.7 | Signal row written only when severity ≥ 20 | ⬜ | — |
| 5.8 | Explanation JSONB stored with component scores + reasons list | ⬜ | — |
| 5.9 | Reasons are template-based, not LLM-generated | ⬜ | — |
| 5.10 | GET /api/signals/{instrument_id} returns latest explanation or 404 | ⬜ | — |

### Milestone 5 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A5.1 | Replay TCS.NS volume spike + price move → one signal row, severity ≥ 80, explanation has volume + price reasons | ⬜ |
| A5.2 | Normal-range updates produce no signal | ⬜ |

---

## Milestone 6 — Personalized Relevance Feed

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 6.1 | build_feed(user_id) reads user's watchlist instruments | ⬜ | — |
| 6.2 | Reads signals newer than user's last-seen state per instrument | ⬜ | — |
| 6.3 | Drops muted instruments | ⬜ | — |
| 6.4 | Applies priority boost for HIGH-priority items | ⬜ | — |
| 6.5 | Sorts by adjusted severity | ⬜ | — |
| 6.6 | Splits into ranked attention items + quiet count | ⬜ | — |
| 6.7 | Updates last-seen state, guarded against stale overwrites | ⬜ | — |
| 6.8 | GET /api/feed returns {last_checked, summary, items} | ⬜ | — |
| 6.9 | Empty watchlist returns empty items + zero summary, not an error | ⬜ | — |
| 6.10 | Feed.jsx polls /api/feed every 10–15 seconds | ⬜ | — |
| 6.11 | Feed.jsx subscribes to onAuthStateChange for token refresh | ⬜ | — |
| 6.12 | FreshnessBadge shows live/delayed/stale per data_quality | ⬜ | — |

### Milestone 6 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A6.1 | User watching TCS.NS sees it in feed after replay signal | ⬜ |
| A6.2 | User NOT watching TCS.NS does NOT see it | ⬜ |
| A6.3 | Second immediate feed call → TCS.NS moves from items to quiet count | ⬜ |

---

## Milestone 7 — Notification Decision Layer

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 7.1 | decide_channel(user_id, instrument_id, severity) → PUSH / IN_APP / SUPPRESS | ⬜ | — |
| 7.2 | One-push-per-instrument-per-hour cooldown via notification_log query | ⬜ | — |
| 7.3 | One notification_log row per signal per user on first evaluation | ⬜ | — |

### Milestone 7 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A7.1 | 3 test users with different settings → same signal → 3 different channels in notification_log | ⬜ |

---

## Milestone 8 — Security Pass

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 8.1 | Every protected route: user_id from verified JWT only | ⬜ | — |
| 8.2 | Every watchlist/state query scoped to user_id at DB-query level | ⬜ | — |
| 8.3 | Ingestion pipeline has no network-reachable route | ⬜ | — |

### Milestone 8 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A8.1 | User B cannot fetch/modify User A's watchlist by ID → 403 or 404, not empty | ⬜ |

---

## Milestone 9 — Polish and Demo Rehearsal

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| 9.1 | FreshnessBadge component fully styled | ⬜ | — |
| 9.2 | SignalDetail screen renders explanation breakdown | ⬜ | — |
| 9.3 | Loading and empty states on all pages | ⬜ | — |
| 9.4 | Full replay sequence narrated and timed | ⬜ | — |

### Milestone 9 Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| A9.1 | Full narrated replay run-through completes in under 5 minutes | ⬜ |

---

## Cross-Cutting Requirements

| # | Requirement | Status | Implemented In |
|---|-------------|--------|----------------|
| C.1 | All error responses use `{"error": {"code": "...", "message": "..."}}` shape | ✅ | `backend/app/models/schemas.py`, `backend/app/auth.py` |
| C.2 | Error codes: VALIDATION_ERROR, UNAUTHORIZED, NOT_FOUND, INTERNAL_ERROR | ✅ | `backend/app/models/schemas.py` |
| C.3 | Dedupe key format: `source:instrument_id:event_time_iso` | ✅ | `backend/app/ingestion/pipeline.py` (enforced as a query on the same triple, no stored column — see Decision Log) |
| C.4 | Schema re-runnable (IF NOT EXISTS everywhere) | ✅ | `db/schema.sql` |
| C.5 | Replay re-runnable without duplicates (dedupe key) | ✅ | Verified: ran the full sequence twice back to back, second run rejected all 29 events, zero new rows |
| C.6 | Backend crash recovery: no in-memory state, all in Postgres | ✅ | `backend/app/ingestion/pipeline.py` — sequence numbers, rolling stats, and last-event tracking are all derived from Postgres queries, nothing cached in process memory |
| C.7 | Demo reset: truncate events/signals/stats/notifications, keep user data | ⬜ | — |
| C.8 | Frontend never sends requests without a valid session | ✅ | `frontend/src/lib/api.js` (`apiFetch` throws `NOT_AUTHENTICATED` rather than sending) |
| C.9 | Frontend polls (not WebSockets) — deliberate simplicity choice | ⬜ | — |
| C.10 | Fixed 20-stock universe, not dynamic search | ✅ | `backend/app/main.py` (SEED_INSTRUMENTS) |
