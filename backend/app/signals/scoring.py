"""
SignalGraph — Severity Scoring (Milestone 5)
=============================================
Combines the four detector scores into a single severity value.

Exposes: compute_severity(price_anomaly, volume_anomaly, sector_divergence, structural_trigger) -> dict

Weights: price 0.40, volume 0.25, sector 0.15, structural 0.20
Bands:   HIGH >= 70, MEDIUM >= 40, LOW >= 20, IGNORE < 20
Floor:   No signal row is written if severity < 20.

Also exposes evaluate_and_record_signal(processed), the orchestration
glue that both replay_source.py and yahoo_source.py call right after a
successful process_event(): it looks up the sector peer basket and
historical high/low, runs the four detectors, calls compute_severity(),
and — if the floor is cleared — upserts a row into `signals`. This
function isn't named in the ExecPlan's Interfaces and Dependencies
section (which only fixes compute_severity's own signature), but a
shared place to do this was needed so replay and live ingestion don't
duplicate it; see the Decision Log entry dated when Milestone 5 was
implemented.
"""

from app.db import supabase
from app.notifications.decision import notify_interested_users
from app.signals.detectors import (
    price_anomaly_score,
    volume_anomaly_score,
    sector_divergence_score,
    structural_trigger_score,
)

WEIGHT_PRICE = 0.40
WEIGHT_VOLUME = 0.25
WEIGHT_SECTOR = 0.15
WEIGHT_STRUCTURAL = 0.20
SEVERITY_FLOOR = 20.0

# Hardcoded peer basket per sector (the ExecPlan's Decision Log rationale:
# no reliable free sector-index feed exists, so sector-relative return is
# computed from the other seeded instruments already sharing that sector).
SECTOR_PEERS = {
    "Information Technology": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "Energy and Utilities": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
    "Consumer Goods": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
    "Automotive": ["TMPV.NS", "MARUTI.NS", "M&M.NS"],
}


def compute_severity(
    price_anomaly: float,
    volume_anomaly: float,
    sector_divergence: float,
    structural_trigger: float,
) -> dict:
    severity = (
        price_anomaly * WEIGHT_PRICE
        + volume_anomaly * WEIGHT_VOLUME
        + sector_divergence * WEIGHT_SECTOR
        + structural_trigger * WEIGHT_STRUCTURAL
    )

    if severity >= 70:
        classification = "HIGH"
    elif severity >= 40:
        classification = "MEDIUM"
    elif severity >= SEVERITY_FLOOR:
        classification = "LOW"
    else:
        classification = "IGNORE"

    reasons = []
    if price_anomaly >= 50:
        reasons.append("Price moved well outside its normal range for this stock")
    if volume_anomaly >= 50:
        reasons.append("Volume is well above its rolling average")
    if sector_divergence >= 50:
        reasons.append("Moving significantly differently from its sector peers")
    if structural_trigger >= 50:
        reasons.append("Price broke through a recent high or low")

    return {
        "price_anomaly": round(price_anomaly, 1),
        "volume_anomaly": round(volume_anomaly, 1),
        "sector_divergence": round(sector_divergence, 1),
        "structural_trigger": round(structural_trigger, 1),
        "severity": round(severity, 1),
        "classification": classification,
        "reasons": reasons,
    }


def _instrument_lookup(instrument_id: str) -> dict | None:
    result = (
        supabase.table("instruments")
        .select("id, ticker, sector")
        .eq("id", instrument_id)
        .execute()
    )
    return result.data[0] if result.data else None


def _historical_high_low(instrument_id: str, before_sequence: int) -> tuple[float, float]:
    result = (
        supabase.table("market_events")
        .select("price")
        .eq("instrument_id", instrument_id)
        .lt("sequence_number", before_sequence)
        .execute()
    )
    prices = [row["price"] for row in result.data]
    if not prices:
        return (None, None)
    return (max(prices), min(prices))


def _sector_basket_return(sector: str, self_ticker: str) -> float:
    peer_tickers = [t for t in SECTOR_PEERS.get(sector, []) if t != self_ticker]
    if not peer_tickers:
        return 0.0
    peers = (
        supabase.table("instruments")
        .select("id, ticker")
        .in_("ticker", peer_tickers)
        .execute()
        .data
    )
    if not peers:
        return 0.0
    peer_ids = [p["id"] for p in peers]
    stats = (
        supabase.table("instrument_stats")
        .select("rolling_avg_return")
        .in_("instrument_id", peer_ids)
        .execute()
        .data
    )
    if not stats:
        return 0.0
    returns = [s["rolling_avg_return"] or 0.0 for s in stats]
    return sum(returns) / len(returns)


def evaluate_and_record_signal(processed) -> dict | None:
    """
    Run signal detection for a just-processed *current* market event and,
    if its severity clears the floor, write it to `signals`. Returns the
    stored signal dict, or None if no signal was warranted (or the event
    was a late-arriving one, which doesn't represent the current market
    state and is therefore never evaluated).
    """
    if processed.status != "current":
        return None

    # An instrument's very first tick has no rolling baseline to compare
    # against yet, so nothing about it can be called "anomalous."
    if processed.is_first_tick:
        return None

    instrument = _instrument_lookup(processed.instrument_id)
    if instrument is None:
        return None

    historical_high, historical_low = _historical_high_low(
        processed.instrument_id, processed.sequence_number
    )
    sector_basket_return = _sector_basket_return(instrument["sector"], instrument["ticker"])

    price_score = price_anomaly_score(
        processed.return_pct, processed.prior_avg_return, processed.prior_std_return
    )
    volume_score = volume_anomaly_score(processed.volume or 0, processed.prior_avg_volume)
    sector_score = sector_divergence_score(processed.return_pct, sector_basket_return)
    structural_score = structural_trigger_score(
        processed.price, historical_high or processed.price, historical_low or processed.price
    )

    result = compute_severity(price_score, volume_score, sector_score, structural_score)
    if result["severity"] < SEVERITY_FLOOR:
        return None

    # Precise, numeric reasons (uses raw values compute_severity's fixed
    # signature doesn't receive) layered on top of its generic ones.
    precise_reasons = []
    if price_score >= 50:
        precise_reasons.append(
            f"Price moved {processed.return_pct * 100:.1f}%, unusual for this stock"
        )
    if volume_score >= 50 and processed.prior_avg_volume:
        ratio = (processed.volume or 0) / processed.prior_avg_volume
        precise_reasons.append(f"Volume is {ratio:.1f}x rolling average")
    if sector_score >= 50:
        precise_reasons.append("Diverging sharply from its sector peers")
    if structural_score >= 50:
        precise_reasons.append("Price broke through a recent high or low")
    if precise_reasons:
        result["reasons"] = precise_reasons

    dominant = max(
        [
            ("PRICE_ANOMALY", price_score * WEIGHT_PRICE),
            ("VOLUME_ANOMALY", volume_score * WEIGHT_VOLUME),
            ("SECTOR_DIVERGENCE", sector_score * WEIGHT_SECTOR),
            ("STRUCTURAL_BREAK", structural_score * WEIGHT_STRUCTURAL),
        ],
        key=lambda pair: pair[1],
    )[0]

    dedupe_key = f"{processed.source}:{processed.instrument_id}:{processed.event_time.isoformat()}"

    signal_row = (
        supabase.table("signals")
        .upsert(
            {
                "instrument_id": processed.instrument_id,
                "signal_type": dominant,
                "severity": result["severity"],
                "event_time": processed.event_time.isoformat(),
                "explanation": result,
                "dedupe_key": dedupe_key,
            },
            on_conflict="dedupe_key",
        )
        .execute()
        .data[0]
    )

    notify_interested_users(processed.instrument_id, signal_row["id"], result["severity"])

    return result
