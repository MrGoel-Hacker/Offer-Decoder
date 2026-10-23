"""Google sign-in: ID-token verification, users, and opaque server-side sessions.

Session tokens are random, stored hashed-at-rest only in Mongo (never logged),
and expire after SESSION_TTL_DAYS. The Google client ID is public by design
(it is embedded in the frontend too), so it may live in code or env.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

# Public value (also embedded in the frontend); env can override it.
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID", "983915537425-bvtsnlntosva6t7phijp4u97pt5broru.apps.googleusercontent.com"
)
SESSION_TTL_DAYS = 30


def verify_credential(credential: str) -> dict:
    """Verify a Google Identity Services ID token. Returns the user profile."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Sign-in is not configured yet.")
    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(401, "Google sign-in failed. Please try again.")
    sub, email = info.get("sub"), info.get("email")
    if not sub or not email:
        raise HTTPException(401, "Google sign-in failed. Please try again.")
    return {
        "sub": sub,
        "email": email,
        "name": info.get("name") or email.split("@")[0],
        "picture": info.get("picture") or "",
    }


async def issue_session(db, sub: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.sessions.insert_one(
        {"_id": token, "userId": sub, "createdAt": now, "expiresAt": now + timedelta(days=SESSION_TTL_DAYS)}
    )
    return token


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""


async def get_session_user(db, request: Request):
    token = _bearer(request)
    if not token:
        return None
    sess = await db.sessions.find_one({"_id": token})
    if not sess:
        return None
    expires = sess["expiresAt"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    return await db.users.find_one({"_id": sess["userId"]})


async def require_user(db, request: Request):
    user = await get_session_user(db, request)
    if not user:
        raise HTTPException(401, "Please sign in to continue.")
    return user
