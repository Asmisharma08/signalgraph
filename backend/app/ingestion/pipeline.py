"""
SignalGraph — Ingestion Pipeline (Milestone 3)
================================================
Shared validation, deduplication, ordering, and rolling-statistics logic.

Exposes: process_event(instrument_id, price, volume, event_time, source) -> ProcessedEvent | None

This module is called by both replay_source.py and yahoo_source.py.
It is NEVER exposed over HTTP — there is no route for ingestion.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.db import supabase

# Exponential-moving-average smoothing factor, fixed per the ExecPlan.
EMA_ALPHA = 0.15


@dataclass
class ProcessedEvent:
    """
    Returned by process_event() on success. The caller (a source module,
    or signal detection in a later milestone) uses `status` only for
    logging/decision-making — "late" events are stored but do not move
    instrument_stats forward.
    """
    instrument_id: str
    price: float
    volume: Optional[int]
    event_time: datetime
    source: str
    sequence_number: int
    status: str  # "current" | "late"
    return_pct: float
    rolling_avg_return: float
    rolling_std_return: float
    rolling_avg_volume: float
    # The rolling stats as they stood BEFORE this event was folded in —
    # what signal detection must compare this event against. Using the
    # post-update values above for detection would always partially
    # compare an event to itself (the EMA update already blends 15% of
    # this very observation into them), making ordinary ticks look
    # artificially anomalous.
    prior_avg_return: float
    prior_std_return: float
    prior_avg_volume: float
    is_first_tick: bool


def _parse_ts(value) -> datetime:
    """Parse a Postgres/Supabase timestamptz string (or datetime) into an
    aware UTC datetime."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def process_event(
    instrument_id: str,
    price: float,
    volume: Optional[int],
    event_time: datetime,
    source: str,
) -> Optional[ProcessedEvent]:
    """
    Validate, deduplicate, order, and fold one market event into the
    instrument's rolling statistics.

    Returns None when the event is rejected by validation or is an exact
    duplicate (same source + instrument + event_time already stored).
    Otherwise returns a ProcessedEvent describing whether it was accepted
    as the current-latest event or stored as a late-arriving one.
    """
    # ── Validation ───────────────────────────────────────────
    if price is None or price <= 0:
        return None
    if volume is not None and volume < 0:
        return None
    if event_time is None:
        return None

    event_time = _parse_ts(event_time)

    # ── Deduplication ───────────────────────────────────────
    # market_events has no physical dedupe_key column/constraint, so the
    # exact-duplicate check is an application-level query against the
    # conceptual key (source, instrument_id, event_time) described in the
    # ExecPlan's Artifacts and Notes section.
    dup_check = (
        supabase.table("market_events")
        .select("id")
        .eq("instrument_id", instrument_id)
        .eq("source", source)
        .eq("event_time", event_time.isoformat())
        .execute()
    )
    if dup_check.data:
        return None

    # ── Load current stats (may not exist yet for a brand-new instrument) ──
    stats_result = (
        supabase.table("instrument_stats")
        .select("*")
        .eq("instrument_id", instrument_id)
        .execute()
    )
    stats = stats_result.data[0] if stats_result.data else None

    last_event_time = _parse_ts(stats["last_event_time"]) if stats and stats.get("last_event_time") else None
    last_price = stats["last_price"] if stats else None
    old_avg_return = stats["rolling_avg_return"] if stats else 0.0
    old_std_return = stats["rolling_std_return"] if stats else 0.0
    old_avg_volume = stats["rolling_avg_volume"] if stats else 0.0

    is_late = last_event_time is not None and event_time < last_event_time
    status = "late" if is_late else "current"

    # ── Rolling-statistics update (EMA, alpha = 0.15) ───────────
    # A late event does not move the instrument's "current" statistics
    # forward — it's stored for the record but instrument_stats keeps
    # whatever the most recent (by event_time) current event set.
    return_pct = 0.0
    new_avg_return = old_avg_return
    new_std_return = old_std_return
    new_avg_volume = old_avg_volume

    if not is_late:
        if last_price:
            return_pct = (price - last_price) / last_price

        if stats is None:
            # Bootstrap: this instrument's very first tick. Blending from
            # an artificial old_avg_volume=0 would permanently under-seed
            # the rolling average (e.g. it would start at just 15% of the
            # real baseline volume) and make every ordinary tick after it
            # look anomalous. Seed directly from this first observation
            # instead of running the EMA formula against a fake zero.
            new_avg_return = 0.0
            new_std_return = 0.0
            new_avg_volume = float(volume or 0)
        else:
            new_avg_return = old_avg_return * 0.85 + return_pct * 0.15
            new_std_return = (
                (old_std_return ** 2) * 0.85 + ((return_pct - new_avg_return) ** 2) * 0.15
            ) ** 0.5
            new_avg_volume = old_avg_volume * 0.85 + (volume or 0) * 0.15

        supabase.table("instrument_stats").upsert(
            {
                "instrument_id": instrument_id,
                "rolling_avg_return": new_avg_return,
                "rolling_std_return": new_std_return,
                "rolling_avg_volume": new_avg_volume,
                "last_price": price,
                "last_event_time": event_time.isoformat(),
                # Postgres's `default now()` only fires on INSERT, not on an
                # UPDATE-via-upsert into an existing row, so this must be set
                # explicitly or updated_at silently freezes at first-insert time.
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="instrument_id",
        ).execute()

    # ── Sequence number (per-instrument, assigned by SignalGraph) ──
    seq_result = (
        supabase.table("market_events")
        .select("sequence_number")
        .eq("instrument_id", instrument_id)
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    )
    next_seq = (seq_result.data[0]["sequence_number"] + 1) if seq_result.data else 1

    # ── Insert the event row ─────────────────────────────────
    supabase.table("market_events").insert(
        {
            "instrument_id": instrument_id,
            "price": price,
            "volume": volume,
            "event_time": event_time.isoformat(),
            "source": source,
            "sequence_number": next_seq,
            "data_quality": "OK",
        }
    ).execute()

    return ProcessedEvent(
        instrument_id=instrument_id,
        price=price,
        volume=volume,
        event_time=event_time,
        source=source,
        sequence_number=next_seq,
        status=status,
        return_pct=return_pct,
        rolling_avg_return=new_avg_return,
        rolling_std_return=new_std_return,
        rolling_avg_volume=new_avg_volume,
        prior_avg_return=old_avg_return,
        prior_std_return=old_std_return,
        prior_avg_volume=old_avg_volume,
        is_first_tick=stats is None,
    )
