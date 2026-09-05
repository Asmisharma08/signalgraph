# SignalGraph

**Your watchlist, but smarter.** SignalGraph turns a passive stock watchlist into a system that tells you what actually deserves your attention — instead of making you scan every price on every visit.

Add a few NSE-listed stocks to your watchlist, close the app, come back hours later, and see a short, ranked list of the two or three things that genuinely changed — each with a plain-language reason — while everything else that stayed normal is folded into a single "nothing unusual" line.

---

## The problem

A stock watchlist app shows you every price, every time. That's not information — it's noise. The real question an investor has isn't "what is the price right now," it's "did anything happen that I should actually care about?" Answering that requires comparing today's behavior against an instrument's own recent history, its sector peers, and its historical range — work no one does by hand on every visit.

## What SignalGraph does

- **Detects real anomalies, not just price changes.** Every tick is scored on four independent signals — unusual price movement, unusual trading volume, divergence from sector peers, and structural breaks above/below recent highs/lows — combined into a single weighted severity score (0–100) with a plain-language explanation of *why* it fired.
- **Shows you what's new, not everything.** The feed only ever surfaces something once per change — after you've seen it, it drops into a quiet "N instruments, nothing unusual" summary until something actually changes again.
- **Survives messy real-world data.** Duplicate events, late-arriving data, and a temporarily unreachable data source are all handled explicitly — the system never silently loses data or lies about how fresh it is.
- **Explains itself in plain language, never gives advice.** A built-in chat assistant answers "why did TCS move today?" or "how's the IT sector doing?" grounded in the system's own live data — and is hard-blocked from ever giving investment advice, price targets, or buy/sell recommendations.
- **Runs on real market data.** A live Yahoo Finance poller feeds the same detection pipeline that a fully scripted, deterministic replay sequence uses for demos — so the exact same logic is provable offline and provable live.

## How it works

```
┌─────────────┐      ┌──────────────────┐      ┌───────────────────┐
│  Live Yahoo  │      │                  │      │                   │
│  Finance     ├─────▶│  Ingestion       │      │  Signal Detection │
│  poller      │      │  Pipeline        ├─────▶│  (4 detectors +   │
├─────────────┤      │  (validate,      │      │   weighted score) │
│  Scripted    ├─────▶│  dedupe, order,  │      │                   │
│  Replay Mode │      │  rolling stats)  │      └─────────┬─────────┘
└─────────────┘      └──────────────────┘                │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Notification    │◀────┤  Personalized    │◀────┤  signals table  │
│  decision layer  │     │  Feed            │     │  (severity ≥20) │
│  (push/in-app/   │     │  (per-user,      │     └────────────────┘
│  suppress)       │     │  muted/priority) │
└─────────────────┘     └──────────────────┘
```

Both the live poller and the replay sequence feed the *same* ingestion pipeline, so anomaly detection is provably identical whether the data is real or scripted. Every signal that clears a 20-point severity floor is stored once, with a full breakdown of what triggered it — nothing is ever recomputed silently or explained after the fact.

## Key features

| Feature | Detail |
|---|---|
| **Watchlist** | Add/remove any of 20 fixed NSE stocks across 5 sectors, per-instrument priority (HIGH boosts severity) and mute |
| **Ingestion pipeline** | Validation, per-instrument sequence numbering, exact-duplicate rejection, late-event handling, exponential-moving-average rolling statistics |
| **Signal detection** | Price anomaly, volume anomaly, sector divergence, structural high/low break — weighted into one severity score with HIGH/MEDIUM/LOW/IGNORE bands |
| **Personalized feed** | Only shows instruments with a *new*, *meaningful* signal since you last looked; everything else is a one-line quiet count |
| **Notifications** | Per-user channel decision (PUSH / IN-APP / SUPPRESS) with a one-push-per-hour cooldown, fully audited |
| **Security** | Every request scoped to the calling user's verified Supabase JWT at the database-query level — never trusts a client-supplied user id |
| **Chat assistant** | Conversational Q&A about tracked companies — comparisons, sector overviews, follow-ups — grounded in live data, zero API cost by default, hard-blocked from giving investment advice |
| **AI market brief** | An optional 2–3 sentence synthesized overview of the feed, generated in the background so it never blocks a request, validated against the feed's own data before ever being shown, with a deterministic fallback if unavailable |

## Tech stack

- **Backend:** Python, FastAPI, Supabase (PostgreSQL + Auth), APScheduler, yfinance
- **Frontend:** React (Vite), Supabase JS client
- **AI:** Claude (Anthropic API) — optional, off by default; every AI-touched feature has a fully deterministic, zero-cost fallback path
- **Data:** 20 fixed NSE-listed instruments across Information Technology, Banking, Energy & Utilities, Consumer Goods, and Automotive

## Project structure

```
backend/
  app/
    ingestion/      # pipeline.py, replay_source.py, yahoo_source.py
    signals/        # detectors.py, scoring.py
    relevance/      # feed.py — the personalized feed
    notifications/  # decision.py — channel decisions
    chat/           # assistant.py — the explain-only chatbot
    ai/             # brief.py — the optional AI market brief
    routes/         # watchlists.py, feed.py, signals.py, chat.py
    auth.py         # JWT verification (HS256 + ES256/JWKS)
    main.py         # FastAPI app, CORS, startup seeding
frontend/
  src/
    pages/          # Login, Watchlist, Feed, SignalDetail
    components/     # ChatWidget, FreshnessBadge
    lib/            # Supabase client, API wrapper
db/
  schema.sql        # Full Postgres schema (idempotent, safe to re-run)
```

## Running it locally

**Prerequisites:** a free [Supabase](https://supabase.com) project (Postgres + Auth).

1. Run `db/schema.sql` once in your Supabase project's SQL editor.
2. Backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET
   uvicorn app.main:app --reload --port 8000
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   cp .env.example .env   # fill in VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
   npm run dev
   ```
4. Open `http://localhost:5173`, sign in with the magic-link email flow, and add a few instruments to your watchlist.

With `REPLAY_MODE=true` (the default), a fully scripted demo sequence — baseline prices, a volume spike, a large price move, an exact duplicate event, a late-arriving event, and a structural break — runs automatically on startup, so the feed has something real to show within about a minute of first boot. Set `REPLAY_MODE=false` to switch to the live Yahoo Finance poller instead.

The chat assistant and AI market brief both work with zero configuration (fully deterministic, zero API cost); adding an `ANTHROPIC_API_KEY` upgrades both to Claude-powered responses using the identical underlying data and the identical safety boundaries.

## What's deliberately not built

- **Deployment.** This runs locally against a real Supabase project; deploying to Render (backend) + Vercel (frontend) was scoped in the original plan but deprioritized in favor of build time on the detection and relevance logic the project is actually judged on.
- **A dynamic instrument universe.** The 20-stock universe is fixed on purpose, to keep ingestion, sector-basket, and demo logic fully testable within the build's time budget.
- **Push notification delivery.** The notification *decision* layer (push/in-app/suppress, with cooldown) is fully built and audited; actually delivering a push notification to a device is not.

## License

Built for a hackathon submission.
