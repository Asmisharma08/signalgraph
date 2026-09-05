/**
 * SignalGraph — Freshness Badge Component (Milestone 4/9)
 * ========================================================
 * Renders a visual indicator of data freshness:
 *   - "Live"    (green)  — data_quality === "OK" and recent
 *   - "Delayed" (yellow) — data is slightly behind
 *   - "Stale"   (red)    — data_quality === "STALE"
 *
 * Used in Feed.jsx next to each instrument's card.
 *
 * Implementation deferred to Milestone 9 (polish).
 */

export default function FreshnessBadge({ quality = 'OK' }) {
  const label = quality === 'OK' ? 'Live' : 'Stale';
  const className = `freshness-badge ${quality === 'OK' ? 'badge-live' : 'badge-stale'}`;

  return (
    <span className={className}>{label}</span>
  );
}
