"""
SignalGraph — Authentication Dependency
========================================
Provides a FastAPI dependency `get_current_user_id` that:
  1. Reads the Authorization header ("Bearer <token>").
  2. Verifies the JWT's signature — against SUPABASE_JWT_SECRET for an
     HS256 token (older Supabase projects' legacy shared secret), or
     against the project's public JWKS for an ES256/RS256 token (newer
     Supabase projects using asymmetric "JWT Signing Keys"). Which path
     runs is decided by the token's own (unverified) header, so this
     works against either kind of Supabase project without config.
  3. Extracts and returns the user's UUID (`sub` claim).
  4. Raises HTTP 401 with the standard error body on any failure.

Every protected route declares this as a dependency — the user ID
is NEVER taken from any client-supplied field in the request body.
"""

from fastapi import Depends, HTTPException, Request
import jwt  # PyJWT
from jwt import PyJWKClient
from app.config import SUPABASE_JWT_SECRET, SUPABASE_URL

# Caches the fetched JWKS for 5 minutes (PyJWKClient's default) so a
# newer Supabase project's ES256/RS256 tokens don't cost a network
# round-trip to Supabase on every single request.
_jwk_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json") if SUPABASE_URL else None


def get_current_user_id(request: Request) -> str:
    """
    FastAPI dependency.  Extracts and verifies the Supabase access token
    from the Authorization header and returns the authenticated user's UUID.

    Raises:
        HTTPException(401) if the token is missing, malformed, or invalid.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Missing or malformed Authorization header"}},
        )

    token = auth_header[len("Bearer "):]

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "HS256":
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            if _jwk_client is None:
                raise jwt.InvalidTokenError("SUPABASE_URL is not configured; cannot fetch JWKS")
            signing_key = _jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",  # Supabase sets this audience by default
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Token has expired"}},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": f"Invalid token: {exc}"}},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Token missing 'sub' claim"}},
        )

    return user_id
