# SignalGraph — Build Log

This file documents every action taken during the build, in chronological order, with rationale for each decision. It is the detailed companion to the ExecPlan's Progress section.

---

## Milestone 1 — Schema and Empty End-to-End Skeleton

### 2026-09-04 13:27 IST — Project bootstrap

**Starting state:** Empty workspace with only `signalgraph_execplan.md` and `AGENTS.md`.

**Goal for Milestone 1:** Create the full project skeleton (db schema, backend, frontend), get a health-check route running locally, and have the frontend call it successfully. Deployment to Render/Vercel is deferred per user decision.

---

#### Step 1: Created `db/schema.sql`

- **File:** `db/schema.sql`
- **What:** The complete PostgreSQL schema — 8 tables + 3 indexes, exactly as specified in the ExecPlan's Concrete Steps section.
- **Why:** This is the first artifact in Milestone 1. Uses `CREATE TABLE IF NOT EXISTS` everywhere so it's idempotent (safe to re-run).
- **Tables created:**
  1. `instruments` — the fixed 20-stock universe (ticker, name, sector)
  2. `watchlists` — one per user, references `auth.users(id)`
  3. `watchlist_items` — per-instrument settings (priority, muted, notifications_enabled), composite PK on (watchlist_id, instrument_id)
  4. `market_events` — every price/volume tick, with source, sequence_number, data_quality
  5. `instrument_stats` — rolling EMA statistics per instrument (avg return, std return, avg volume, last price)
  6. `signals` — detected anomalies with severity ≥ 20, explanation as JSONB, unique dedupe_key
  7. `user_instrument_state` — feed read-cursor per user+instrument (last_seen_at guards against stale overwrites)
  8. `notification_log` — audit trail of push/in-app/suppress decisions
- **Indexes:** On market_events(instrument_id, event_time DESC), signals(instrument_id, event_time DESC), notification_log(user_id, sent_at DESC) — these are the three hottest query patterns (feed reads, signal lookups, cooldown checks).

---

#### Step 2: Created `backend/requirements.txt`

- **File:** `backend/requirements.txt`
- **What:** Python dependencies.
- **Packages listed:**
  - `fastapi` — web framework (ExecPlan decision)
  - `uvicorn[standard]` — ASGI server with uvloop/httptools for performance
  - `supabase` — official Python client for DB access
  - `yfinance` — Yahoo Finance data (Milestone 4)
  - `python-dotenv` — loads `.env` files in local dev
  - `pydantic` — request/response validation (FastAPI uses this natively)
  - `apscheduler` — scheduled jobs for the live poller loop (Milestone 4)
  - `PyJWT` — **not in the original ExecPlan deps list**, added because we need to manually verify Supabase JWTs in the auth dependency. The Supabase Python client doesn't expose a token-verification helper.
  - `httpx` — required by the `supabase` Python client internally

---

#### Step 3: Created `backend/app/__init__.py`

- **File:** `backend/app/__init__.py`
- **What:** Empty package marker so Python treats `backend/app/` as a package.
- **Why:** Required for `from app.config import ...` style imports to work.

---

#### Step 4: Created `backend/app/config.py`

- **File:** `backend/app/config.py`
- **What:** Central configuration module. All env vars in one place.
- **Variables defined:**
  - `SUPABASE_URL` — defaults to `""` (will fail clearly at runtime if not set)
  - `SUPABASE_SERVICE_ROLE_KEY` — defaults to `""`
  - `SUPABASE_JWT_SECRET` — defaults to `""`
  - `FRONTEND_ORIGIN` — defaults to `http://localhost:5173` (Vite's default dev port)
  - `REPLAY_MODE` — defaults to `true` (a fresh local run is immediately demoable)
  - `POLL_INTERVAL_SECONDS` — defaults to `30`
- **Design choice:** `load_dotenv()` is called at module level so any file that imports config automatically gets `.env` values. This is standard practice for FastAPI projects.

---

#### Step 5: Created `backend/app/db.py`

- **File:** `backend/app/db.py`
- **What:** Singleton Supabase client using the service-role key.
- **Why service-role key (not anon key):** The backend needs full DB access — RLS policies shouldn't block backend operations. The anon key is only used by the frontend.
- **Placeholder handling:** If credentials aren't set yet, we use placeholder values so the module can be imported without crashing. Actual DB calls will fail with a clear HTTP error at runtime, not a cryptic import error.

---

#### Step 6: Created `backend/app/auth.py`

- **File:** `backend/app/auth.py`
- **What:** FastAPI dependency `get_current_user_id(request) -> str`.
- **How it works:**
  1. Reads `Authorization: Bearer <token>` header
  2. Decodes JWT using PyJWT with HS256 algorithm and `audience="authenticated"` (Supabase's default)
  3. Extracts the `sub` claim as the user UUID
  4. Returns the UUID string
- **Error handling:** Three distinct 401 responses for missing header, expired token, and invalid token — all using the `{"error": {"code": "UNAUTHORIZED", "message": "..."}}` shape specified in the ExecPlan's Validation and Acceptance section.
- **Security note:** The user ID is NEVER taken from any client-supplied body field. It's always extracted from the verified JWT. This is the foundation for Milestone 8's security pass.

---

#### Steps remaining for Milestone 1:
- [x] Create Pydantic schemas (`backend/app/models/schemas.py`)
- [x] Create stub modules for ingestion, signals, relevance, notifications
- [x] Create route stubs (`watchlists.py`, `feed.py`, `signals.py`)
- [x] Create `backend/app/main.py` with health-check route + CORS
- [x] Create seed script for the 20 demo instruments
- [x] Initialize the Vite React frontend
- [x] Create frontend file structure (Login, Watchlist, Feed, SignalDetail, FreshnessBadge, supabaseClient)
- [x] Wire frontend to call the backend health-check
- [ ] Verify everything runs locally (backend ✅, frontend pending npm)
- [ ] Update ExecPlan Progress section

---

#### Step 7: Created `backend/app/models/schemas.py`

- **File:** `backend/app/models/__init__.py` + `backend/app/models/schemas.py`
- **What:** All Pydantic request/response models for every HTTP endpoint.
- **Models defined:**
  - `ErrorDetail` / `ErrorResponse` — standard `{"error": {"code": "...", "message": "..."}}` shape
  - `CreateWatchlistRequest` / `CreateWatchlistResponse` — POST /api/watchlists
  - `WatchlistItemOut` / `WatchlistOut` — GET /api/watchlists response
  - `AddWatchlistItemRequest` — POST /api/watchlists/{id}/items
  - `UpdateWatchlistItemRequest` — PATCH (optional priority + muted)
  - `FeedSummary` / `FeedItem` / `FeedResponse` — GET /api/feed
  - `SignalExplanation` — GET /api/signals/{instrument_id}
  - `HealthResponse` — GET /api/health
- **Design note:** `schemas.py` re-exports from `__init__.py` so both `from app.models import X` and `from app.models.schemas import X` work, matching the ExecPlan's specified import path.

---

#### Step 8: Created all stub modules

Created 10 stub files for modules that will be implemented in later milestones:

| File | Milestone | Purpose |
|------|-----------|---------|
| `backend/app/ingestion/__init__.py` | — | Package marker |
| `backend/app/ingestion/pipeline.py` | 3 | Shared validation/dedup/ordering/EMA logic |
| `backend/app/ingestion/replay_source.py` | 3 | Scripted demo event sequence |
| `backend/app/ingestion/yahoo_source.py` | 4 | Live Yahoo Finance poller |
| `backend/app/signals/__init__.py` | — | Package marker |
| `backend/app/signals/detectors.py` | 5 | Four anomaly detection functions |
| `backend/app/signals/scoring.py` | 5 | Weighted severity scoring |
| `backend/app/relevance/__init__.py` + `feed.py` | 6 | Personalized feed builder |
| `backend/app/notifications/__init__.py` + `decision.py` | 7 | Channel decision logic |

Each stub contains a docstring documenting the exact interface contract from the ExecPlan (function signatures, parameters, return types) so future implementation has a clear spec.

---

#### Step 9: Created route stubs

| File | Prefix | Endpoints |
|------|--------|-----------|
| `backend/app/routes/watchlists.py` | `/api/watchlists` | POST, GET, POST items, PATCH items, DELETE items |
| `backend/app/routes/feed.py` | `/api` | GET /api/feed |
| `backend/app/routes/signals.py` | `/api/signals` | GET /api/signals/{instrument_id} |

Each declares an `APIRouter` that `main.py` mounts. Actual route handlers deferred to their respective milestones.

---

#### Step 10: Created `backend/app/main.py`

- **What:** The FastAPI application entry point.
- **Key features:**
  - Creates FastAPI app with title, description, version
  - CORS middleware restricted to `FRONTEND_ORIGIN` only
  - Mounts all three route modules (watchlists, feed, signals)
  - `GET /api/health` endpoint returning `{status, version, replay_mode}`
  - `seed_instruments()` on startup — upserts all 20 demo stocks (idempotent via `on_conflict="ticker"`)
  - Lifespan context manager (not deprecated `on_event`) for startup/shutdown hooks
  - Startup prints whether replay or live mode is active (placeholders for Milestones 3/4)
- **Seed data:** All 20 NSE stocks with full names and sectors, exactly matching the ExecPlan's Context and Orientation section.

---

#### Step 11: Initialized Vite React frontend

- **Command:** `npx -y create-vite@latest frontend --template react`
- **Result:** Scaffolded a standard Vite + React project in `frontend/`
- **Dependencies installed:** react, react-dom, @supabase/supabase-js (via separate npm install)

---

#### Step 12: Created frontend source files

| File | Purpose |
|------|---------|
| `frontend/src/lib/supabaseClient.js` | Supabase browser client singleton (anon key) |
| `frontend/src/lib/api.js` | Centralized fetch wrapper: `apiFetch` (authenticated) + `publicFetch` (unauthenticated) |
| `frontend/src/pages/Login.jsx` | Magic-link login form |
| `frontend/src/pages/Watchlist.jsx` | Stub — Milestone 2 |
| `frontend/src/pages/Feed.jsx` | Stub — Milestone 6 |
| `frontend/src/pages/SignalDetail.jsx` | Stub — Milestone 5/9 |
| `frontend/src/components/FreshnessBadge.jsx` | Live/Stale badge with pulsing dot animation |
| `frontend/src/App.jsx` | Main component: auth state, routing, health-check display |

**App.jsx key behaviors:**
- Checks existing Supabase session on mount
- Subscribes to `onAuthStateChange` for mid-session token refresh
- Calls `/api/health` on mount and displays result (Milestone 1 proof)
- Shows Login page when no session, main app when authenticated
- Client-side routing between Feed, Watchlist pages
- Logout via `supabase.auth.signOut()`

---

#### Step 13: Created CSS design system (`frontend/src/index.css`)

- **Font:** Inter from Google Fonts (300–700 weights)
- **Theme:** Premium dark mode with design tokens (CSS custom properties)
- **Color palette:**
  - Background layers: `#0a0e1a` → `#111827` → `#1a2035` → `#1f2a45`
  - Accent: Indigo `#6366f1`, Green `#22c55e`, Amber `#f59e0b`, Red `#ef4444`
  - All accents have matching glow/bg variants for badges and alerts
- **Components styled:** Nav, Login card, health banner, freshness badge, loading spinner, page containers
- **Animations:** `fadeIn` (login card), `slideUp` (health status), `spin` (loading spinner), `pulse` (live badge dot)
- **Responsive:** Mobile breakpoint at 768px

---

#### Step 14: Created environment files

| File | Purpose |
|------|---------|
| `frontend/.env` | VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY (blank), VITE_API_BASE_URL=http://localhost:8000 |
| `backend/.env` | SUPABASE_URL, keys (blank), FRONTEND_ORIGIN=http://localhost:5173, REPLAY_MODE=true, POLL_INTERVAL_SECONDS=30 |
| `.gitignore` | Excludes .env files, __pycache__, node_modules, IDE files |

---

#### Step 15: Installed backend dependencies and verified health endpoint

- **Command:** `pip install -r requirements.txt` — all 22 packages installed successfully
- **Command:** `uvicorn app.main:app --port 8000` — server started without errors
- **Verification:** `curl http://localhost:8000/api/health` returned:
  ```json
  {"status": "ok", "version": "0.1.0", "replay_mode": true}
  ```
- **Note:** Instrument seeding was skipped (expected — no Supabase credentials configured yet). Server printed: `[SEED] Skipped instrument seeding (DB not available)` — this is the designed graceful fallback.

---

## Milestones 2-9 — Summary

Implemented and verified in a single later session (2026-09-04), after real Supabase credentials were configured. Full narrative detail — what was built, every bug found and fixed, every decision made, and the exact verification evidence for each milestone's Proof of Success — lives in `signalgraph_execplan.md`'s Progress, Surprises and Discoveries, Decision Log, and Outcomes and Retrospective sections; this entry is a pointer, not a duplicate.

Headline results: watchlist CRUD and login (Milestone 2) work end to end, including a real `HTTPException` error-shape bug fixed along the way. The ingestion pipeline (Milestone 3) correctly rejects exact-duplicate events and stores late-arriving events without corrupting `instrument_stats`, verified by direct query against a real replay run. The live Yahoo Finance poller (Milestone 4) pulls real NSE data and isolates per-instrument failures — this surfaced a real-world data issue (TATAMOTORS.NS delisted on Yahoo post-demerger; swapped to TMPV.NS). Signal detection (Milestone 5) went through two rounds of real bugs — comparing ticks against post-update rather than pre-update rolling stats, and a bad EMA bootstrap — both caught only by running the actual replay and checking for false positives on ordinary ticks, not by code review. The personalized feed (Milestone 6), notification decision layer (Milestone 7), and a live cross-user security test with a throwaway Supabase account (Milestone 8) all passed their stated acceptance criteria against real data. Frontend pages (Feed, SignalDetail, Watchlist) were built out against the real API responses; visual browser verification was left to the user since no headless-browser tooling was available in this environment.
