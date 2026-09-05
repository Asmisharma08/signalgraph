"""
SignalGraph — Configuration
===========================
All runtime configuration is read from environment variables.
In local dev, these come from a .env file loaded by python-dotenv.
In production (Render), they are set in the service's env-var settings.

Variables:
  SUPABASE_URL             — The Supabase project URL (https://<ref>.supabase.co)
  SUPABASE_SERVICE_ROLE_KEY — Service-role key for backend DB access (never exposed to frontend)
  SUPABASE_JWT_SECRET       — JWT secret used to verify user access tokens
  FRONTEND_ORIGIN           — Allowed CORS origin (e.g. https://signalgraph.vercel.app)
  REPLAY_MODE               — "true" to run the scripted replay on startup; "false" for live Yahoo poller
  POLL_INTERVAL_SECONDS     — Seconds between Yahoo Finance polling cycles (ignored in replay mode)
"""

import os
from dotenv import load_dotenv

# Load .env file if present (local dev); no-op if the file doesn't exist.
load_dotenv()

# ── Supabase ─────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

# ── CORS ─────────────────────────────────────────────────────
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# ── Ingestion mode ───────────────────────────────────────────
REPLAY_MODE: bool = os.getenv("REPLAY_MODE", "true").lower() == "true"
POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

# ── Chat assistant (explain-only, no investment advice) ───────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── AI market brief (Milestone 11) ─────────────────────────────
# Reuses ANTHROPIC_API_KEY above rather than a separate
# AI_PROVIDER_API_KEY — this project only ever calls one provider
# (Claude), so a second identically-purposed env var would just be
# redundant. AI_BRIEF_ENABLED is the kill switch from the plan: set
# to "false" to force the deterministic fallback even with a key
# configured, without a redeploy.
AI_BRIEF_ENABLED: bool = os.getenv("AI_BRIEF_ENABLED", "true").lower() == "true"
