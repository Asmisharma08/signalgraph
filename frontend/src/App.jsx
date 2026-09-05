/**
 * SignalGraph — Main App Component
 * ==================================
 * Handles:
 *   1. Auth state management (session tracking via Supabase)
 *   2. Page routing (Login ↔ authenticated pages)
 *   3. Health-check call to verify backend connectivity (Milestone 1)
 *   4. Navigation between Watchlist, Feed, and SignalDetail
 *
 * For Milestone 1, the key acceptance criterion is:
 *   "Opening the frontend and seeing a successful response from the backend."
 * So we call /api/health on mount and render the result.
 */

import { useState, useEffect } from 'react';
import { supabase } from './lib/supabaseClient';
import { publicFetch } from './lib/api';
import Login from './pages/Login';
import Feed from './pages/Feed';
import Watchlist from './pages/Watchlist';
import SignalDetail from './pages/SignalDetail';
import ChatWidget from './components/ChatWidget';

export default function App() {
  // ── Auth state ──────────────────────────────────────────
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // ── Health check (Milestone 1 proof) ────────────────────
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState('');

  // ── Simple client-side routing ──────────────────────────
  const [currentPage, setCurrentPage] = useState('feed');
  const [selectedInstrument, setSelectedInstrument] = useState(null); // { id, ticker }

  const openSignalDetail = (id, ticker) => {
    setSelectedInstrument({ id, ticker });
    setCurrentPage('signal-detail');
  };

  // Check existing session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setAuthLoading(false);
    });

    // Subscribe to auth state changes (handles token refresh mid-session,
    // as required by the ExecPlan for Feed.jsx)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  // Call health-check on mount (Milestone 1 acceptance proof)
  useEffect(() => {
    publicFetch('/api/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setHealthError(err.message));
  }, []);

  // ── Loading state ───────────────────────────────────────
  if (authLoading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading SignalGraph...</p>
      </div>
    );
  }

  // ── Not authenticated → Login ───────────────────────────
  if (!session) {
    return (
      <>
        <Login />
        {/* Show health status even on login page for Milestone 1 demo */}
        <div className="health-status">
          {health ? (
            <span className="health-ok">
              ✓ Backend connected — v{health.version} ({health.replay_mode ? 'Replay' : 'Live'} mode)
            </span>
          ) : healthError ? (
            <span className="health-error">
              ✗ Backend unreachable: {healthError}
            </span>
          ) : (
            <span className="health-checking">Connecting to backend...</span>
          )}
        </div>
      </>
    );
  }

  // ── Authenticated → Main app ────────────────────────────
  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'feed':
        return <Feed onSelectInstrument={openSignalDetail} />;
      case 'watchlist':
        return <Watchlist />;
      case 'signal-detail':
        return (
          <SignalDetail
            instrumentId={selectedInstrument?.id}
            ticker={selectedInstrument?.ticker}
            onBack={() => setCurrentPage('feed')}
          />
        );
      default:
        return <Feed onSelectInstrument={openSignalDetail} />;
    }
  };

  return (
    <div className="app-container">
      {/* Navigation */}
      <nav className="app-nav">
        <div className="nav-brand">
          <span className="logo-signal">Signal</span>
          <span className="logo-graph">Graph</span>
        </div>

        <div className="nav-links">
          <button
            className={`nav-link ${currentPage === 'feed' ? 'active' : ''}`}
            onClick={() => setCurrentPage('feed')}
          >
            Feed
          </button>
          <button
            className={`nav-link ${currentPage === 'watchlist' ? 'active' : ''}`}
            onClick={() => setCurrentPage('watchlist')}
          >
            Watchlist
          </button>
        </div>

        <div className="nav-user">
          <span className="user-email">{session.user.email}</span>
          <button className="logout-button" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </nav>

      {/* Health banner */}
      <div className="health-banner">
        {health ? (
          <span className="health-ok">
            ✓ v{health.version} • {health.replay_mode ? 'Replay' : 'Live'} mode
          </span>
        ) : healthError ? (
          <span className="health-error">✗ Backend unreachable</span>
        ) : null}
      </div>

      {/* Page content */}
      <main className="app-main">
        {renderPage()}
      </main>

      <ChatWidget />
    </div>
  );
}
