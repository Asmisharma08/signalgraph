"""
SignalGraph — Notification Decision (Milestone 7)
===================================================
Exposes: decide_channel(user_id: str, instrument_id: str, severity: float) -> str

Returns one of PUSH, IN_APP, SUPPRESS for one user's per-instrument
notification settings and the current cooldown state:
  - muted for this user                          -> SUPPRESS
  - notifications disabled for this user          -> IN_APP (still visible
    in the feed itself, just no push)
  - severity is HIGH (>=70) or the user marked this instrument HIGH
    priority, and no PUSH has already gone to this user for this
    instrument within the last hour                -> PUSH
  - anything else that reaches here (enabled, but not urgent enough,
    or a PUSH already went out this hour)           -> IN_APP

Also exposes notify_interested_users(instrument_id, signal_id, severity),
the fan-out glue scoring.evaluate_and_record_signal() calls right after
writing a new signal: it finds every user watching that instrument
(across any of their watchlists), runs decide_channel() for each, and
writes one notification_log row per user for that signal.
"""

from datetime import datetime, timedelta, timezone

from app.db import supabase

COOLDOWN = timedelta(hours=1)


def _watchlist_item_for(user_id: str, instrument_id: str) -> dict | None:
    wl_ids = [w["id"] for w in supabase.table("watchlists").select("id").eq("user_id", user_id).execute().data]
    if not wl_ids:
        return None
    rows = (
        supabase.table("watchlist_items")
        .select("priority, muted, notifications_enabled")
        .in_("watchlist_id", wl_ids)
        .eq("instrument_id", instrument_id)
        .execute()
        .data
    )
    return rows[0] if rows else None


def _push_cooldown_active(user_id: str, instrument_id: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - COOLDOWN).isoformat()
    recent_signal_ids = [
        row["id"]
        for row in supabase.table("signals")
        .select("id")
        .eq("instrument_id", instrument_id)
        .gte("event_time", cutoff)
        .execute()
        .data
    ]
    if not recent_signal_ids:
        return False
    recent_pushes = (
        supabase.table("notification_log")
        .select("id")
        .eq("user_id", user_id)
        .eq("channel", "PUSH")
        .in_("signal_id", recent_signal_ids)
        .gte("sent_at", cutoff)
        .execute()
        .data
    )
    return len(recent_pushes) > 0


def decide_channel(user_id: str, instrument_id: str, severity: float) -> str:
    item = _watchlist_item_for(user_id, instrument_id)
    if item is None or item.get("muted"):
        return "SUPPRESS"

    if not item.get("notifications_enabled", True):
        return "IN_APP"

    urgent = severity >= 70 or item.get("priority") == "HIGH"
    if urgent and not _push_cooldown_active(user_id, instrument_id):
        return "PUSH"

    return "IN_APP"


def _interested_user_ids(instrument_id: str) -> list[str]:
    watchlist_ids = [
        row["watchlist_id"]
        for row in supabase.table("watchlist_items")
        .select("watchlist_id")
        .eq("instrument_id", instrument_id)
        .execute()
        .data
    ]
    if not watchlist_ids:
        return []
    user_ids = [
        row["user_id"]
        for row in supabase.table("watchlists")
        .select("user_id")
        .in_("id", watchlist_ids)
        .execute()
        .data
    ]
    return list(set(user_ids))


def notify_interested_users(instrument_id: str, signal_id: str, severity: float) -> list[dict]:
    """Called once, right after a new signal row is written, for every
    user watching that instrument. Writes one notification_log row per
    user recording the channel decision."""
    decisions = []
    for user_id in _interested_user_ids(instrument_id):
        channel = decide_channel(user_id, instrument_id, severity)
        supabase.table("notification_log").insert(
            {"user_id": user_id, "signal_id": signal_id, "channel": channel}
        ).execute()
        decisions.append({"user_id": user_id, "channel": channel})
    return decisions
