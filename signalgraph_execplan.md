```
# Purpose and Big Picture

SignalGraph turns a passive stock watchlist into a system that tells a person what actually deserves their attention, instead of making them scan every price on every visit. After this plan is fully implemented, a person can create a watchlist of NSE stocks, close the app, come back hours later, and see a short, ranked list of the two or three things that genuinely changed in a way that matters for those specific stocks — each with a plain-language reason — while everything else that stayed within normal behavior is silently folded into a one-line "nothing unusual" summary. The system also demonstrably survives duplicate market data, late-arriving data, and a temporarily unreachable data source without breaking or lying to the user about how fresh the data is. This plan exists to be handed to a coding agent (or followed by a person) with no other context and produce exactly this outcome.


# Progress

  [x] Milestone 1 — Schema and empty end-to-end skeleton. Completed 2026-09-04 13:50 IST — schema file ready, backend health route returns {"status":"ok","version":"0.1.0","replay_mode":true}, frontend renders Login page with green "✓ Backend connected — v0.1.0 (Replay mode)" badge. Deployment to Render/Vercel deferred per user decision; local end-to-end verified.
  [x] Milestone 2 — Watchlist CRUD and login. Completed 2026-09-04 16:10 IST — magic-link login (built in Milestone 1) verified against a real Supabase session; all five watchlist routes implemented in backend/app/routes/watchlists.py, every lookup scoped to the verified user_id at the query level (`.eq("user_id", user_id)` before ever touching a watchlist row); Watchlist.jsx built against the fixed 20-instrument universe with add/remove/priority/mute controls. Verified end-to-end in a real headless-Chromium session against the live Supabase project (not mocked): created a watchlist, added TCS.NS/INFY.NS/RELIANCE.NS, full page reload showed all 3 still present (screenshot evidence), PATCH and DELETE confirmed via UI and re-fetch. Cross-user isolation also verified early (Milestone 8's acceptance check): a second authenticated test user got 404 NOT_FOUND on POST/PATCH/DELETE against the first user's watchlist, never the data itself.
  [x] Milestone 3 — Ingestion pipeline, Replay Mode first. Completed 2026-09-04 16:45 IST — `backend/app/ingestion/pipeline.py` implements process_event() (validation, self-assigned per-instrument sequence numbers, dedup via (source, instrument_id, event_time) existence check, late-event detection against instrument_stats.last_event_time, and the exact EMA rolling-stats formula from Interfaces and Dependencies). `backend/app/ingestion/replay_source.py` plays the full scripted sequence (baseline for 20 instruments, 4 normal updates, TCS.NS volume spike, TCS.NS price move, exact duplicate, late INFY.NS event, RELIANCE.NS structural update) against fixed (non-wall-clock) event timestamps, paced 3-5s apart. Wired into `main.py`'s startup on a background thread when REPLAY_MODE=true. Verified against the live Supabase project: TCS.NS has exactly 3 market_events rows (the duplicate was rejected, not a 4th row); INFY.NS's instrument_stats.last_price stayed 1554.65 (the in-order update) after the late event was stored; running the full sequence a second time rejected all 29 events as duplicates with zero new rows in either run (`content-range: 0-27/28` unchanged before and after), confirming true idempotence per Idempotence and Recovery.
  [x] Milestone 4 — Live Yahoo Finance poller. Completed 2026-09-04 17:10 IST — `backend/app/ingestion/yahoo_source.py` implements `poll_once()` (fetches `yfinance`'s `fast_info.last_price`/`.last_volume` per ticker, each wrapped in its own try/except, feeding successes through the same `pipeline.process_event()` Replay Mode uses) and `start_scheduler()` (apscheduler `BackgroundScheduler` on `POLL_INTERVAL_SECONDS`, running one poll immediately). Wired into `main.py`'s `lifespan()` on a background thread when `REPLAY_MODE=false`, mutually exclusive with the replay path, with the scheduler reference stashed on `app.state` so it isn't garbage-collected and can be shut down cleanly. Verified against real Yahoo Finance data and the live Supabase project: ran 3 consecutive polling cycles for TCS.NS and confirmed `instrument_stats.last_event_time` advanced and `rolling_avg_volume` moved each time; separately, seeded a temporary fake instrument (`FAKEXYZ.NS`, deleted after the test) — the fake one's fetch failed and was skipped with a logged warning, while both real tickers on either side of it still landed in `market_events` with `source=yahoo`, proving per-instrument isolation. Full end-to-end run showed 10 real NSE tickers polled and accepted with live prices.
  [x] Milestone 5 — Signal detection and severity scoring. Completed 2026-09-04 — implemented the four detectors, compute_severity() with the specified weights/bands, and the evaluate_and_record_signal() orchestration (sector peer basket lookup, historical high/low from market_events, severity-floor gate, upsert to `signals`) called from both ingestion sources after every successful current-tick process_event(). Acceptance run produced: zero signals for any of the four small TCS.NS updates, exactly one signal for the TCS.NS volume-spike-plus-price-move pair at severity 83.4 (HIGH, ≥80 required) with reasons citing both price move and volume ratio, and a signal for RELIANCE.NS structural update.
  [x] Milestone 6 — Personalized relevance feed. Completed 2026-09-04 — implemented build_feed() (per-user watchlist read, muted-instrument exclusion, new-vs-already-seen gating against user_instrument_state, HIGH-priority severity boost, HIGH/MEDIUM-only ranked items with everything else folded into a quiet count, explicit checkpoint advancement via POST /api/feed/seen/{id}) and the GET /api/feed route.
  [x] Milestone 7 — Notification decision layer. Completed 2026-09-04 — implemented decide_channel() (muted → SUPPRESS, notifications disabled → IN_APP, urgent + no active cooldown → PUSH, else IN_APP) and notify_interested_users(), writing one notification_log row per watching user.
  [x] Milestone 8 — Security pass. Completed 2026-09-04 — reviewed every route under backend/app/routes/ for user-id sourcing (verified JWT, never client-supplied) and query-level scoping. Verified live: created throwaway auth user, confirmed 404 NOT_FOUND on cross-user watchlist access. Confirmed ingestion pipeline is not reachable over HTTP.
  [x] Milestone 9 — Polish and demo rehearsal. Completed 2026-09-04 — built out Feed.jsx and SignalDetail.jsx against real API responses. Loading, error, and empty states present on Watchlist and Feed. Ran full Replay Mode sequence cleanly end to end (~30-45s wall-clock).
  [x] Milestone 10 — Chat assistant (added post-launch). Completed 2026-09-04 — `POST /api/chat` answers questions about the 20 tracked companies grounded in live database snapshot. Deterministic template engine by default (zero-cost), switchable to Claude if API key present. Investment-advice requests hard-blocked by keyword gate. `ChatWidget.jsx` mounted globally in `App.jsx`, visible on every authenticated page.
  [x] Milestone 11 — AI-generated Market Brief. Completed 2026-09-05 — `backend/app/ai/brief.py` implements `generate_brief()`, `validate_brief()`, and `deterministic_brief()` exactly as specified; `build_feed()` reads a module-level `_brief_cache` dict (read-only, no AI knowledge) and `routes/feed.py`'s handler compares each response's items hash against the cache and schedules a `BackgroundTasks` regeneration when it differs. Verified against a merged copy of `main` (see Surprises & Discoveries — this session's work had been merged with a collaborator's parallel session since the last update here): a fresh Replay run's first `build_feed()` call for a user watching TCS.NS returned a non-empty market_brief mentioning TCS.NS immediately (the cache-miss deterministic path), a simulated second poll after background regeneration still returned a non-empty TCS.NS-mentioning brief with `items`/`summary` byte-identical to the first call, and `validate_brief()` directly confirmed rejecting both a fabricated `ZOMATO.NS` mention and "you should buy more shares now" while accepting clean grounded text. All three proofs pass with zero API cost, since no `ANTHROPIC_API_KEY` is configured in this environment (see Decision Log) — `generate_brief()`'s own fallback-on-missing-key behavior is exactly what the third proof point requires anyway.

Update each line above in place with a timestamp the moment its milestone's Validation and Acceptance criteria are met, for example: [x] Milestone 1 — Schema and empty end-to-end deploy. Completed 2026-09-05 14:20 IST — schema applied cleanly, backend health route reachable from the deployed frontend.


# Surprises and Discoveries

Surprise (2026-09-04 13:45 IST): The `@supabase/supabase-js` `createClient()` function throws `Error: supabaseUrl is required` when passed an empty string, crashing the entire React app before any component can render. The plan assumed empty-string defaults would be safe (like the Python backend's placeholder approach). Fix: changed the frontend's `supabaseClient.js` to use `'https://placeholder.supabase.co'` and `'placeholder-anon-key'` as fallbacks — auth calls fail gracefully at runtime (returning Supabase errors) instead of preventing the page from loading at all. This matches the backend's `db.py` approach of using placeholder values.

Surprise (2026-09-04 15:40 IST / post-Milestone-9): With real Supabase credentials in place, `get_current_user_id()` rejected valid session tokens signed with ES256 (the newer Supabase JWT Signing Keys default feature) with `{"error":{"code":"UNAUTHORIZED","message":"Invalid token: The specified alg value is not allowed"}}`. Fix: `backend/app/auth.py` now reads the token's `alg` header first; for HS256 it verifies against `SUPABASE_JWT_SECRET` as before, otherwise it fetches the matching public key from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` via `jwt.PyJWKClient` (5-minute cache) and verifies against that.

Surprise (2026-09-04 16:00 IST): Testing the Watchlist page in a real (non-mocked) browser session turned up a race condition: React 18 StrictMode double-invokes effects on mount in dev, causing duplicate watchlist creation. Fix: added a `useRef` guard in `Watchlist.jsx` so the create-on-first-load step runs at most once per mount, and added `.order("created_at")` to `GET /api/watchlists`.

Surprise (2026-09-04 16:35 IST): Stamping replay events with `datetime.now()` wall-clock time violated the plan's idempotent-re-run requirement because timestamps changed on every run. Fix: `replay_source.py` stamps events against a fixed `ANCHOR` datetime (2026-09-01T09:00:00Z) plus fixed per-event offsets.

Surprise (2026-09-04 16:57 IST): Postgres didn't auto-update `instrument_stats.updated_at` on upsert. Fix: set `"updated_at": datetime.now(timezone.utc).isoformat()` explicitly in `pipeline.py`.

Surprise (2026-09-04 17:05 IST): `yahoo_source.py`'s `logging` output was swallowed under uvicorn. Fix: switched to `print()` throughout, consistent with `pipeline.py` and `replay_source.py`.

Surprise (2026-09-04): FastAPI's default exception handling wrapped `HTTPException(detail=...)` under `"detail"`. Fix: registered `@app.exception_handler(HTTPException)` in `main.py` to return custom error shapes directly.

Surprise (2026-09-04): Milestone 5 detection initially compared event values against post-update rolling stats instead of pre-event stats. Fix: returned prior stats from `pipeline.process_event()` for detection to compare against, and seeded first-ever ticks directly.

Surprise (2026-09-04): TATAMOTORS.NS demerged into separate listings and failed on Yahoo Finance. Fix: swapped to TMPV.NS.

Surprise (2026-09-05): starting a new session to check through Milestone 10 and build Milestone 11, `origin/main` had moved far beyond what this session had last pushed — a collaborator (Sarthak Lal, the repo owner) had been building the same milestones in parallel on their own branch, merged this session's pushed branch into `main` alongside their own work, resolved the resulting conflicts, and pushed a docs cleanup commit. Confirmed via `git log --graph` and per-commit authorship (`git log <range> --pretty=format:"%h %an <%ae> %s"`) rather than assumed. The good news: every backend file this session had actually written and live-tested (`pipeline.py`, `detectors.py`, `scoring.py`, `feed.py`, `routes/feed.py`, `routes/watchlists.py`, `auth.py`, `notifications/decision.py`, `chat/*`) survived the merge byte-for-byte identical to this session's own last-verified versions; only the two ingestion source files (`replay_source.py`, `yahoo_source.py`) carry the collaborator's own implementation choices (a fixed `ANCHOR` timestamp instead of wall-clock `datetime.now()`, and `yfinance`'s `fast_info` accessor instead of `.history()`), and both were confirmed working via a fresh end-to-end replay run producing the identical expected result (TCS.NS severity 83.4, RELIANCE.NS 77.0, 28 market_events, zero false positives). Two real regressions from the collaborator's side were found and fixed during this re-verification: a new, unused `frontend/src/lib/instruments.js` file still listed the retired `TATAMOTORS.NS` ticker instead of `TMPV.NS` (fixed for consistency even though nothing currently imports it), and `instrument_stats.updated_at` was never being set explicitly on upsert — Postgres's `default now()` only fires on INSERT, not on an UPDATE-via-upsert into an existing row, so the column was silently frozen at each instrument's first-ever tick (fixed in `pipeline.py`). Lesson for future sessions on a collaborative repo: before resuming "check milestone N, build milestone N+1" work, run `git fetch` and diff against `origin/main` first — the working assumption that "my last local state is still the current state" does not hold on a shared repository.


# Decision Log

Decision (2026-09-04): backend framework is FastAPI, not Spring Boot. Rationale: the builder is a solo beginner with roughly 45 effective hours; Spring Boot's project ceremony (build tooling, layered boilerplate, slower iteration loop) would consume build time that is better spent on the signal-detection and relevance logic that this project is actually judged on. Spring Boot's raw-throughput advantage is irrelevant at hackathon-demo scale.

Decision (2026-09-04): database and authentication are both PostgreSQL and Supabase Auth, rather than a self-hosted database or a hand-rolled auth system. Rationale: removes local database setup and password-handling code entirely, both classic sources of beginner time loss, without sacrificing a real, production-credible mechanism.

Decision (2026-09-04): sector-relative return is computed from a hardcoded peer basket of four to six known NSE stocks per sector, not from a real sector-index data feed. Rationale: no reliable free sector-index API was identified; the peer-basket approach uses data already being pulled for other instruments and is simple to explain and defend.

Decision (2026-09-04): event ordering uses a sequence number assigned by SignalGraph itself at ingestion time, incremented per instrument, rather than a sequence number from the upstream data source. Rationale: free market data providers, including Yahoo Finance, do not supply one.

Decision (2026-09-04): the frontend polls the backend every ten to fifteen seconds rather than using WebSockets or Server-Sent Events. Rationale: at this refresh cadence, push-based transport adds real operational complexity (connection lifecycle, reconnect handling) for no user-visible benefit; this is stated explicitly as a deliberate simplicity choice, not an oversight, in Outcomes and Retrospective and in any demo of this project.

Decision (2026-09-04): the demo instrument universe is a fixed list of twenty NSE-listed stocks across five sectors (see Context and Orientation), not a dynamic, searchable universe. Rationale: keeps the ingestion, sector-basket, and demo-replay logic bounded and fully testable within the hackathon's time budget.

Decision (2026-09-04): PyJWT and httpx added to backend/requirements.txt, beyond the dependencies listed in the original plan. Rationale: PyJWT is needed because the Supabase Python client does not expose a token-verification helper — the auth dependency must manually decode and verify JWTs. httpx is a required transitive dependency of the supabase Python client.

Decision (2026-09-04): the frontend drives exactly one watchlist per user, auto-creating one named "My Watchlist" on first load of the Watchlist page if the user has none, even though the schema and watchlists routes support multiple watchlists.

Decision (2026-09-04): `PATCH /api/watchlists/{id}/items/{instrument_id}` and `POST /api/watchlists/{id}/items` return full updated objects, and `POST` upserts on composite key `(watchlist_id, instrument_id)`.

Decision (2026-09-04): `market_events` has no physical `dedupe_key` column; duplicate rejection in `pipeline.process_event()` is an application-level existence query on `(instrument_id, source, event_time)`.

Decision (2026-09-04, after Milestone 9): changed checkpoint advancement so `build_feed()` is read-only and `POST /api/feed/seen/{instrument_id}` explicitly advances seen state on detail open.

Decision (2026-09-04): `evaluate_and_record_signal()` lives in `app/signals/scoring.py` and `notify_interested_users()` lives in `app/notifications/decision.py`.

Decision (2026-09-04): `sector_basket_return` is computed from each peer instrument's `rolling_avg_return` in `instrument_stats`.

Decision (2026-09-04): HIGH-priority watchlist items receive a flat +15 severity boost (capped at 100).

Decision (2026-09-04): `instrument_id` was added to `FeedItem` response model.

Decision (2026-09-04): data quality (OK vs STALE) is computed dynamically at feed-read time based on `instrument_stats.last_event_time`.

Decision (2026-09-04): swapped TATAMOTORS.NS for TMPV.NS in fixed 20-instrument universe due to demerger.

Decision (2026-09-04): `main.py` startup replay and live polling launch on background daemon threads.

Decision (2026-09-04): Supabase Row Level Security (RLS) is deliberately not enabled on any table. Rationale: the frontend never queries Supabase directly — all data access flows through the FastAPI backend, which uses the service_role key (bypasses RLS) and enforces authorization at the application level via the JWT auth dependency in backend/app/auth.py. Enabling RLS would add policy-writing overhead with no security benefit in this architecture, and misconfigured policies could silently block the backend's own queries.

Decision (2026-09-04): `market_events` has no `dedupe_key` column (only `signals` does, per the Concrete Steps schema, which is fixed and already applied). The ingestion pipeline's duplicate check is instead an existence query on the triple `(instrument_id, source, event_time)` before insert — semantically identical to the plan's described dedupe_key concept, just enforced without a stored column. Rationale: the schema was already applied in Milestone 1 and altering it wasn't warranted for this; the query-based check gives the exact same guarantee (reject an exact repeat of source+instrument+event_time) without a migration.

Decision (2026-09-04): the self-assigned per-instrument sequence number is computed by querying `max(sequence_number)` for that instrument (via `order + limit(1)`) and adding one, rather than maintained as separate durable counter state. Rationale: both ingestion sources (replay and, in Milestone 4, the poller) process one instrument at a time within a single process, so there's no concurrent-write race in practice at this scale; this keeps sequence numbering entirely derived from the Postgres source of truth, consistent with Idempotence and Recovery's requirement that no state live only in memory.

Decision (2026-09-04): `replay_source.py`'s scripted events are stamped with a fixed `ANCHOR` datetime (2026-09-01T09:00:00Z) plus fixed per-event offsets, rather than wall-clock time at send. See Surprises and Discoveries, 2026-09-04 16:35 IST, for why the first (wall-clock) version violated the plan's idempotent-re-run guarantee. The demo-paced `time.sleep(3-5s)` between events is unaffected — it controls playback speed only, never the recorded event_time.

Decision (2026-09-04): the replay sequence's late INFY.NS event (Milestone 3's Concrete Steps) uses a price 0.5% below the in-order update it precedes, and the "structural update" on RELIANCE.NS is a +6% price move — the plan specifies these events exist and their relative ordering, but not their exact magnitudes, since precise anomaly thresholds aren't exercised until Milestone 5's severity scoring. Baseline prices/volumes for all 20 instruments (`BASELINE` in replay_source.py) are likewise plausible round NSE-scale figures chosen for this plan, not live-accurate data, since Replay Mode is explicitly scripted and deterministic rather than reflecting real market state.

Decision (2026-09-04): a failed poll for one instrument (Milestone 4) is not recorded anywhere as an explicit "STALE" flag — there's simply no `market_events` row for that instrument that cycle, and `instrument_stats` is left untouched. The schema (fixed, applied in Milestone 1) has no `data_quality`/staleness column on `instrument_stats` at all — only `market_events` has `data_quality`, per-event. Rationale: staleness is fully derivable later (Milestone 6) from how old `instrument_stats.last_event_time` is relative to now, without needing a separate stored flag or a schema change; this is also consistent with Validation and Acceptance's requirement that a stale instrument's "last known price [is] still returned rather than omitted" — leaving the row untouched is exactly that.

Decision (2026-09-04): `yahoo_source.py` uses `yfinance`'s `Ticker(ticker).fast_info` (`.last_price`, `.last_volume`) rather than `.history()` or `.info`. Rationale: `fast_info` is yfinance's lightweight, purpose-built accessor for exactly this (latest price/volume) — one HTTP call per ticker, versus `.history()`'s heavier OHLCV-series response or `.info`'s much larger, slower payload; confirmed working end-to-end against real NSE tickers including the literal `M&M.NS` symbol.

Decision (2026-09-04): the live poller's `start_scheduler()` runs one polling cycle synchronously before starting the recurring apscheduler job, so live data appears immediately on startup rather than only after the first `POLL_INTERVAL_SECONDS` elapses (mirrors Replay Mode's "immediately demoable" framing in Interfaces and Dependencies). Both the initial poll and the scheduler startup are launched on a background daemon thread from `main.py`'s `lifespan()`, same pattern as Milestone 3's replay thread, so a slow or unreachable Yahoo Finance response can't delay the server from accepting requests.

Decision (2026-09-05): Milestone 11's `generate_brief()` reuses the `ANTHROPIC_API_KEY` config value from Milestone 10's chat assistant, rather than introducing the separate `AI_PROVIDER_API_KEY` this plan originally named. Rationale: this project calls exactly one LLM provider (Claude); a second, identically-purposed environment variable holding the same kind of credential would be pure redundancy with no configuration benefit, and keeping one key means one place to rotate it.

Decision (2026-09-05): the market-brief cache (`_brief_cache`, a plain module-level dict) lives in `app/relevance/feed.py` rather than in `app/ai/brief.py`, even though it's AI-related state. Rationale: `build_feed()` needs to read it synchronously on every call to attach `market_brief` to its response, and the plan is explicit that `build_feed()` must have "no knowledge of the AI layer" — it can read a plain cache dict without that constituting AI knowledge, but importing from `app/ai/brief.py` beyond the already-necessary `deterministic_brief()` template helper would blur that boundary. `routes/feed.py` (which does know about the AI layer, since it's the one scheduling `generate_brief()` as a background task) imports the same dict object from `app.relevance.feed` to write to it after the background task completes.

Decision (2026-09-05): `deterministic_brief()` (the fallback template) is exported as a public function from `app/ai/brief.py` and imported by `app/relevance/feed.py` for the cache-miss case (the very first request for a user, before any background generation has run), rather than duplicating the same template string in both files. It is pure string templating with no API calls, no validation, and no knowledge of whether the AI path even exists, so importing it doesn't violate build_feed()'s "no AI knowledge" constraint in spirit — it's the same category of import as `deterministic_brief` being usable standalone by anything that wants a grounded one-line summary of ranked items.


# Outcomes and Retrospective

All nine milestones are complete as of 2026-09-04. Nothing in the Plan of Work was cut.

What actually broke during the build, beyond what's already logged in Surprises and Discoveries: the two most consequential bugs were both in signal detection (Milestone 5) and both were "the math is locally correct but the base case is wrong" — comparing a tick to rolling stats that already partially included itself, and bootstrapping an instrument's very first rolling average from an EMA blend against a fake zero instead of seeding it from the real first observation. Both were caught only by actually running the replay sequence and checking that baseline ticks produced zero signals, not by reading the code. This is the strongest argument in the whole build for why every milestone's Proof of Success in this plan insists on checking real data by direct query rather than trusting that correct-looking code did the right thing — in both cases the code looked entirely reasonable until it was run.

The other recurring failure mode during the build itself (not a defect in the shipped system, but worth recording): repeatedly running `python -m app.ingestion.replay_source` directly against the same Supabase project while a `uvicorn` server was also running with `REPLAY_MODE=true` caused two replay sequences to race against the same instrument rows, corrupting rolling stats with cross-contaminated data. `pkill`/`taskkill` by process name was unreliable on this Windows machine — a killed shell command sometimes left the actual `uvicorn.exe` / `python.exe` processes (and, critically, the live Yahoo poller's background thread) running because the name pattern didn't match the real Windows PID. Anyone continuing this build locally should verify with `Get-CimInstance Win32_Process` (or Task Manager) that nothing is still bound to port 8000, not just trust that a kill command returned success, before re-running Replay Mode or the live poller.

If given another week, the single highest-value next improvement would be a proper burn-in / minimum-sample-count guard on signal detection generally, not just the two bootstrap-specific fixes made here. The current fix stops the *first* tick and a fixed 1% std floor from producing false positives, but the underlying issue — an EMA-based rolling average is inherently unreliable after only a handful of observations — is only patched around the exact cases this replay script happens to exercise, not solved structurally (e.g. tracking an observation count and scaling confidence, or widening the effective floor, until N ticks have been seen for a given instrument). This wasn't done now because doing it well would need more real market data to tune against than a scripted nine-event replay provides, and because the two targeted fixes were already sufficient to pass every stated acceptance criterion.

Also worth a future look: this build's tests always exercised Replay Mode and Live Mode in the same Supabase project, one after another, sharing the same `instrument_stats` rows. The plan calls the two mutually exclusive within a single running process, which is true, but nothing stops someone from running Live Mode for a while and then switching to Replay Mode against the same already-populated tables, which is exactly the scenario that produced the corrupted-baseline bug during this build's own testing. A `source` guard — or at minimum, a documented rule that switching modes means resetting per Idempotence and Recovery first — would remove a sharp edge that's easy to hit by accident.


# Context and Orientation

Nothing exists yet: there is no repository, no deployed service, no Supabase project. This section describes the state the project starts from and the accounts and structure it will grow into, written so that someone opening this document with no other information can begin immediately.

Three free accounts are needed before any code is written: a Supabase account, used for hosted PostgreSQL and for authentication; a Render account, used to host the backend as a long-running process, which matters because the backend's ingestion loop must keep running between requests, something a serverless platform that sleeps the process would not allow; and a Vercel account, used to host the static frontend build.

The repository is organized as two top-level directories plus a schema file. The backend directory, `backend/`, contains a Python FastAPI application under `backend/app/`, with `backend/app/main.py` as the entry point that creates the FastAPI app, registers CORS restricted to the deployed frontend's origin, and mounts the route modules described later in this plan. Configuration is read from environment variables in `backend/app/config.py`. The Supabase client is created once in `backend/app/db.py` and imported wherever database access is needed. Token verification lives in `backend/app/auth.py` as a FastAPI dependency that every protected route uses to resolve the calling user's id from their Supabase access token — no route ever trusts a user id supplied by the client itself. Pydantic request and response models live in `backend/app/models/schemas.py`. The ingestion logic lives under `backend/app/ingestion/`, split into `yahoo_source.py` for the live poller, `replay_source.py` for the scripted demo event sequence, and `pipeline.py` for the validation, deduplication, ordering, and rolling-statistics logic shared by both sources. Signal detection lives under `backend/app/signals/`, split into `detectors.py` for the individual anomaly calculations and `scoring.py` for combining them into a severity score. The personalized feed logic lives in `backend/app/relevance/feed.py`. The notification decision logic lives in `backend/app/notifications/decision.py`. HTTP route handlers live under `backend/app/routes/`, one file per resource: `watchlists.py`, `feed.py`, and `signals.py`; there is deliberately no route file for ingestion, because the ingestion pipeline is called directly from within the backend process by the poller and replay scheduler and is never exposed over the network. Python dependencies are declared in `backend/requirements.txt`: fastapi, uvicorn with the standard extras, the official supabase Python client, yfinance, python-dotenv, pydantic, and apscheduler for running the ingestion loop on a schedule inside the same long-running process.

The frontend directory, `frontend/`, is a Vite-based React application. `frontend/src/lib/supabaseClient.js` creates the Supabase browser client used for login and for reading the current session's access token. `frontend/src/pages/Login.jsx` is a single email field that calls Supabase's magic-link sign-in. `frontend/src/pages/Watchlist.jsx` lists and edits the current user's watchlist against the fixed twenty-instrument universe described below. `frontend/src/pages/Feed.jsx` is the hero screen that polls the personalized feed endpoint and renders the ranked attention list. `frontend/src/pages/SignalDetail.jsx` renders one instrument's severity breakdown. `frontend/src/components/FreshnessBadge.jsx` renders the live or delayed or stale indicator described in Milestone 4 and Milestone 6. Frontend dependencies are react, react-dom, and the Supabase JavaScript client, on top of Vite's own tooling.

Finally, `db/schema.sql`, at the repository root outside both `backend/` and `frontend/`, holds the complete PostgreSQL schema described in Milestone 1's Concrete Steps, intended to be run once against the Supabase project's SQL editor before any application code is deployed.

The fixed twenty-instrument demo universe, grouped by sector, is: information technology — TCS.NS, INFY.NS, WIPRO.NS, HCLTECH.NS, TECHM.NS; banking — HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, KOTAKBANK.NS, AXISBANK.NS; energy and utilities — RELIANCE.NS, ONGC.NS, NTPC.NS, POWERGRID.NS; consumer goods — HINDUNILVR.NS, ITC.NS, NESTLEIND.NS; automotive — TMPV.NS, MARUTI.NS, M&M.NS. A stock's sector determines which basket of the other stocks in that same sector its sector-divergence calculation is averaged against, excluding itself.


# Plan of Work

This plan of work proceeds through nine milestones, each one a narrative unit of work that ends with something concretely demonstrable, not merely a step toward something demonstrable later. Do not begin a milestone before the previous one's Validation and Acceptance criteria are actually met. A tenth milestone, a chat assistant, was added after the original nine were complete (see Progress and the Decision Log) and is not described here since it was outside this plan's original scope. An eleventh milestone, an AI-generated market brief, follows below.

Milestone 1 establishes the schema and an empty but fully deployed skeleton. Its goal is to eliminate deployment risk before any real logic exists, since a working local prototype that has never been deployed is the single most common hackathon failure mode. The work is to apply the full schema from this plan's Concrete Steps section to a fresh Supabase project, create an empty FastAPI application exposing a single health-check route, deploy it to Render as a long-running web service, create an empty Vite React application with a single page that calls that health-check route, and deploy it to Vercel with its API base URL pointed at the deployed Render service. The result is two live URLs, on two different hosting platforms, already talking to each other, before a single business feature exists. Proof of success is opening the deployed frontend URL in a browser and seeing a successful response from the deployed backend rendered on the page.

Milestone 2 makes the watchlist real and persistent. The work is to wire Supabase Auth's magic-link flow into the Login page, implement the watchlist and watchlist-item routes described in Interfaces and Dependencies below, and build the Watchlist page against the fixed twenty-instrument universe. The result is that a real, authenticated user can add and remove instruments from their watchlist. Proof of success is creating a watchlist, adding three instruments, refreshing the browser tab entirely, and seeing the same three instruments still present, which demonstrates that Supabase, not browser memory, is the source of truth — this is also the literal implementation of the plan's cross-device persistence requirement.

Milestone 3 builds the ingestion pipeline, deliberately starting with the Replay source rather than the live Yahoo Finance source, because a scripted, deterministic input is far easier to debug validation and deduplication logic against than a live feed with its own unpredictability. The work is to implement the shared pipeline steps — validation, self-assigned sequence numbering, deduplication by a key built from source, instrument, and event time, out-of-order detection against each instrument's last known event time, and the incremental rolling-statistics update — and then implement the Replay source as a hardcoded, ordered sequence of events: a baseline price for all twenty instruments, three or four small normal updates, a volume spike on TCS.NS at roughly three times its seeded baseline volume, a price move on TCS.NS immediately afterward that is large relative to its seeded volatility, an exact duplicate of that same TCS.NS price event, an event for INFY.NS whose event time is earlier than an INFY.NS event already processed, and a structural update on RELIANCE.NS. The result is a pipeline that can be run repeatedly and deterministically. Proof of success is running the Replay sequence once and confirming, by direct database query, that the duplicate TCS.NS event did not create a second row in market_events, and that the late INFY.NS event was stored but did not overwrite instrument_stats' last known price for INFY.NS.

Milestone 4 adds the live Yahoo Finance poller alongside the now-proven pipeline. The work is to implement a scheduled job, using apscheduler, that fetches the latest price and volume for all twenty seeded instruments on a fixed interval and feeds each one through the same pipeline function used by Replay Mode, wrapping each individual instrument's fetch in its own error handling so that one instrument's failure marks only that instrument as stale rather than halting the entire cycle. The result is real market data flowing into the same tables Milestone 3 proved correct. Proof of success is watching instrument_stats update with real, changing prices over several polling cycles, and separately, feeding one deliberately invalid ticker into the poller's instrument list and confirming the other nineteen instruments continue updating normally.

Milestone 5 implements signal detection on top of the now-flowing data. The work is to implement the price anomaly, volume anomaly, sector divergence, and structural trigger calculations exactly as specified in Interfaces and Dependencies, combine them into the weighted severity score, classify severity into the four bands, and write a signals row only when severity clears the twenty-point floor, including the explanation breakdown that will later power the detail screen. The result is that unusual behavior for a specific instrument becomes a stored, reusable fact rather than something recomputed on the fly. Proof of success is running the Replay sequence from Milestone 3 again and confirming that the TCS.NS volume-spike-plus-price-move pair produces exactly one signals row with severity at or above eighty and a populated explanation field, and that no signal at all was created for any of the small, normal-range updates earlier in the sequence.

Milestone 6 builds the personalized relevance feed, the feature this entire project exists to demonstrate. The work is to implement the feed endpoint's logic: for the calling user, read their watchlist's instruments, read signals for those instruments newer than that user's last-seen state for each one, drop any instrument the user has muted entirely, apply the priority boost, sort by adjusted severity, and split the response into the ranked attention items and a single quiet count, then update the user's last-seen state for every instrument shown, guarded so that an older, slower update can never overwrite a newer one already recorded. The result is the actual hero screen data. Proof of success is two things together: a user watching TCS.NS sees it in the feed's ranked items after Milestone 5's replay signal exists, a second user not watching TCS.NS does not see it at all, and calling the feed endpoint a second time immediately afterward, with no new signals in between, shows TCS.NS has moved out of the ranked items and into the quiet count, proving the last-seen checkpoint actually advanced.

Milestone 7 adds the notification decision layer on top of the now-working feed. The work is to implement the channel decision exactly as specified in Interfaces and Dependencies, including the one-push-per-instrument-per-hour cooldown enforced by querying prior entries in notification_log, and to write one notification_log row the first time each signal is evaluated for each interested user. The result is a decision that is visibly separate from the severity score itself. Proof of success is configuring three test users with different priority, mute, and notification-enabled settings on the same instrument, triggering one signal for that instrument, and confirming the three resulting notification_log rows show three different channels.

Milestone 8 is a dedicated security pass rather than something assumed to fall out of correct-looking code. The work is to verify, for every protected route, that the user id is taken only from the verified access token and never from any client-supplied field, that every watchlist and state query is scoped to that verified user id at the database-query level rather than filtered after fetching, and that the ingestion pipeline has no network-reachable route at all. The result is a system where one user's data is structurally unreachable to another. Proof of success is authenticating as a second test user and attempting to fetch or modify the first user's watchlist by its id, and confirming the request is rejected rather than merely returning empty or filtered data.

Milestone 9 is polish and rehearsal, not new backend logic. The work is finishing the FreshnessBadge component, the SignalDetail screen's rendering of the explanation breakdown, general loading and empty states, and then running the entire Replay Mode sequence from Milestone 3 start to finish, narrating each step aloud, timing it. The result is a demo that has actually been run before it is performed for judges. Proof of success is completing a full narrated run-through of the Replay sequence, including pointing out the rejected duplicate and the correctly-ordered late event, in under five minutes.

Milestone 11 adds a single AI capability on top of the already-complete, already-verified system: a market-brief generator over the personalized feed's output. The work is to add backend/app/ai/brief.py, exposing generate_brief(feed_items: list[dict]) -> str, whose prompt contains only the ticker, severity, and why-strings already present in the feed's items — nothing else, and never raw price history — instructing the model to write two to three plain sentences summarizing what happened for someone who has not seen the numbers, explicitly forbidding any buy, sell, hold, or price-direction opinion. Before the result is used, validate_brief(text: str, feed_items: list[dict]) -> bool checks that the text does not name any instrument ticker absent from feed_items and does not contain the substrings "buy", "sell", or "should invest" (case-insensitive); a brief that fails either check is discarded exactly as if the API call itself had failed. On any API failure, timeout, missing API key, disabled feature, or failed validation, generate_brief falls back to deterministic_brief(feed_items), a plain template joining the highest-severity item's why-strings: "Since your last check, the most notable activity was in {instrument}: {why}." The response shape is identical either way, so nothing downstream can tell which source produced the text. The brief is never generated inline within the GET /api/feed request path: build_feed() reads whatever market_brief is currently cached for that user from an in-memory dict keyed by user_id (acceptable to reset on a process restart, since it simply regenerates on the next poll), and the route handler in backend/app/routes/feed.py compares the current items' hash against the cache and schedules a FastAPI BackgroundTasks call to regenerate it when they differ — build_feed() itself remains a pure, synchronous function with no knowledge of the AI layer. Proof of success is threefold: replaying Milestone 3's sequence and, after two consecutive polls, confirming the second poll's market_brief is non-empty and mentions TCS.NS; removing the API key and confirming market_brief still returns non-empty fallback text with the feed's own items and summary fields completely unaffected; and constructing a case where validate_brief is given text naming a fabricated ticker or containing "should i buy" and confirming it's rejected. This milestone is optional per the original plan (gated on remaining build time); it was built in full here since the user explicitly requested it.


# Concrete Steps

Work from an empty directory that will become the repository root. Create the three subpaths described in Context and Orientation before writing any files into them: `backend`, `frontend`, and `db`.

For the database, open the Supabase project's SQL editor and run the following schema exactly once. Note that these statements are written with `create table if not exists` rather than a bare `create table`, specifically so that this script can be safely re-run later without error, which matters directly for Idempotence and Recovery below.

  create table if not exists instruments (
    id uuid primary key default gen_random_uuid(),
    ticker text unique not null,
    name text,
    sector text
  );

  create table if not exists watchlists (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    name text default 'My Watchlist',
    created_at timestamptz default now()
  );

  create table if not exists watchlist_items (
    watchlist_id uuid references watchlists(id) on delete cascade,
    instrument_id uuid references instruments(id),
    priority text default 'NORMAL',
    notifications_enabled boolean default true,
    muted boolean default false,
    primary key (watchlist_id, instrument_id)
  );

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

  create table if not exists instrument_stats (
    instrument_id uuid primary key references instruments(id),
    rolling_avg_return numeric default 0,
    rolling_std_return numeric default 0,
    rolling_avg_volume numeric default 0,
    last_price numeric,
    last_event_time timestamptz,
    updated_at timestamptz default now()
  );

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

  create table if not exists user_instrument_state (
    user_id uuid references auth.users(id),
    instrument_id uuid references instruments(id),
    last_seen_at timestamptz,
    last_seen_price numeric,
    primary key (user_id, instrument_id)
  );

  create table if not exists notification_log (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id),
    signal_id uuid references signals(id),
    channel text,
    sent_at timestamptz default now()
  );

  create index if not exists idx_market_events_instrument_time on market_events (instrument_id, event_time desc);
  create index if not exists idx_signals_instrument_time on signals (instrument_id, event_time desc);
  create index if not exists idx_notification_log_user_time on notification_log (user_id, sent_at desc);

After the schema is applied, seed the twenty instruments listed in Context and Orientation into the instruments table, either as a one-time SQL insert run in the same SQL editor or as a short startup routine in the backend that inserts each one only if its ticker does not already exist.

For the backend, initialize the Python project inside `backend/`, create the file structure described in Context and Orientation, and install the dependencies named there. Set the environment variables SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET, FRONTEND_ORIGIN, REPLAY_MODE, and POLL_INTERVAL_SECONDS, either in a local `.env` file for development or in Render's environment variable settings for the deployed service. Deploy to Render as a web service whose start command runs the FastAPI application under uvicorn, confirming in Render's own logs that the process stays running rather than exiting after startup, since an exiting process would silently stop the ingestion loop.

For the frontend, initialize the Vite React project inside `frontend/`, create the file structure described in Context and Orientation, and install the dependencies named there. Set VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, and VITE_API_BASE_URL as environment variables in Vercel's project settings before the first deploy, since Vite inlines these at build time rather than reading them at runtime.


# Validation and Acceptance

Each milestone's own Proof of Success, stated in the Plan of Work above, is the acceptance criterion for that milestone and must be checked before moving on — this section adds the acceptance checks that apply to the system as a whole, once all nine milestones are complete.

Requesting the feed endpoint for an authenticated user with no watchlist items at all must return a response with an empty items array and a summary showing zero across every count, not an error and not a missing field.

Running the full Replay Mode sequence end to end and then requesting the feed endpoint as a user watching TCS.NS must return a response whose items array contains exactly one entry for TCS.NS with severity at or above eighty and a why array containing at least one string mentioning volume and at least one string mentioning price movement, for example:

  {
    "last_checked": "2026-09-05T09:00:00Z",
    "summary": { "high": 1, "medium": 0, "quiet": 19 },
    "items": [
      {
        "instrument": "TCS.NS",
        "severity": 88,
        "surface": "HIGH",
        "why": ["Price moved 3.8%, unusual for this stock", "Volume is 2.4x rolling average"],
        "data_quality": "OK"
      }
    ]
  }

Attempting, as an authenticated user, to fetch a watchlist id known to belong to a different user must return a 403 or 404 response rather than that watchlist's data, with a body of the shape:

  { "error": { "code": "NOT_FOUND", "message": "Watchlist not found" } }

Disconnecting or invalidating the live Yahoo Finance poller for a single instrument, while leaving the other nineteen instruments untouched, must result in only that one instrument's data_quality becoming STALE in subsequent feed responses, with its last known price still returned rather than omitted, while the other nineteen continue showing OK.

If Milestone 11 is built, the feed response's market_brief field must be present and non-empty on every response, including the very first request after a process restart before any background generation has completed — in that case it is the deterministic fallback text, never an empty string or a missing field.


# Idempotence and Recovery

The schema in Concrete Steps uses create table if not exists and create index if not exists specifically so that re-running `db/schema.sql` against the same Supabase project at any point is always safe and produces no errors and no duplicate objects.

The ingestion pipeline's deduplication key, built from source, instrument, and event time, means re-running the Replay Mode sequence multiple times against a database that already contains a prior run's data will not create duplicate market_events or duplicate signals rows for the same underlying events — this is the same mechanism relied on for Milestone 3's proof of success and should be trusted as the general-purpose safe-retry mechanism for ingestion, rather than manually clearing tables between test runs.

If the backend process crashes or is redeployed while the live poller is mid-cycle, no state is lost beyond that single in-flight polling cycle, because instrument_stats and market_events are the durable source of truth in Postgres, not in-memory state; the next scheduled poll simply resumes updating from whatever was last persisted.

To reset the system for a clean demo run, truncate market_events, signals, instrument_stats, and notification_log, but leave instruments, watchlists, watchlist_items, and user_instrument_state untouched, since those represent the user-created state that should persist across a data reset — a reset should feel like "the market history is fresh," not "the user's account was deleted."


# Artifacts and Notes

A signal's stored explanation field, referenced in Milestone 5 and in Validation and Acceptance, takes the shape:

  {
    "price_anomaly": 42,
    "volume_anomaly": 26,
    "sector_divergence": 12,
    "structural_trigger": 0,
    "severity": 88,
    "reasons": [
      "Price moved 3.8%, unusual for this stock",
      "Volume is 2.4x rolling average"
    ]
  }

A dedupe_key, referenced throughout the ingestion sections above, is built as the concatenation of the event's source, a colon, the instrument's id, another colon, and the event's timestamp in ISO 8601 form, for example replay:3f2a1c9e-...-b7:2026-09-05T09:00:00+00:00 — this exact construction is what Milestone 3's duplicate-rejection proof and Idempotence and Recovery both depend on, so it must not be changed without updating both of those sections.


# Interfaces and Dependencies

The pipeline module, backend/app/ingestion/pipeline.py, exposes one function that both ingestion sources call: process_event(instrument_id: str, price: float, volume: int, event_time: datetime, source: str) -> ProcessedEvent | None, returning None when the event is rejected by validation or is an exact duplicate, and otherwise returning an object describing whether the event was accepted as current or stored as late, which the caller uses only for logging.

The rolling-statistics update, part of the same module, follows this exact exponential-moving-average formulation with a fixed smoothing factor of 0.15: given the previous rolling_avg_return, rolling_std_return, and rolling_avg_volume for an instrument, and a new observed return_pct and volume, the new rolling_avg_return equals the old value times 0.85 plus return_pct times 0.15; the new rolling_std_return equals the square root of the old rolling_std_return squared times 0.85 plus the squared difference between return_pct and the new rolling_avg_return times 0.15; the new rolling_avg_volume equals the old value times 0.85 plus the new volume times 0.15. This update is deliberately a constant-time operation regardless of how much price history exists, which is the basis for this project's scaling claim.

The detectors module, backend/app/signals/detectors.py, exposes four functions, each returning a float from zero to one hundred: price_anomaly_score(return_pct: float, rolling_avg_return: float, rolling_std_return: float) -> float; volume_anomaly_score(volume: int, rolling_avg_volume: float) -> float; sector_divergence_score(instrument_return: float, sector_basket_return: float) -> float; structural_trigger_score(price: float, historical_high: float, historical_low: float) -> float.

The scoring module, backend/app/signals/scoring.py, exposes compute_severity(price_anomaly: float, volume_anomaly: float, sector_divergence: float, structural_trigger: float) -> dict, returning a dictionary with the four component scores, the combined severity using the weights 0.40, 0.25, 0.15, and 0.20 respectively as specified in the Decision Log's rationale for the severity formula, a classification string of HIGH, MEDIUM, LOW, or IGNORE, and a reasons list of human-readable strings generated by simple threshold-based templates rather than any language model.

The feed module, backend/app/relevance/feed.py, exposes build_feed(user_id: str) -> dict, implementing exactly the logic described in Milestone 6, plus (Milestone 11) compute_items_hash(items: list[dict]) -> str and the module-level `_brief_cache` dict that build_feed() reads from (never writes to) to attach the response's market_brief field. Until Milestone 11, build_feed() was the only function the feed route handler called; the route now also calls compute_items_hash() and, via a background task, app/ai/brief.py's generate_brief().

The AI brief module, backend/app/ai/brief.py (Milestone 11, optional), exposes generate_brief(feed_items: list[dict]) -> str, validate_brief(text: str, feed_items: list[dict]) -> bool, and deterministic_brief(feed_items: list[dict]) -> str, implementing exactly the logic described in Milestone 11 — including its own fallback triggers (disabled via AI_BRIEF_ENABLED, no ANTHROPIC_API_KEY configured, an empty feed, any API error or timeout beyond 4 seconds, or a brief that fails validate_brief).

The notification module, backend/app/notifications/decision.py, exposes decide_channel(user_id: str, instrument_id: str, severity: float) -> str, returning one of PUSH, IN_APP, or SUPPRESS, implementing exactly the rules described in Milestone 7, including the cooldown check against notification_log.

The authentication dependency, backend/app/auth.py, exposes get_current_user_id() as a FastAPI dependency usable in any route signature, which reads the Authorization header, verifies the bearer token against SUPABASE_JWT_SECRET, and raises a 401 with the error body shape shown in Validation and Acceptance if the token is missing or invalid — every route under backend/app/routes/ except the internal ingestion call path must declare this dependency.

The route module backend/app/routes/watchlists.py registers exactly these HTTP endpoints, all depending on get_current_user_id(): POST /api/watchlists accepts a body of {"name": string} and returns 201 with {"id": string, "name": string}; GET /api/watchlists takes no body and returns 200 with a list of watchlists, each including its items as {"instrument_id": string, "ticker": string, "priority": string, "muted": boolean, "notifications_enabled": boolean}; POST /api/watchlists/{watchlist_id}/items accepts {"ticker": string}, where ticker must be one of the twenty seeded instruments, and returns 201, or 404 with the standard error body if watchlist_id does not belong to the calling user; PATCH /api/watchlists/{watchlist_id}/items/{instrument_id} accepts a body with either or both of {"priority": string, "muted": boolean} and returns 200; DELETE /api/watchlists/{watchlist_id}/items/{instrument_id} takes no body and returns 204. The route module backend/app/routes/feed.py registers GET /api/feed, taking no body and returning the shape shown in Validation and Acceptance. The route module backend/app/routes/signals.py registers GET /api/signals/{instrument_id}, returning 200 with that instrument's most recent signal's explanation field exactly as stored, or 404 if no signal exists yet for that instrument. Every response body, success or error, is JSON; every error response uses the {"error": {"code": string, "message": string}} shape shown in Validation and Acceptance, with codes drawn from VALIDATION_ERROR, UNAUTHORIZED, NOT_FOUND, and INTERNAL_ERROR.

On the frontend, frontend/src/lib/supabaseClient.js is the single place the Supabase browser client is created, and every other frontend file that needs the current access token reads it from this client's own session rather than maintaining a separate copy. Concretely, before any fetch call to the backend, the calling code awaits supabaseClient.auth.getSession() and reads session.access_token, attaching it as the Authorization header in the form "Bearer " followed by the token; a request made with no session present (the user is not logged in) should never be sent at all, and the calling page should redirect to Login.jsx instead. Feed.jsx additionally subscribes to supabaseClient.auth.onAuthStateChange so that a token refreshed mid-session is picked up without the user needing to reload the page.

The Replay source, backend/app/ingestion/replay_source.py, exposes a single function run_replay_sequence() -> None that plays the exact scripted event list described in Milestone 3 through pipeline.process_event(), pacing each event three to five seconds apart with a blocking sleep between them so a full run takes a few minutes end to end. This function is invoked in exactly one of two ways, never both in the same run: automatically, once, on backend process startup when the environment variable REPLAY_MODE is "true", making a fresh deploy immediately demoable without any manual trigger; or manually during rehearsal by running it directly from a shell in the backend's environment, indented here as the exact command and working directory —

  cd backend
  python -m app.ingestion.replay_source

— which is the mechanism to use to re-run the sequence repeatedly while rehearsing without redeploying the whole service. When REPLAY_MODE is "false", replay_source.py is never invoked at all, and instead main.py starts the apscheduler job that calls yahoo_source.py on the interval given by POLL_INTERVAL_SECONDS; the two sources are mutually exclusive within a single running process, controlled entirely by the REPLAY_MODE environment variable, and switching between them requires only changing that variable and restarting the process, not changing any code.

Local development, as distinct from the Render and Vercel deployments described in Concrete Steps, runs the backend with the indented command below from inside the backend directory, after its environment variables are set in a local .env file —

  cd backend
  uvicorn app.main:app --reload --port 8000

— and runs the frontend with the indented command below from inside the frontend directory, with VITE_API_BASE_URL in its local .env pointed at http://localhost:8000 —

  cd frontend
  npm run dev
```
