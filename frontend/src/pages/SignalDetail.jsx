/**
 * SignalGraph — Signal Detail Page (Milestone 5/9)
 * ==================================================
 * Renders one instrument's severity breakdown from the explanation
 * field returned by GET /api/signals/{instrument_id}.
 */

import { useState, useEffect } from 'react';
import { apiFetch } from '../lib/api';

const COMPONENTS = [
  { key: 'price_anomaly', label: 'Price anomaly', weight: '40%' },
  { key: 'volume_anomaly', label: 'Volume anomaly', weight: '25%' },
  { key: 'sector_divergence', label: 'Sector divergence', weight: '15%' },
  { key: 'structural_trigger', label: 'Structural trigger', weight: '20%' },
];

export default function SignalDetail({ instrumentId, ticker, onBack }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!instrumentId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/api/signals/${instrumentId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error?.message || 'Failed to load signal');
        if (!cancelled) setExplanation(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [instrumentId]);

  return (
    <div className="page-container">
      <button className="back-link" onClick={onBack}>&larr; Back to feed</button>

      {!instrumentId && (
        <p className="placeholder-text">Select an instrument from the feed to see its breakdown.</p>
      )}

      {instrumentId && loading && (
        <div className="watchlist-loading">
          <div className="spinner" />
          <p>Loading signal...</p>
        </div>
      )}

      {instrumentId && !loading && error && (
        <div className="watchlist-error"><span>⚠</span> {error}</div>
      )}

      {instrumentId && !loading && !error && explanation && (
        <div className="signal-detail">
          <h2>{ticker?.replace('.NS', '') || 'Signal'} breakdown</h2>
          <div className="signal-severity-row">
            <span className={`surface-badge surface-${(explanation.classification || '').toLowerCase()}`}>
              {explanation.classification}
            </span>
            <span className="signal-severity-value">Severity {explanation.severity}</span>
          </div>

          <div className="signal-components">
            {COMPONENTS.map((c) => (
              <div key={c.key} className="signal-component-row">
                <div className="signal-component-label">
                  <span>{c.label}</span>
                  <span className="signal-component-weight">weight {c.weight}</span>
                </div>
                <div className="signal-component-bar-track">
                  <div
                    className="signal-component-bar-fill"
                    style={{ width: `${Math.min(100, explanation[c.key] || 0)}%` }}
                  />
                </div>
                <span className="signal-component-value">{explanation[c.key] ?? 0}</span>
              </div>
            ))}
          </div>

          {explanation.reasons?.length > 0 && (
            <div className="signal-reasons">
              <h3>Why this was flagged</h3>
              <ul>
                {explanation.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
