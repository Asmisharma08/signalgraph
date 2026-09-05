"""
SignalGraph — Signals Route (Milestone 5)
==========================================
Endpoint:
  GET /api/signals/{instrument_id} — returns the most recent signal's
  explanation field for the given instrument, or 404 if none exists.
"""

from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.db import supabase

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/{instrument_id}")
async def get_latest_signal(
    instrument_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Return the most recent signal's explanation for one instrument."""
    result = (
        supabase.table("signals")
        .select("*")
        .eq("instrument_id", instrument_id)
        .order("event_time", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "No signal found for this instrument"}},
        )

    return result.data[0]["explanation"]
