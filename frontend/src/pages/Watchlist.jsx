/**
 * SignalGraph — Watchlist Page (Milestone 2)
 * ============================================
 * Fully functional watchlist management UI.
 *
 * Features:
 *   - Auto-creates a watchlist on first visit if none exists
 *   - Shows the fixed 20-instrument universe grouped by sector
 *   - Toggle instruments in/out of the watchlist (add/remove)
 *   - Set priority (NORMAL / HIGH) per instrument
 *   - Mute/unmute individual instruments
 *   - Persists everything to Supabase via the backend API
 *   - Refreshing the page shows the same state (proof for Milestone 2)
 */

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../lib/api';

// The fixed 20-instrument universe, grouped by sector.
// This matches the backend's SEED_INSTRUMENTS exactly.
const INSTRUMENT_UNIVERSE = [
  { sector: 'Information Technology', tickers: ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'] },
  { sector: 'Banking', tickers: ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'] },
  { sector: 'Energy and Utilities', tickers: ['RELIANCE.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS'] },
  { sector: 'Consumer Goods', tickers: ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS'] },
  { sector: 'Automotive', tickers: ['TMPV.NS', 'MARUTI.NS', 'M&M.NS'] },
];

// Friendly names for tickers
const TICKER_NAMES = {
  'TCS.NS': 'Tata Consultancy Services',
  'INFY.NS': 'Infosys',
  'WIPRO.NS': 'Wipro',
  'HCLTECH.NS': 'HCL Technologies',
  'TECHM.NS': 'Tech Mahindra',
  'HDFCBANK.NS': 'HDFC Bank',
  'ICICIBANK.NS': 'ICICI Bank',
  'SBIN.NS': 'State Bank of India',
  'KOTAKBANK.NS': 'Kotak Mahindra Bank',
  'AXISBANK.NS': 'Axis Bank',
  'RELIANCE.NS': 'Reliance Industries',
  'ONGC.NS': 'Oil and Natural Gas Corp',
  'NTPC.NS': 'NTPC Limited',
  'POWERGRID.NS': 'Power Grid Corp',
  'HINDUNILVR.NS': 'Hindustan Unilever',
  'ITC.NS': 'ITC Limited',
  'NESTLEIND.NS': 'Nestle India',
  'TMPV.NS': 'Tata Motors Passenger Vehicles',
  'MARUTI.NS': 'Maruti Suzuki',
  'M&M.NS': 'Mahindra & Mahindra',
};

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState(null);   // { id, name, items: [...] }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(''); // ticker currently being toggled

  // Load watchlists on mount
  const loadWatchlists = useCallback(async () => {
    try {
      setError('');
      const res = await apiFetch('/api/watchlists');
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.error?.message || 'Failed to load watchlists');
      }

      if (data.length === 0) {
        // No watchlists exist yet — create one automatically
        const createRes = await apiFetch('/api/watchlists', {
          method: 'POST',
          body: JSON.stringify({ name: 'My Watchlist' }),
        });
        const created = await createRes.json();
        if (!createRes.ok) throw new Error(created?.error?.message || 'Failed to create watchlist');
        setWatchlist({ id: created.id, name: created.name, items: [] });
      } else {
        // Use the first (and typically only) watchlist
        setWatchlist(data[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWatchlists();
  }, [loadWatchlists]);

  // Check if a ticker is in the watchlist
  const isInWatchlist = (ticker) => {
    if (!watchlist) return false;
    return watchlist.items.some((item) => item.ticker === ticker);
  };

  // Get watchlist item for a ticker
  const getItem = (ticker) => {
    if (!watchlist) return null;
    return watchlist.items.find((item) => item.ticker === ticker) || null;
  };

  // Add a ticker to the watchlist
  const addTicker = async (ticker) => {
    if (!watchlist) return;
    setActionLoading(ticker);
    try {
      const res = await apiFetch(`/api/watchlists/${watchlist.id}/items`, {
        method: 'POST',
        body: JSON.stringify({ ticker }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.error?.message || 'Failed to add');
      }
      await loadWatchlists();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  };

  // Remove a ticker from the watchlist
  const removeTicker = async (ticker) => {
    if (!watchlist) return;
    const item = getItem(ticker);
    if (!item) return;
    setActionLoading(ticker);
    try {
      await apiFetch(`/api/watchlists/${watchlist.id}/items/${item.instrument_id}`, {
        method: 'DELETE',
      });
      await loadWatchlists();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  };

  // Toggle priority between NORMAL and HIGH
  const togglePriority = async (ticker) => {
    if (!watchlist) return;
    const item = getItem(ticker);
    if (!item) return;
    setActionLoading(`priority-${ticker}`);
    try {
      const newPriority = item.priority === 'HIGH' ? 'NORMAL' : 'HIGH';
      const res = await apiFetch(
        `/api/watchlists/${watchlist.id}/items/${item.instrument_id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ priority: newPriority }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.error?.message || 'Failed to update');
      }
      await loadWatchlists();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  };

  // Toggle muted status
  const toggleMuted = async (ticker) => {
    if (!watchlist) return;
    const item = getItem(ticker);
    if (!item) return;
    setActionLoading(`mute-${ticker}`);
    try {
      const res = await apiFetch(
        `/api/watchlists/${watchlist.id}/items/${item.instrument_id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ muted: !item.muted }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.error?.message || 'Failed to update');
      }
      await loadWatchlists();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  };

  // ── Render ───────────────────────────────────────────────
  if (loading) {
    return (
      <div className="page-container">
        <div className="watchlist-loading">
          <div className="spinner" />
          <p>Loading your watchlist...</p>
        </div>
      </div>
    );
  }

  const watchedCount = watchlist ? watchlist.items.length : 0;

  return (
    <div className="page-container">
      <div className="watchlist-header">
        <div>
          <h2>My Watchlist</h2>
          <p className="watchlist-subtitle">
            {watchedCount === 0
              ? 'Add instruments to start getting signals'
              : `Watching ${watchedCount} instrument${watchedCount > 1 ? 's' : ''}`}
          </p>
        </div>
      </div>

      {error && (
        <div className="watchlist-error">
          <span>⚠</span> {error}
          <button onClick={() => setError('')} className="error-dismiss">✕</button>
        </div>
      )}

      <div className="sector-grid">
        {INSTRUMENT_UNIVERSE.map((sector) => (
          <div key={sector.sector} className="sector-card">
            <div className="sector-header">
              <span className="sector-icon">
                {sector.sector === 'Information Technology' && '💻'}
                {sector.sector === 'Banking' && '🏦'}
                {sector.sector === 'Energy and Utilities' && '⚡'}
                {sector.sector === 'Consumer Goods' && '🛒'}
                {sector.sector === 'Automotive' && '🚗'}
              </span>
              <h3 className="sector-name">{sector.sector}</h3>
            </div>

            <div className="instrument-list">
              {sector.tickers.map((ticker) => {
                const watched = isInWatchlist(ticker);
                const item = getItem(ticker);
                const isToggling = actionLoading === ticker;

                return (
                  <div
                    key={ticker}
                    className={`instrument-row ${watched ? 'watched' : ''}`}
                  >
                    <div className="instrument-info">
                      <span className="instrument-ticker">{ticker.replace('.NS', '')}</span>
                      <span className="instrument-name">{TICKER_NAMES[ticker]}</span>
                    </div>

                    <div className="instrument-actions">
                      {watched && (
                        <>
                          <button
                            className={`action-btn priority-btn ${item?.priority === 'HIGH' ? 'is-high' : ''}`}
                            onClick={() => togglePriority(ticker)}
                            disabled={actionLoading.startsWith('priority')}
                            title={item?.priority === 'HIGH' ? 'Priority: HIGH — click to set NORMAL' : 'Priority: NORMAL — click to set HIGH'}
                          >
                            {item?.priority === 'HIGH' ? '⭐' : '☆'}
                          </button>
                          <button
                            className={`action-btn mute-btn ${item?.muted ? 'is-muted' : ''}`}
                            onClick={() => toggleMuted(ticker)}
                            disabled={actionLoading.startsWith('mute')}
                            title={item?.muted ? 'Muted — click to unmute' : 'Active — click to mute'}
                          >
                            {item?.muted ? '🔇' : '🔔'}
                          </button>
                        </>
                      )}
                      <button
                        className={`toggle-btn ${watched ? 'remove' : 'add'}`}
                        onClick={() => (watched ? removeTicker(ticker) : addTicker(ticker))}
                        disabled={isToggling}
                      >
                        {isToggling ? '...' : watched ? '✕' : '+'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
