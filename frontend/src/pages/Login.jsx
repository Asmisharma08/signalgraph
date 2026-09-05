/**
 * SignalGraph — Login Page
 * =========================
 * Single email field that triggers Supabase magic-link sign-in.
 *
 * Flow:
 *   1. User enters email
 *   2. We call supabase.auth.signInWithOtp({ email })
 *   3. User clicks the link in their email
 *   4. Supabase redirects back here, session is established
 *   5. App redirects to the Feed page
 *
 * This page is shown when there is no active session.
 */

import { useState } from 'react';
import { supabase } from '../lib/supabaseClient';

export default function Login() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // After clicking the magic link, redirect back to the app
        emailRedirectTo: window.location.origin,
      },
    });

    if (authError) {
      setError(authError.message);
    } else {
      setMessage('Check your email for the magic link!');
    }

    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">
            <span className="logo-signal">Signal</span>
            <span className="logo-graph">Graph</span>
          </h1>
          <p className="login-subtitle">
            Your watchlist, but smarter. See only what matters.
          </p>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <label htmlFor="email-input" className="input-label">
              Email address
            </label>
            <input
              id="email-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              disabled={loading}
              className="input-field"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="login-button"
          >
            {loading ? 'Sending...' : 'Send Magic Link'}
          </button>
        </form>

        {message && (
          <div className="login-message success">{message}</div>
        )}
        {error && (
          <div className="login-message error">{error}</div>
        )}

        <p className="login-footnote">
          No password needed — we'll send a sign-in link to your email.
        </p>
      </div>
    </div>
  );
}
