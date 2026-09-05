"""
SignalGraph — Feed Builder (Milestone 6)
=========================================
Exposes: build_feed(user_id: str) -> dict, mark_seen(user_id: str, instrument_id: str) -> None

For the calling user: reads their watchlists' instruments, finds each
instrument's latest signal, keeps only the ones that are both new (its
event_time is after the user's last-seen checkpoint for that
instrument) and meaningful (HIGH or MEDIUM severity band) as the
ranked "items", applies a priority boost for instruments the user
marked HIGH priority, and folds everything else (muted instruments
excluded entirely, LOW/no-signal instruments, and anything already
seen) into a single "quiet" count.

build_feed() itself is read-only — it does NOT advance the user's
last-seen checkpoint. Originally it did, on every call, per the
ExecPlan's Milestone 6 spec ("update the user's last-seen state for
every instrument shown"). That meant Feed.jsx's own automatic
background poll (every 12s) could mark a signal "seen" before the
user had actually noticed it, making it silently vanish into the
quiet count. Changed by explicit user request after they hit exactly
this during testing: checkpoints now advance only through the explicit
mark_seen() call below, fired when the user actually opens an
instrument's detail — never from a passive poll. See the Decision Log
entry dated when this changed for the full rationale; it supersedes
Milestone 6's original "second immediate call moves it to quiet"
acceptance behavior on purpose.
"""

import hashlib
from datetime import datetime, timezone

from app.ai.brief import deterministic_brief
from app.db import supabase
from app.config import POLL_INTERVAL_SECONDS

# ── Milestone 11: AI market brief cache ─────────────────────────
# A plain in-memory dict is enough at this scale — it's acceptable
# for this cache to reset on a process restart, since it simply
# regenerates on the next poll. build_feed() below only ever READS
# from this cache to attach market_brief to its response; it never
# calls generate_brief() or knows anything about the AI layer, keeping
# it a pure, synchronous function as specified. The route handler in
# routes/feed.py owns writing to it via a background task.
_brief_cache: dict[str, dict] = {}  # user_id -> {"brief": str, "items_hash": str}


def compute_items_hash(items: list[dict]) -> str:
    key = "|".join(f"{i['instrument']}:{i['severity']}" for i in sorted(items, key=lambda x: x["instrument"]))
    return hashlib.sha256(key.encode()).hexdigest()

# An instrument's data is considered STALE once its last known event is
# older than this. Not specified numerically by the ExecPlan; chosen as
# a multiple of the live poll interval with a floor generous enough not
# to falsely flag instruments during Replay Mode's own multi-second
# pacing between events.
STALE_THRESHOLD_SECONDS = max(POLL_INTERVAL_SECONDS * 5, 300)

PRIORITY_BOOST = 15.0


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _data_quality(last_event_time, now: datetime) -> str:
    if not last_event_time:
        return "STALE"
    age = (now - _parse_ts(last_event_time)).total_seconds()
    return "OK" if age <= STALE_THRESHOLD_SECONDS else "STALE"


def build_feed(user_id: str) -> dict:
    now = datetime.now(timezone.utc)

    # ── Watched instruments across all of this user's watchlists ──────
    wl_ids = [w["id"] for w in supabase.table("watchlists").select("id").eq("user_id", user_id).execute().data]
    watched: dict[str, dict] = {}
    if wl_ids:
        rows = (
            supabase.table("watchlist_items")
            .select("instrument_id, priority, muted, instruments(ticker)")
            .in_("watchlist_id", wl_ids)
            .execute()
            .data
        )
        for row in rows:
            iid = row["instrument_id"]
            entry = watched.setdefault(
                iid, {"ticker": row["instruments"]["ticker"], "priority": "NORMAL", "muted": False}
            )
            if row.get("priority") == "HIGH":
                entry["priority"] = "HIGH"
            if row.get("muted"):
                entry["muted"] = True

    active = {iid: meta for iid, meta in watched.items() if not meta["muted"]}
    if not active:
        return {
            "last_checked": now.isoformat(),
            "summary": {"high": 0, "medium": 0, "quiet": 0},
            "items": [],
            "market_brief": deterministic_brief([]),
        }

    instrument_ids = list(active.keys())

    # ── Latest signal per instrument ───────────────────────────────
    signal_rows = (
        supabase.table("signals")
        .select("*")
        .in_("instrument_id", instrument_ids)
        .order("event_time", desc=True)
        .execute()
        .data
    )
    latest_signal: dict[str, dict] = {}
    for row in signal_rows:
        latest_signal.setdefault(row["instrument_id"], row)  # first hit per id = latest (desc order)

    # ── This user's last-seen checkpoint per instrument ─────────────
    state_rows = (
        supabase.table("user_instrument_state")
        .select("*")
        .eq("user_id", user_id)
        .in_("instrument_id", instrument_ids)
        .execute()
        .data
    )
    last_seen = {row["instrument_id"]: row for row in state_rows}

    # ── Freshness / current price per instrument ────────────────────
    stats_rows = (
        supabase.table("instrument_stats")
        .select("*")
        .in_("instrument_id", instrument_ids)
        .execute()
        .data
    )
    stats_by_instrument = {row["instrument_id"]: row for row in stats_rows}

    candidates = []
    quiet_count = 0

    for iid, meta in active.items():
        signal = latest_signal.get(iid)
        state = last_seen.get(iid)
        prior_seen_at = _parse_ts(state["last_seen_at"]) if state and state.get("last_seen_at") else None

        is_new = signal is not None and (
            prior_seen_at is None or _parse_ts(signal["event_time"]) > prior_seen_at
        )

        classification = (signal or {}).get("explanation", {}).get("classification", "IGNORE")

        if is_new and classification in ("HIGH", "MEDIUM"):
            boost = PRIORITY_BOOST if meta["priority"] == "HIGH" else 0.0
            adjusted_severity = min(100.0, signal["severity"] + boost)
            surface = "HIGH" if adjusted_severity >= 70 else "MEDIUM"
            stats = stats_by_instrument.get(iid, {})
            candidates.append(
                {
                    "instrument": meta["ticker"],
                    "instrument_id": iid,
                    "severity": round(adjusted_severity, 1),
                    "surface": surface,
                    "why": signal.get("explanation", {}).get("reasons", []),
                    "data_quality": _data_quality(stats.get("last_event_time"), now),
                }
            )
        else:
            quiet_count += 1

    candidates.sort(key=lambda c: c["severity"], reverse=True)

    cached_brief = _brief_cache.get(user_id)
    market_brief = cached_brief["brief"] if cached_brief else deterministic_brief(candidates)

    return {
        "last_checked": now.isoformat(),
        "summary": {
            "high": sum(1 for c in candidates if c["surface"] == "HIGH"),
            "medium": sum(1 for c in candidates if c["surface"] == "MEDIUM"),
            "quiet": quiet_count,
        },
        "items": candidates,
        "market_brief": market_brief,
    }


def mark_seen(user_id: str, instrument_id: str) -> None:
    """
    Explicitly advance this user's last-seen checkpoint for one
    instrument to its latest signal's event_time, guarded forward-only
    (never overwrites a newer checkpoint than the one being written).
    Called when the user actually opens an instrument's detail — not
    from build_feed()'s own read, so a passive background poll can
    never silently mark something "seen" on the user's behalf.
    """
    signal_rows = (
        supabase.table("signals")
        .select("event_time")
        .eq("instrument_id", instrument_id)
        .order("event_time", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not signal_rows:
        return
    new_seen_at = _parse_ts(signal_rows[0]["event_time"])

    existing = (
        supabase.table("user_instrument_state")
        .select("last_seen_at")
        .eq("user_id", user_id)
        .eq("instrument_id", instrument_id)
        .execute()
        .data
    )
    if existing and existing[0].get("last_seen_at"):
        if _parse_ts(existing[0]["last_seen_at"]) >= new_seen_at:
            return  # already at least this fresh — don't regress it

    stats_rows = (
        supabase.table("instrument_stats")
        .select("last_price")
        .eq("instrument_id", instrument_id)
        .execute()
        .data
    )
    price = stats_rows[0]["last_price"] if stats_rows else None

    supabase.table("user_instrument_state").upsert(
        {
            "user_id": user_id,
            "instrument_id": instrument_id,
            "last_seen_at": new_seen_at.isoformat(),
            "last_seen_price": price,
        },
        on_conflict="user_id,instrument_id",
    ).execute()
