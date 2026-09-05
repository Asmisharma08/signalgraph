"""
SignalGraph — Pydantic Schemas
===============================
Request and response models for all HTTP endpoints.

These models serve three purposes:
  1. Automatic request body validation (FastAPI reads these)
  2. Response serialization (ensures consistent JSON shapes)
  3. OpenAPI documentation generation (Swagger UI)

Every error response uses the standard shape:
  {"error": {"code": "<CODE>", "message": "<human-readable>"}}
with codes drawn from: VALIDATION_ERROR, UNAUTHORIZED, NOT_FOUND, INTERNAL_ERROR.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Error response ───────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── Watchlist ────────────────────────────────────────────────

class CreateWatchlistRequest(BaseModel):
    """POST /api/watchlists — body"""
    name: str = "My Watchlist"


class WatchlistItemOut(BaseModel):
    """One item inside a watchlist response"""
    instrument_id: str
    ticker: str
    priority: str = "NORMAL"
    muted: bool = False
    notifications_enabled: bool = True


class WatchlistOut(BaseModel):
    """GET /api/watchlists — one watchlist in the response list"""
    id: str
    name: str
    items: list[WatchlistItemOut] = []


class CreateWatchlistResponse(BaseModel):
    """POST /api/watchlists — response"""
    id: str
    name: str


class AddWatchlistItemRequest(BaseModel):
    """POST /api/watchlists/{watchlist_id}/items — body.
    ticker must be one of the 20 seeded instruments."""
    ticker: str


class UpdateWatchlistItemRequest(BaseModel):
    """PATCH /api/watchlists/{watchlist_id}/items/{instrument_id} — body.
    Both fields are optional; send whichever you want to change."""
    priority: Optional[str] = None
    muted: Optional[bool] = None


# ── Feed ─────────────────────────────────────────────────────

class FeedSummary(BaseModel):
    """Counts by severity band"""
    high: int = 0
    medium: int = 0
    quiet: int = 0


class FeedItem(BaseModel):
    """One ranked item in the attention list"""
    instrument: str          # e.g. "TCS.NS"
    instrument_id: str       # for navigating to GET /api/signals/{instrument_id}
    severity: float
    surface: str             # HIGH | MEDIUM | LOW
    why: list[str] = []      # human-readable reasons
    data_quality: str = "OK" # OK | STALE


class FeedResponse(BaseModel):
    """GET /api/feed — full response"""
    last_checked: str
    summary: FeedSummary
    items: list[FeedItem] = []
    market_brief: str = ""  # Milestone 11 — always non-empty in practice, never absent


# ── Signal detail ────────────────────────────────────────────

class SignalExplanation(BaseModel):
    """GET /api/signals/{instrument_id} — the explanation breakdown"""
    price_anomaly: float = 0
    volume_anomaly: float = 0
    sector_divergence: float = 0
    structural_trigger: float = 0
    severity: float = 0
    reasons: list[str] = []


# ── Health check ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    """GET /api/health — simple liveness probe"""
    status: str = "ok"
    version: str = "0.1.0"
    replay_mode: bool = True
