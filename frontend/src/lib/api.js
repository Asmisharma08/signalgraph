/**
 * SignalGraph — API Helper
 * =========================
 * Centralized fetch wrapper that:
 *   1. Reads the current Supabase session
 *   2. Attaches the access token as Authorization: Bearer <token>
 *   3. Redirects to login if no session exists
 *   4. Provides consistent error handling
 *
 * Every frontend page uses this instead of raw fetch().
 */

import { supabase } from './supabaseClient';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Make an authenticated API call to the backend.
 *
 * @param {string} path    — e.g. '/api/feed' (will be appended to API_BASE)
 * @param {object} options — standard fetch options (method, body, headers, etc.)
 * @returns {Promise<Response>} — the raw fetch Response
 * @throws {Error} if no session exists (caller should redirect to login)
 */
export async function apiFetch(path, options = {}) {
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    // No session — caller should redirect to Login.
    // We throw rather than silently returning so the caller can handle it.
    throw new Error('NOT_AUTHENTICATED');
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  return response;
}

/**
 * Make an unauthenticated API call (e.g. health check).
 * Does NOT attach any Authorization header.
 */
export async function publicFetch(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  return fetch(`${API_BASE}${path}`, { ...options, headers });
}
