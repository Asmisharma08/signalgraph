"""
SignalGraph — Yahoo Finance Poller (Milestone 4)
=================================================
Live market data source using yfinance.

Runs as an apscheduler job at POLL_INTERVAL_SECONDS intervals.
Fetches latest price/volume for all 20 instruments and feeds each
through pipeline.process_event().

Error handling: each instrument's fetch is wrapped individually, so
one instrument's failure (bad ticker, network blip, no data returned)
simply leaves that instrument's instrument_stats un-refreshed for this
cycle — the other nineteen continue updating normally. There is no
explicit "mark as stale" write: staleness is derived at read time
(Milestone 6's feed) from how long it's been since last_event_time
last moved forward, so a silently-skipped instrument naturally reads
as stale once enough cycles have passed without it.
"""

import threading
from datetime import datetime, timezone

import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import POLL_INTERVAL_SECONDS
from app.db import supabase
from app.ingestion.pipeline import process_event
from app.signals.scoring import evaluate_and_record_signal

SOURCE = "yahoo"
_scheduler = None


def _instrument_ids() -> dict:
    result = supabase.table("instruments").select("id, ticker").execute()
    return {row["ticker"]: row["id"] for row in result.data}


def poll_once() -> None:
    """
    Fetch the latest price/volume for every seeded instrument and feed
    each one through the shared ingestion pipeline, one instrument at a
    time. A failure fetching or processing one ticker is caught and
    logged; it does not prevent the remaining instruments in this cycle
    from updating.
    """
    ids = _instrument_ids()
    if not ids:
        print("[YAHOO] No instruments seeded yet — skipping this cycle.")
        return

    for ticker, instrument_id in ids.items():
        try:
            info = yf.Ticker(ticker).fast_info
            price = float(info.last_price)
            volume = int(info.last_volume)
            # fast_info doesn't provide a timestamp — use wall-clock
            # time, which is correct for "the price right now."
            event_time = datetime.now(timezone.utc)

            outcome = process_event(instrument_id, price, volume, event_time, SOURCE)
            if outcome is None:
                print(f"[YAHOO] {ticker}: event rejected (invalid or duplicate)")
            else:
                print(f"[YAHOO] {ticker}: {outcome.status} price={price} volume={volume}")
                signal = evaluate_and_record_signal(outcome)
                if signal is not None:
                    print(f"[YAHOO] {ticker}: SIGNAL severity={signal['severity']} "
                          f"({signal['classification']}) {signal['reasons']}")
        except Exception as exc:
            print(f"[YAHOO] {ticker}: fetch failed ({exc}) — stats untouched this cycle")


def start_scheduler() -> None:
    """
    Start the recurring polling job. Called once from main.py's lifespan
    when REPLAY_MODE is false. Runs an immediate poll on a background
    thread (so app startup isn't blocked on ~20 sequential network
    calls), then schedules poll_once() every POLL_INTERVAL_SECONDS.
    """
    global _scheduler
    threading.Thread(target=poll_once, daemon=True).start()

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(poll_once, "interval", seconds=POLL_INTERVAL_SECONDS, id="yahoo_poll")
    _scheduler.start()
    print(f"[YAHOO] Scheduler started — polling every {POLL_INTERVAL_SECONDS}s")


if __name__ == "__main__":
    poll_once()
