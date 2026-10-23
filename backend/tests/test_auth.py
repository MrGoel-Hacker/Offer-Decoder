"""Unit tests for auth.py: Google credential verification + session helpers (FakeDB, no Mongo needed)."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import auth  # noqa: E402


class FakeDB:
    def __init__(self):
        self._stores = {"sessions": {}, "users": {}}
        self.sessions = _Col(self._stores["sessions"])
        self.users = _Col(self._stores["users"])


class _Col:
    def __init__(self, store):
        self.store = store

    async def insert_one(self, doc):
        self.store[doc["_id"]] = dict(doc)

    async def find_one(self, q):
        return self.store.get(q["_id"])

    async def delete_one(self, q):
        self.store.pop(q["_id"], None)


class FakeRequest:
    def __init__(self, token=None):
        self.headers = {"authorization": f"Bearer {token}"} if token else {}


# --- credential verification

def test_verify_credential_success():
    info = {"sub": "g123", "email": "a@b.com", "name": "Asha", "picture": "https://p"}
    with patch.object(auth.google_id_token, "verify_oauth2_token", return_value=info):
        with patch.object(auth, "GOOGLE_CLIENT_ID", "cid"):
            p = auth.verify_credential("token")
    assert p == {"sub": "g123", "email": "a@b.com", "name": "Asha", "picture": "https://p"}


def test_verify_credential_bad_token():
    with patch.object(auth.google_id_token, "verify_oauth2_token", side_effect=ValueError("bad")):
        with patch.object(auth, "GOOGLE_CLIENT_ID", "cid"):
            with pytest.raises(HTTPException) as e:
                auth.verify_credential("junk")
    assert e.value.status_code == 401


def test_verify_credential_missing_sub():
    with patch.object(auth.google_id_token, "verify_oauth2_token", return_value={"email": "a@b.com"}):
        with patch.object(auth, "GOOGLE_CLIENT_ID", "cid"):
            with pytest.raises(HTTPException) as e:
                auth.verify_credential("token")
    assert e.value.status_code == 401


def test_verify_credential_not_configured():
    with patch.object(auth, "GOOGLE_CLIENT_ID", ""):
        with pytest.raises(HTTPException) as e:
            auth.verify_credential("token")
    assert e.value.status_code == 503


# --- sessions

def test_session_roundtrip_and_expiry():
    asyncio.run(_session_roundtrip_and_expiry())


async def _session_roundtrip_and_expiry():
    db = FakeDB()
    await db.users.insert_one({"_id": "g123", "email": "a@b.com", "name": "Asha"})
    token = await auth.issue_session(db, "g123")
    assert len(token) >= 32
    user = await auth.get_session_user(db, FakeRequest(token))
    assert user["email"] == "a@b.com"
    # expired session -> None
    db._stores["sessions"][token]["expiresAt"] = datetime.now(timezone.utc) - timedelta(days=1)
    assert await auth.get_session_user(db, FakeRequest(token)) is None


def test_session_rejects_unknown_and_missing_token():
    asyncio.run(_session_rejects_unknown_and_missing_token())


async def _session_rejects_unknown_and_missing_token():
    db = FakeDB()
    assert await auth.get_session_user(db, FakeRequest()) is None
    assert await auth.get_session_user(db, FakeRequest("nope")) is None
    with pytest.raises(HTTPException) as e:
        await auth.require_user(db, FakeRequest())
    assert e.value.status_code == 401
