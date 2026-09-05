"""
SignalGraph — FastAPI Application Entry Point
===============================================
This is the main module that:
  1. Creates the FastAPI application
  2. Configures CORS (restricted to FRONTEND_ORIGIN)
  3. Mounts all route modules
  4. Exposes a health-check endpoint at GET /api/health
  5. Seeds the 20 demo instruments on startup (idempotent)

Run locally with:
    cd backend
    uvicorn app.main:app --reload --port 8000

In production (Render), the start command is:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import FRONTEND_ORIGIN, REPLAY_MODE
from app.models.schemas import HealthResponse
from app.routes import watchlists, feed, signals, chat


# ── Instrument seed data ─────────────────────────────────────
# The fixed 20-stock NSE demo universe from the ExecPlan.
# Grouped by sector for clarity; the sector field determines
# which peer basket an instrument's divergence is averaged against.
SEED_INSTRUMENTS = [
    # Information Technology
    {"ticker": "TCS.NS",      "name": "Tata Consultancy Services", "sector": "Information Technology"},
    {"ticker": "INFY.NS",     "name": "Infosys",                   "sector": "Information Technology"},
    {"ticker": "WIPRO.NS",    "name": "Wipro",                     "sector": "Information Technology"},
    {"ticker": "HCLTECH.NS",  "name": "HCL Technologies",         "sector": "Information Technology"},
    {"ticker": "TECHM.NS",    "name": "Tech Mahindra",             "sector": "Information Technology"},
    # Banking
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank",                 "sector": "Banking"},
    {"ticker": "ICICIBANK.NS","name": "ICICI Bank",                "sector": "Banking"},
    {"ticker": "SBIN.NS",     "name": "State Bank of India",       "sector": "Banking"},
    {"ticker": "KOTAKBANK.NS","name": "Kotak Mahindra Bank",       "sector": "Banking"},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank",                 "sector": "Banking"},
    # Energy and Utilities
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries",       "sector": "Energy and Utilities"},
    {"ticker": "ONGC.NS",     "name": "Oil and Natural Gas Corp",  "sector": "Energy and Utilities"},
    {"ticker": "NTPC.NS",     "name": "NTPC Limited",              "sector": "Energy and Utilities"},
    {"ticker": "POWERGRID.NS","name": "Power Grid Corp",           "sector": "Energy and Utilities"},
    # Consumer Goods
    {"ticker": "HINDUNILVR.NS","name": "Hindustan Unilever",       "sector": "Consumer Goods"},
    {"ticker": "ITC.NS",      "name": "ITC Limited",               "sector": "Consumer Goods"},
    {"ticker": "NESTLEIND.NS","name": "Nestle India",              "sector": "Consumer Goods"},
    # Automotive
    {"ticker": "TMPV.NS",      "name": "Tata Motors Passenger Vehicles", "sector": "Automotive"},
    {"ticker": "MARUTI.NS",   "name": "Maruti Suzuki",             "sector": "Automotive"},
    {"ticker": "M&M.NS",      "name": "Mahindra & Mahindra",       "sector": "Automotive"},
]


def seed_instruments():
    """
    Insert the 20 demo instruments into the instruments table.
    Uses upsert (on conflict do nothing) so this is safe to call repeatedly.
    Called once on startup.
    """
    try:
        from app.db import supabase
        for inst in SEED_INSTRUMENTS:
            supabase.table("instruments").upsert(
                inst, on_conflict="ticker"
            ).execute()
        print(f"[SEED] Seeded {len(SEED_INSTRUMENTS)} instruments (idempotent)")
    except Exception as e:
        # Don't crash the app if DB isn't configured yet.
        # This lets the skeleton run locally without Supabase credentials.
        print(f"[SEED] Skipped instrument seeding (DB not available): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup: seeds instruments, starts ingestion if configured.
    Runs on shutdown: (cleanup if needed).
    """
    # ── Startup ──────────────────────────────────────────────
    print("[STARTUP] SignalGraph backend starting...")
    seed_instruments()

    if REPLAY_MODE:
        print("[STARTUP] REPLAY_MODE=true — running replay sequence once in the background")
        import threading
        from app.ingestion.replay_source import run_replay_sequence
        threading.Thread(target=run_replay_sequence, daemon=True).start()
    else:
        print("[STARTUP] REPLAY_MODE=false — starting live Yahoo Finance poller")
        from app.ingestion.yahoo_source import start_scheduler
        start_scheduler()

    yield  # App is now running and serving requests

    # ── Shutdown ─────────────────────────────────────────────
    print("[SHUTDOWN] SignalGraph backend shutting down...")


# ── Create the FastAPI app ───────────────────────────────────
app = FastAPI(
    title="SignalGraph",
    description="Smart stock watchlist — surfaces what actually deserves your attention.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────
# Restricted to the frontend's origin only.
# In local dev this defaults to http://localhost:5173 (Vite).
# In production this is the Vercel deployment URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error shape ──────────────────────────────────────────────
# Every route raises HTTPException(detail={"error": {"code", "message"}}).
# FastAPI's default handler wraps that under a top-level "detail" key;
# this override makes the response body exactly {"error": {...}} as
# specified in the ExecPlan's Validation and Acceptance section.
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    body = exc.detail
    if not (isinstance(body, dict) and "error" in body):
        body = {"error": {"code": "INTERNAL_ERROR", "message": str(exc.detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


# ── Mount route modules ─────────────────────────────────────
app.include_router(watchlists.router)
app.include_router(feed.router)
app.include_router(signals.router)
app.include_router(chat.router)


# ── Health check ─────────────────────────────────────────────
# This is the first endpoint, used by Milestone 1 to verify
# the frontend can talk to the backend.
@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """
    Simple liveness probe. Returns the app status, version, and current mode.
    The frontend calls this on load to confirm connectivity.
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        replay_mode=REPLAY_MODE,
    )
