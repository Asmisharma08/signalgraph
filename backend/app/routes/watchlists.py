"""
SignalGraph — Watchlist Routes (Milestone 2)
=============================================
All endpoints require authentication via get_current_user_id.
The user_id is ALWAYS extracted from the verified JWT — never from
any client-supplied field.

Endpoints:
  POST   /api/watchlists                                      — create watchlist
  GET    /api/watchlists                                      — list user's watchlists with items
  POST   /api/watchlists/{watchlist_id}/items                 — add instrument by ticker
  PATCH  /api/watchlists/{watchlist_id}/items/{instrument_id} — update priority/muted
  DELETE /api/watchlists/{watchlist_id}/items/{instrument_id} — remove instrument
"""

from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.db import supabase
from app.models.schemas import (
    CreateWatchlistRequest,
    CreateWatchlistResponse,
    WatchlistOut,
    WatchlistItemOut,
    AddWatchlistItemRequest,
    UpdateWatchlistItemRequest,
)

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


def _verify_watchlist_ownership(watchlist_id: str, user_id: str):
    """
    Check that the given watchlist belongs to the given user.
    Raises 404 if not found or not owned — we use 404 (not 403) so we
    don't leak the existence of other users' watchlists.
    """
    result = (
        supabase.table("watchlists")
        .select("id")
        .eq("id", watchlist_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Watchlist not found"}},
        )


# ── POST /api/watchlists ────────────────────────────────────
@router.post("", status_code=201, response_model=CreateWatchlistResponse)
async def create_watchlist(
    body: CreateWatchlistRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new watchlist for the authenticated user."""
    try:
        result = (
            supabase.table("watchlists")
            .insert({"user_id": user_id, "name": body.name})
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )
    row = result.data[0]
    return CreateWatchlistResponse(id=row["id"], name=row["name"])


# ── GET /api/watchlists ─────────────────────────────────────
@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(user_id: str = Depends(get_current_user_id)):
    """
    Return all watchlists for the authenticated user, each with its items.
    Items include the instrument ticker resolved from the instruments table.
    """
    # Fetch watchlists
    wl_result = (
        supabase.table("watchlists")
        .select("id, name")
        .eq("user_id", user_id)
        .execute()
    )

    watchlists = []
    for wl in wl_result.data:
        # Fetch items for this watchlist, joining instruments to get the ticker
        items_result = (
            supabase.table("watchlist_items")
            .select("instrument_id, priority, muted, notifications_enabled, instruments(ticker)")
            .eq("watchlist_id", wl["id"])
            .execute()
        )

        items = []
        for item in items_result.data:
            # The join returns instruments as a dict: {"ticker": "TCS.NS"}
            ticker = item.get("instruments", {}).get("ticker", "UNKNOWN")
            items.append(
                WatchlistItemOut(
                    instrument_id=item["instrument_id"],
                    ticker=ticker,
                    priority=item.get("priority", "NORMAL"),
                    muted=item.get("muted", False),
                    notifications_enabled=item.get("notifications_enabled", True),
                )
            )

        watchlists.append(WatchlistOut(id=wl["id"], name=wl["name"], items=items))

    return watchlists


# ── POST /api/watchlists/{watchlist_id}/items ────────────────
@router.post("/{watchlist_id}/items", status_code=201)
async def add_watchlist_item(
    watchlist_id: str,
    body: AddWatchlistItemRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Add an instrument to a watchlist by ticker.
    The ticker must be one of the 20 seeded instruments.
    """
    # Verify ownership
    _verify_watchlist_ownership(watchlist_id, user_id)

    # Look up the instrument by ticker
    inst_result = (
        supabase.table("instruments")
        .select("id")
        .eq("ticker", body.ticker)
        .execute()
    )
    if not inst_result.data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Ticker '{body.ticker}' is not in the instrument universe",
                }
            },
        )

    instrument_id = inst_result.data[0]["id"]

    # Insert into watchlist_items (upsert to avoid duplicates)
    supabase.table("watchlist_items").upsert(
        {
            "watchlist_id": watchlist_id,
            "instrument_id": instrument_id,
        },
        on_conflict="watchlist_id,instrument_id",
    ).execute()

    return {"instrument_id": instrument_id, "ticker": body.ticker}


# ── PATCH /api/watchlists/{watchlist_id}/items/{instrument_id}
@router.patch("/{watchlist_id}/items/{instrument_id}")
async def update_watchlist_item(
    watchlist_id: str,
    instrument_id: str,
    body: UpdateWatchlistItemRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update priority and/or muted status for a watchlist item."""
    # Verify ownership
    _verify_watchlist_ownership(watchlist_id, user_id)

    # Build the update payload from provided fields only
    update_data = {}
    if body.priority is not None:
        if body.priority not in ("NORMAL", "HIGH"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Priority must be 'NORMAL' or 'HIGH'",
                    }
                },
            )
        update_data["priority"] = body.priority
    if body.muted is not None:
        update_data["muted"] = body.muted

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "No fields to update",
                }
            },
        )

    result = (
        supabase.table("watchlist_items")
        .update(update_data)
        .eq("watchlist_id", watchlist_id)
        .eq("instrument_id", instrument_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Watchlist item not found"}},
        )

    return {"status": "updated"}


# ── DELETE /api/watchlists/{watchlist_id}/items/{instrument_id}
@router.delete("/{watchlist_id}/items/{instrument_id}", status_code=204)
async def delete_watchlist_item(
    watchlist_id: str,
    instrument_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Remove an instrument from a watchlist."""
    # Verify ownership
    _verify_watchlist_ownership(watchlist_id, user_id)

    supabase.table("watchlist_items").delete().eq(
        "watchlist_id", watchlist_id
    ).eq("instrument_id", instrument_id).execute()

    return None
