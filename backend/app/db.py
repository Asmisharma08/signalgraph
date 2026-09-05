"""
SignalGraph — Supabase Client
==============================
Creates a single Supabase client instance using the service-role key.
This client has full database access and is used by all backend modules.
It is NEVER exposed to the frontend; the frontend uses its own anon-key client.

Usage:
    from app.db import supabase
    result = supabase.table("instruments").select("*").execute()
"""

from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Create the client once at import time.
# If credentials are not yet configured (e.g. before Supabase project exists),
# we still create the module so imports don't break — actual DB calls will fail
# with a clear error at runtime.
supabase: Client = create_client(
    SUPABASE_URL or "https://placeholder.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
)
