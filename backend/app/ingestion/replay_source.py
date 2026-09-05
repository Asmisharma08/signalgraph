"""
SignalGraph — Replay Source (Milestone 3)
==========================================
Scripted, deterministic event sequence for demo and testing.

Exposes: run_replay_sequence() -> None

Plays a hardcoded sequence of events through pipeline.process_event(),
pacing each event 3-5 seconds apart. Includes:
  - Baseline prices for all 20 instruments
  - Four small normal updates on TCS.NS (seeds its rolling volatility)
  - Volume spike on TCS.NS (~3x its seeded baseline volume)
  - Price move on TCS.NS immediately afterward (large vs. seeded volatility)
  - Exact duplicate of that same TCS.NS price event (must be rejected)
  - Late-arriving INFY.NS event (stored, but must not overwrite instrument_stats)
  - Structural update on RELIANCE.NS (new all-time-high in the replay)

Invoked on startup when REPLAY_MODE=true, or manually via:
    cd backend && python -m app.ingestion.replay_source
"""

import time
from datetime import datetime, timedelta, timezone

from app.db import supabase
from app.ingestion.pipeline import process_event
from app.signals.scoring import evaluate_and_record_signal

SOURCE = "replay"
PACING_SECONDS = 3

# ticker -> (baseline price INR, baseline volume shares)
BASELINE = {
    "TCS.NS": (3800.0, 2_000_000),
    "INFY.NS": (1550.0, 3_000_000),
    "WIPRO.NS": (480.0, 4_000_000),
    "HCLTECH.NS": (1750.0, 1_500_000),
    "TECHM.NS": (1400.0, 1_200_000),
    "HDFCBANK.NS": (1650.0, 5_000_000),
    "ICICIBANK.NS": (1200.0, 4_500_000),
    "SBIN.NS": (810.0, 6_000_000),
    "KOTAKBANK.NS": (1750.0, 1_800_000),
    "AXISBANK.NS": (1150.0, 3_200_000),
    "RELIANCE.NS": (2900.0, 5_500_000),
    "ONGC.NS": (260.0, 3_000_000),
    "NTPC.NS": (360.0, 4_000_000),
    "POWERGRID.NS": (320.0, 3_500_000),
    "HINDUNILVR.NS": (2400.0, 900_000),
    "ITC.NS": (460.0, 7_000_000),
    "NESTLEIND.NS": (2350.0, 200_000),
    "TMPV.NS": (950.0, 6_500_000),
    "MARUTI.NS": (12500.0, 400_000),
    "M&M.NS": (2850.0, 1_000_000),
}


def _instrument_ids() -> dict:
    result = supabase.table("instruments").select("id, ticker").execute()
    return {row["ticker"]: row["id"] for row in result.data}


def _log(label: str, ticker: str, outcome):
    if outcome is None:
        print(f"[REPLAY] {label:<28} {ticker:<12} -> REJECTED (duplicate/invalid)")
    else:
        print(f"[REPLAY] {label:<28} {ticker:<12} -> {outcome.status.upper()} "
              f"(price={outcome.price}, seq={outcome.sequence_number})")


def _ingest(label: str, ticker: str, instrument_id: str, price: float, volume: int, event_time):
    """process_event() + Milestone 5's signal evaluation, in one place so
    every call site in the sequence gets both without repeating itself."""
    outcome = process_event(instrument_id, price, volume, event_time, SOURCE)
    _log(label, ticker, outcome)
    if outcome is not None:
        signal = evaluate_and_record_signal(outcome)
        if signal is not None:
            print(f"[REPLAY] {'':<28} {ticker:<12} -> SIGNAL severity={signal['severity']} "
                  f"({signal['classification']}) {signal['reasons']}")
    return outcome


def run_replay_sequence() -> None:
    ids = _instrument_ids()
    if not ids:
        print("[REPLAY] No instruments found — has the schema been seeded? Aborting.")
        return

    print(f"[REPLAY] Starting replay sequence ({len(ids)} instruments known)")
    t0 = datetime(2026, 9, 1, 9, 0, 0, tzinfo=timezone.utc)  # Fixed anchor per Decision Log

    # ── 1. Baseline: one tick for every instrument ──────────────
    for ticker, (price, volume) in BASELINE.items():
        if ticker not in ids:
            continue
        _ingest("baseline", ticker, ids[ticker], price, volume, t0)
    time.sleep(PACING_SECONDS)

    # ── 2. Three or four small, normal updates on TCS.NS ─────────
    # Seeds TCS.NS's rolling volatility so the later anomaly reads as
    # genuinely unusual relative to its own recent behavior.
    tcs_id = ids.get("TCS.NS")
    tcs_price, tcs_volume = BASELINE["TCS.NS"]
    small_moves = [0.002, -0.0015, 0.0025, -0.001]  # +0.2%, -0.15%, +0.25%, -0.1%
    running_price = tcs_price
    for i, move in enumerate(small_moves, start=1):
        running_price = round(running_price * (1 + move), 2)
        event_time = t0 + timedelta(minutes=i)
        _ingest(
            f"small update #{i}", "TCS.NS", tcs_id,
            running_price, int(tcs_volume * (1 + move / 4)), event_time,
        )
        time.sleep(PACING_SECONDS)

    # ── 3. Volume spike on TCS.NS (~2.4x baseline volume, price barely moves) ──
    # Deliberately tuned to stay under the 20-point severity floor on its
    # own (volume anomaly alone isn't enough to cross it) — the pair's
    # single signal is meant to come from the price-move event next,
    # whose own volume is still elevated relative to the freshly-bumped
    # rolling average this tick leaves behind.
    spike_time = t0 + timedelta(minutes=len(small_moves) + 1)
    spike_price = round(running_price * 1.001, 2)
    spike_volume = int(tcs_volume * 2.4)
    _ingest("volume spike", "TCS.NS", tcs_id, spike_price, spike_volume, spike_time)
    time.sleep(PACING_SECONDS)

    # ── 4. Price move on TCS.NS immediately afterward, large vs. seeded volatility ──
    move_time = t0 + timedelta(minutes=len(small_moves) + 2)
    move_price = round(spike_price * 1.06, 2)  # ~6% jump
    move_volume = int(tcs_volume * 2.8)
    _ingest("price move", "TCS.NS", tcs_id, move_price, move_volume, move_time)
    time.sleep(PACING_SECONDS)

    # ── 5. Exact duplicate of the price-move event — must be rejected ──
    dup_outcome = _ingest("duplicate of price move", "TCS.NS", tcs_id, move_price, move_volume, move_time)
    assert dup_outcome is None, "duplicate TCS.NS event was not rejected!"
    time.sleep(PACING_SECONDS)

    # ── 6. Late-arriving INFY.NS event (earlier than the baseline tick) ──
    infy_id = ids.get("INFY.NS")
    infy_price, infy_volume = BASELINE["INFY.NS"]
    late_time = t0 - timedelta(minutes=10)
    late_price = round(infy_price * 0.995, 2)
    late_outcome = _ingest("late-arriving event", "INFY.NS", infy_id, late_price, infy_volume, late_time)
    if late_outcome is not None:
        assert late_outcome.status == "late", "INFY.NS event should have been marked late!"
    time.sleep(PACING_SECONDS)

    # ── 7. Structural update on RELIANCE.NS (new high for the replay) ──
    rel_id = ids.get("RELIANCE.NS")
    rel_price, rel_volume = BASELINE["RELIANCE.NS"]
    structural_time = t0 + timedelta(minutes=len(small_moves) + 3)
    structural_price = round(rel_price * 1.06, 2)  # breaks above the seeded baseline high
    _ingest(
        "structural update", "RELIANCE.NS", rel_id,
        structural_price, int(rel_volume * 1.8), structural_time,
    )

    print("[REPLAY] Sequence complete.")


if __name__ == "__main__":
    run_replay_sequence()
