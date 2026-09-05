"""
SignalGraph — Notification Decision (Milestone 7)
===================================================
Exposes: decide_channel(user_id, instrument_id, severity) -> str

Returns one of: "PUSH", "IN_APP", or "SUPPRESS"

Includes a one-push-per-instrument-per-hour cooldown enforced by
querying prior entries in notification_log.

Implementation deferred to Milestone 7.
"""
