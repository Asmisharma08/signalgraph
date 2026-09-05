/**
 * SignalGraph — Feed Page (Milestone 6)
 * =======================================
 * The hero screen. Polls GET /api/feed every 10-15 seconds and renders
 * the ranked attention list, with everything else folded into a single
 * "nothing unusual" quiet line.
 *
 * Opening a card's detail marks it seen (POST /api/feed/seen/{id}) —
 * the background poll itself never does this, so a signal can't
 * silently disappear into the quiet count before the user notices it.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from '../lib/api';
import FreshnessBadge from '../components/FreshnessBadge';

const POLL_MS = 12000;

export default function Feed({ onSelectInstrument }) {
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const timerRef = useRef(null);

  const loadFeed = useCallback(async () => {
    try {
      const res = await apiFetch('/api/feed');
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error?.message || 'Failed to load feed');
      setFeed(data);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const openInstrument = (instrumentId, ticker) => {
    onSelectInstrument?.(instrumentId, ticker);
    // Fire-and-forget: don't block navigation on this.
    apiFetch(`/api/feed/seen/${instrumentId}`, { method: 'POST' }).catch(() => {});
  };

  useEffect(() => {
    loadFeed();
    timerRef.current = setInterval(loadFeed, POLL_MS);
    return () => clearInterval(timerRef.current);
  }, [loadFeed]);

  if (loading) {
    return (
      <div className="page-container">
        <div className="watchlist-loading">
          <div className="spinner" />
          <p>Scanning your watchlist...</p>
        </div>
      </div>
    );
  }

  if (error && !feed) {
    return (
      <div className="page-container">
        <div className="watchlist-error">
          <span>⚠</span> {error}
        </div>
      </div>
    );
  }

  const items = feed?.items || [];
  const summary = feed?.summary || { high: 0, medium: 0, quiet: 0 };
  const totalWatched = summary.high + summary.medium + summary.quiet;

  return (
    <div className="page-container">
      <div className="feed-header">
        <div>
          <h2>Attention Feed</h2>
          <p className="watchlist-subtitle">
            {items.length === 0
              ? totalWatched === 0
                ? 'Add instruments to your watchlist to start getting signals'
                : 'Nothing unusual right now — everything is within normal behavior'
              : `${items.length} thing${items.length > 1 ? 's' : ''} that actually changed`}
          </p>
        </div>
        {feed?.last_checked && (
          <span className="last-checked">
            Last checked {new Date(feed.last_checked).toLocaleTimeString()}
          </span>
        )}
      </div>

      {feed?.market_brief && (
        <div className="market-brief">
          <span className="market-brief-label">Brief</span>
          <p>{feed.market_brief}</p>
        </div>
      )}

      {items.length > 0 && (
        <div className="feed-list">
          {items.map((item) => (
            <div
              key={item.instrument}
              className={`feed-card surface-${item.surface.toLowerCase()}`}
              onClick={() => openInstrument(item.instrument_id, item.instrument)}
              role="button"
              tabIndex={0}
            >
              <div className="feed-card-header">
                <span className="feed-card-ticker">{item.instrument.replace('.NS', '')}</span>
                <span className={`surface-badge surface-${item.surface.toLowerCase()}`}>
                  {item.surface}
                </span>
                <FreshnessBadge quality={item.data_quality} />
              </div>
              <div className="feed-card-severity">Severity {Math.round(item.severity)}</div>
              <ul className="feed-card-why">
                {item.why.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {totalWatched > 0 && (
        <div className="feed-quiet-summary">
          <span className="quiet-dot" />
          {summary.quiet} instrument{summary.quiet === 1 ? '' : 's'} quiet — nothing unusual
        </div>
      )}
    </div>
  );
}
