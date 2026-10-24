"""Authenticated isolation + webhook lifecycle tests against an in-memory Mongo (mongomock-motor).
Real app code and routes; Dodo's API is faked, so this is NOT a real Dodo test cycle."""
import asyncio, base64, hashlib, hmac, json, os, sys, time
import pytest

pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("MONGO_URL", "mongodb://localhost")
os.environ.setdefault("DB_NAME", "t")
from mongomock_motor import AsyncMongoMockClient
import motor.motor_asyncio as mm
mm.AsyncIOMotorClient = AsyncMongoMockClient
from fastapi.testclient import TestClient
import server, payments, auth

KEY = base64.b64encode(b"unit-test-secret-key-0123456789").decode()
IN = {"ctc": 1800000, "basic": 720000, "hra": 360000, "employerPF": 86400, "gratuity": 34632, "variablePay": 180000}


def sign(wid, ts, body):
    mac = hmac.new(base64.b64decode(KEY), f"{wid}.{ts}.".encode() + body, hashlib.sha256).digest()
    return {"webhook-id": wid, "webhook-timestamp": str(ts), "webhook-signature": "v1," + base64.b64encode(mac).decode()}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("DODO_PAYMENTS_API_KEY", "k")
    monkeypatch.setenv("DODO_PAYMENTS_WEBHOOK_KEY", "whsec_" + KEY)
    monkeypatch.setenv("DODO_PRODUCT_ID", "pdt_x")
    async def fake_checkout(user, rid, pid):
        return {"checkout_url": "https://example.invalid/pay", "session_id": "cks_1"}
    monkeypatch.setattr(payments, "create_checkout", fake_checkout)
    server.db = AsyncMongoMockClient()["t"]
    c = TestClient(server.app)
    loop = asyncio.new_event_loop()
    def mk(uid):
        loop.run_until_complete(server.db.users.insert_one({"_id": uid, "email": uid + "@x.com", "name": uid}))
        tok = loop.run_until_complete(auth.issue_session(server.db, uid))
        return {"Authorization": f"Bearer {tok}"}
    a, b = mk("ua"), mk("ub")
    ra = c.post("/api/reports", json={"input": IN, "country": "in"}, headers=a).json()["id"]
    ra2 = c.post("/api/reports", json={"input": {**IN, "ctc": 2000000}, "country": "in"}, headers=a).json()["id"]
    rb = c.post("/api/reports", json={"input": IN, "country": "in"}, headers=b).json()["id"]
    return c, a, b, ra, ra2, rb


def pay(c, hdr, rid, wid, etype="payment.succeeded", meta=True):
    r = c.post("/api/payments/checkout", json={"reportId": rid}, headers=hdr)
    assert r.status_code == 200
    pid = asyncio.new_event_loop().run_until_complete(server.db.purchases.find_one({"reportId": rid}))["_id"]
    body = json.dumps({"type": etype, "data": {"payment_id": "pay_1", "metadata": {"purchase_id": pid} if meta else {}}}).encode()
    return c.post("/api/payments/webhook", content=body, headers=sign(wid, int(time.time()), body))


def neg(c, hdr, rid):
    return c.post("/api/pack/negotiation", json={"reportId": rid}, headers=hdr).status_code


def test_unpaid_is_402_and_unauth_401(env):
    c, a, b, ra, ra2, rb = env
    assert neg(c, a, ra) == 402
    assert c.post("/api/pack/negotiation", json={"reportId": ra}).status_code == 401


def test_paid_unlocks_only_that_report_for_that_user(env):
    c, a, b, ra, ra2, rb = env
    assert pay(c, a, ra, "w1").status_code == 200
    assert neg(c, a, ra) == 200
    assert neg(c, a, ra2) == 402          # other report of same user stays locked
    assert neg(c, b, ra) == 404           # other user cannot read it
    assert neg(c, b, rb) == 402
    assert c.get(f"/api/payments/status/{ra}", headers=b).json()["paid"] is False
    assert c.get(f"/api/payments/status/{ra}", headers=a).json()["paid"] is True


def test_cannot_checkout_someone_elses_report(env):
    c, a, b, ra, ra2, rb = env
    assert c.post("/api/payments/checkout", json={"reportId": rb}, headers=a).status_code == 404


def test_compare_needs_ownership_of_both(env):
    c, a, b, ra, ra2, rb = env
    pay(c, a, ra, "w1")
    assert c.post("/api/pack/compare", json={"reportIdA": ra, "reportIdB": rb}, headers=a).status_code == 404
    assert c.post("/api/pack/compare", json={"reportIdA": ra, "reportIdB": ra2}, headers=a).status_code == 200


def test_failed_then_replay_and_bad_signature(env):
    c, a, b, ra, ra2, rb = env
    assert pay(c, a, ra, "wf", "payment.failed").status_code == 200
    assert neg(c, a, ra) == 402
    body = b'{"type":"payment.succeeded","data":{"metadata":{"purchase_id":"x"}}}'
    h = sign("wbad", int(time.time()), body); h["webhook-signature"] = "v1,AAAA"
    assert c.post("/api/payments/webhook", content=body, headers=h).status_code == 401
    old = sign("wold", int(time.time()) - 3600, body)
    assert c.post("/api/payments/webhook", content=body, headers=old).status_code == 401


def test_replay_and_no_metadata_do_not_unlock_or_downgrade(env):
    c, a, b, ra, ra2, rb = env
    assert pay(c, a, ra2, "wn", meta=False).status_code == 200
    assert neg(c, a, ra2) == 402
    assert pay(c, a, ra, "w1").status_code == 200
    pid = asyncio.new_event_loop().run_until_complete(server.db.purchases.find_one({"reportId": ra}))["_id"]
    body = json.dumps({"type": "payment.failed", "data": {"metadata": {"purchase_id": pid}}}).encode()
    assert c.post("/api/payments/webhook", content=body, headers=sign("w2", int(time.time()), body)).status_code == 200
    assert neg(c, a, ra) == 200           # a later failed event does not revoke a paid purchase
