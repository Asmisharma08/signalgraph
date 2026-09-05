/**
 * SignalGraph — Supabase Browser Client
 * ======================================
 * Single instance of the Supabase client for the frontend.
 * Used for:
 *   1. Authentication (magic-link login)
 *   2. Reading the current session's access token for backend API calls
 *
 * Environment variables (set in .env or Vercel project settings):
 *   VITE_SUPABASE_URL      — e.g. https://<ref>.supabase.co
 *   VITE_SUPABASE_ANON_KEY — the anon/public key (NOT the service-role key)
 *
 * These are inlined at build time by Vite (import.meta.env).
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder-anon-key';

// Note: If these are placeholders, auth calls will fail gracefully at runtime
// (returning errors from Supabase) rather than crashing the app on load.
// This lets the Login page and health-check still render before Supabase is configured.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
