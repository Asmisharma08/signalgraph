"""
SignalGraph — Personalized Relevance Feed (Milestone 6)
========================================================
The hero feature.

Exposes: build_feed(user_id: str) -> dict

Logic:
  1. Read user's watchlist instruments
  2. Read signals newer than user's last-seen state per instrument
  3. Drop muted instruments
  4. Apply priority boost for HIGH-priority items
  5. Sort by adjusted severity
  6. Split into ranked attention items + quiet count
  7. Update last-seen state (guarded against stale overwrites)

Implementation deferred to Milestone 6.
"""
