# Unit tests for ai_extract model fallback chain (_call / extract) with mocked OpenRouter + throwaway Mongo db
import asyncio
import json
import os
import sys
import uuid

import httpx
import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ai_extract  # noqa: E402

ENV = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
MONGO_URL = ENV["MONGO_URL"]
TEST_DB = f"TEST_ai_fallback_{uuid.uuid4().hex[:8]}"

GOOD = {"ctc": 1800000, "basic": 720000, "company": "TEST_Co", "role": "SDE", "flags": ["bond"]}


def ok_body(content):
    return {"choices": [{"message": {"content": content}}]}


class Recorder:
    """Per-model scripted responses; each entry is a callable(request) -> httpx.Response or raises."""

    def __init__(self, script):
        self.script = {m: list(v) for m, v in script.items()}
        self.calls = []

    def handler(self, request):
        payload = json.loads(request.content)
        self.calls.append((payload["model"], "response_format" in payload))
        step = self.script[payload["model"]].pop(0)
        return step(request)


def resp(status, body=None, text=None):
    def f(request):
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=body if body is not None else {})
    return f


def raise_timeout(request):
    raise httpx.ReadTimeout("timeout", request=request)


@pytest.fixture
def run(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-test-key")
    real = httpx.AsyncClient

    def go(script, coro_fn):
        rec = Recorder(script)

        def fake_client(*a, **kw):
            kw.pop("transport", None)
            return real(*a, transport=httpx.MockTransport(rec.handler), **kw)

        monkeypatch.setattr(ai_extract.httpx, "AsyncClient", fake_client)

        async def main():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[TEST_DB]
            try:
                await db.usage.delete_many({})
                await db.ai_cache.delete_many({})
                return await coro_fn(db)
            finally:
                client.close()

        return asyncio.run(main()), rec

    yield go

    async def drop():
        c = AsyncIOMotorClient(MONGO_URL)
        await c.drop_database(TEST_DB)
        c.close()
    asyncio.run(drop())


IMG = ai_extract.IMAGE_MODELS
TXT = ai_extract.TEXT_MODELS


def call(models):
    return lambda db: ai_extract._call(db, models, [{"role": "user", "content": "x"}], None)


# --- fallthrough cases (image chain) ---
@pytest.mark.parametrize("first", [
    resp(429, {"error": {"message": "rate"}}),
    resp(503, {"error": "x"}),
    resp(404, {"error": "x"}),
    raise_timeout,
    resp(200, ok_body("sorry I cannot read this")),
    resp(200, text="<html>not json</html>"),
    resp(500),
], ids=["429", "503", "404", "timeout", "non_json_content", "non_json_body", "500"])
def test_image_first_fails_second_ok(run, first):
    (data, err), rec = run({IMG[0]: [first], IMG[1]: [resp(200, ok_body(json.dumps(GOOD)))]}, call(IMG))
    assert err is None
    assert data["model"] == IMG[1]
    assert data["fields"]["ctc"] == 1800000
    assert data["company"] == "TEST_Co"
    assert [c[0] for c in rec.calls] == [IMG[0], IMG[1]]


def test_all_429_limit_msg(run):
    (data, err), rec = run({m: [resp(429)] for m in IMG}, call(IMG))
    assert data is None and err == ai_extract.LIMIT_MSG
    assert len(rec.calls) == 2


def test_mix_429_500_unavailable(run):
    (data, err), _ = run({IMG[0]: [resp(429)], IMG[1]: [resp(500)]}, call(IMG))
    assert err == ai_extract.UNAVAILABLE_MSG


def test_mix_500_429_text_unavailable(run):
    (data, err), _ = run({TXT[0]: [resp(500)], TXT[1]: [resp(429)], TXT[2]: [resp(429)]}, call(TXT))
    assert err == ai_extract.UNAVAILABLE_MSG


def test_body_error_429_counts_rate_limited(run):
    (data, err), rec = run({m: [resp(200, {"error": {"code": 429, "message": "rl"}})] for m in IMG}, call(IMG))
    assert err == ai_extract.LIMIT_MSG
    assert len(rec.calls) == 2


def test_body_error_429_then_success(run):
    (data, err), _ = run({IMG[0]: [resp(200, {"error": {"code": 429}})], IMG[1]: [resp(200, ok_body(json.dumps(GOOD)))]}, call(IMG))
    assert err is None and data["model"] == IMG[1]


def test_body_error_500_mixed_unavailable(run):
    (data, err), _ = run({IMG[0]: [resp(200, {"error": {"code": 502}})], IMG[1]: [resp(429)]}, call(IMG))
    assert err == ai_extract.UNAVAILABLE_MSG


def test_400_retry_without_response_format_then_next(run):
    (data, err), rec = run({IMG[0]: [resp(400), resp(400)], IMG[1]: [resp(200, ok_body(json.dumps(GOOD)))]}, call(IMG))
    assert err is None and data["model"] == IMG[1]
    assert rec.calls == [(IMG[0], True), (IMG[0], False), (IMG[1], True)]


def test_400_retry_succeeds_same_model(run):
    (data, err), rec = run({IMG[0]: [resp(400), resp(200, ok_body("```json\n" + json.dumps(GOOD) + "\n```"))]}, call(IMG))
    assert err is None and data["model"] == IMG[0]
    assert rec.calls == [(IMG[0], True), (IMG[0], False)]


def test_text_chain_falls_through_all_three(run):
    (data, err), rec = run({TXT[0]: [resp(429)], TXT[1]: [raise_timeout], TXT[2]: [resp(200, ok_body(json.dumps(GOOD)))]}, call(TXT))
    assert err is None and data["model"] == TXT[2]
    assert [c[0] for c in rec.calls] == TXT


def test_text_all_429_limit(run):
    (data, err), rec = run({m: [resp(429)] for m in TXT}, call(TXT))
    assert err == ai_extract.LIMIT_MSG and len(rec.calls) == 3


# --- caps via extract() ---
def test_global_cap_no_http(run):
    async def fn(db):
        await db.usage.insert_one({"_id": f"global:{ai_extract.today()}", "count": ai_extract.AI_GLOBAL_PER_DAY})
        return await ai_extract.extract(db, "1.1.1.1", "k1", [], IMG, None)
    res, rec = run({m: [] for m in IMG}, fn)
    assert res == {"ok": False, "message": ai_extract.LIMIT_MSG}
    assert rec.calls == []


def test_global_cap_mid_chain(run):
    async def fn(db):
        await db.usage.insert_one({"_id": f"global:{ai_extract.today()}", "count": ai_extract.AI_GLOBAL_PER_DAY - 1})
        return await ai_extract.extract(db, "1.1.1.2", "k2", [], IMG, None)
    res, rec = run({IMG[0]: [resp(503)], IMG[1]: []}, fn)
    assert res["ok"] is False and res["message"] == ai_extract.LIMIT_MSG
    assert len(rec.calls) == 1


def test_per_ip_cap_sixth_call(run):
    async def fn(db):
        out = []
        for i in range(6):
            out.append(await ai_extract.extract(db, "9.9.9.9", f"ipk{i}", [], IMG, None))
        return out
    script = {IMG[0]: [resp(200, ok_body(json.dumps(GOOD)))] * 5, IMG[1]: []}
    res, rec = run(script, fn)
    assert all(r["ok"] for r in res[:5])
    assert res[5] == {"ok": False, "message": ai_extract.LIMIT_MSG}
    assert len(rec.calls) == 5


def test_extract_success_cached(run):
    async def fn(db):
        a = await ai_extract.extract(db, "2.2.2.2", "ck", [], IMG, None)
        b = await ai_extract.extract(db, "2.2.2.2", "ck", [], IMG, None)
        return a, b
    (a, b), rec = run({IMG[0]: [resp(429)], IMG[1]: [resp(200, ok_body(json.dumps(GOOD)))]}, fn)
    assert a["ok"] and a["cached"] is False and a["model"] == IMG[1]
    assert b["ok"] and b["cached"] is True
    assert len(rec.calls) == 2


def test_extract_failure_not_cached_unavailable(run):
    async def fn(db):
        r = await ai_extract.extract(db, "3.3.3.3", "fk", [], IMG, None)
        return r, await db.ai_cache.count_documents({})
    (r, n), _ = run({IMG[0]: [resp(500)], IMG[1]: [raise_timeout]}, fn)
    assert r == {"ok": False, "message": ai_extract.UNAVAILABLE_MSG} and n == 0


# --- light regression via public URL ---
BASE = os.environ.get("REACT_APP_BACKEND_URL", dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "")).rstrip("/")


def test_public_decode():
    r = requests.post(f"{BASE}/api/decode", json={"input": {"ctc": 1800000}}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["monthlyFixed"] == 122045


def test_public_quickscan():
    r = requests.post(f"{BASE}/api/quickscan", json={"text": "CTC: Rs 18,00,000 per annum. Basic 7,20,000. Notice period 90 days. Service bond of 2 years."}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fields"]["ctc"] == 1800000
    assert len(d["flags"]) >= 1
