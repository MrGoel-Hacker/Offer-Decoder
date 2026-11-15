"""Billing API tests: real SDK and signatures, fake Mongo, no payment requests."""
import asyncio
import base64
import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from types import SimpleNamespace

import httpx
import pytest
from dodopayments import AsyncDodoPayments
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from standardwebhooks import Webhook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "billing_test")
import billing  # noqa: E402
import server  # noqa: E402

SECRET = "whsec_" + base64.b64encode(b"test-secret-that-is-at-least-32-bytes").decode()
HEADERS = {"authorization": "Bearer token"}


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def setup(monkeypatch):
    db = AsyncMongoMockClient().billing
    run(db.users.insert_one({"_id": "user", "email": "test@example.com", "name": "Tester"}))
    run(db.sessions.insert_one({"_id": "token", "userId": "user",
                               "expiresAt": datetime(2099, 1, 1, tzinfo=timezone.utc)}))
    for k, v in {"DODO_PAYMENTS_API_KEY": "test-key", "DODO_PAYMENTS_WEBHOOK_KEY": SECRET,
                 "DODO_PAYMENTS_ENVIRONMENT": "test_mode", "APP_PUBLIC_URL": "https://example.com",
                 "DODO_PRODUCT_ID_US": "pdt_us", "DODO_PRODUCT_ID_IN": "pdt_in"}.items():
        monkeypatch.setenv(k, v)
    requests = []
    product_price = {"us": 500, "in": 12500}

    async def transport(request):
        requests.append(request)
        if request.url.path.startswith("/products/"):
            region = request.url.path.rsplit("_", 1)[-1]
            return httpx.Response(200, json={"is_recurring": False, "price": {
                "type": "one_time_price", "currency": "USD" if region == "us" else "INR",
                "price": product_price[region],
                "tax_inclusive": True,
            }})
        if request.url.path == "/checkouts":
            return httpx.Response(200, json={"session_id": "cks_test", "checkout_url": "https://test.checkout.dodopayments.com/session/test"})
        if request.url.path == "/checkouts/cks_test":
            return httpx.Response(200, json={"id": "cks_test", "payment_status": product_price.get("previous_status")})
        if request.url.path == "/payments/pay_test":
            order = await db.billing_orders.find_one({"userId": "user"})
            return httpx.Response(200, json={"metadata": {"order_id": order["_id"]}})
        raise AssertionError(f"Unexpected provider request: {request.method} {request.url}")

    monkeypatch.setattr(billing, "AsyncDodoPayments", lambda **opts: AsyncDodoPayments(
        **opts, http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
    ))
    monkeypatch.setattr(server, "db", db)
    app = FastAPI()
    app.include_router(server.api)
    app.include_router(billing.router(db))
    return db, TestClient(app), requests, product_price


def checkout(client, region="us"):
    return client.post("/api/billing/checkout", json={"region": region}, headers=HEADERS)


def event_for(db, **changes):
    order = run(db.billing_orders.find_one({"userId": "user"}))
    data = {"metadata": {"order_id": order["_id"]}, "payment_id": "pay_test", "status": "succeeded",
            "currency": order["currency"], "total_amount": order["amount"], "tax": 0,
            "billing": {"country": order["billingCountry"]},
            "product_cart": [{"product_id": order["productId"], "quantity": 1}]}
    data.update(changes)
    return {"type": "payment.succeeded", "data": data}


def deliver(client, event, timestamp=None):
    raw = json.dumps(event)
    ts = timestamp or int(time.time())
    signature = Webhook(SECRET).sign("msg_test", datetime.fromtimestamp(ts, timezone.utc), raw)
    return client.post("/api/billing/webhook", content=raw, headers={
        "content-type": "application/json", "webhook-id": "msg_test",
        "webhook-timestamp": str(ts), "webhook-signature": signature,
    })


@pytest.mark.parametrize("region,amount,currency", [("us", 500, "USD"), ("in", 12500, "INR")])
def test_regional_checkout_and_verified_credits(setup, region, amount, currency):
    db, client, requests, _ = setup
    assert checkout(client, region).status_code == 200
    order = run(db.billing_orders.find_one({"userId": "user"}))
    assert (order["amount"], order["currency"]) == (amount, currency)
    outgoing = json.loads(next(r.content for r in requests if r.method == "POST"))
    assert outgoing["product_cart"] == [{"product_id": f"pdt_{region}", "quantity": 1}]
    assert outgoing["feature_flags"]["allow_currency_selection"] is False
    assert outgoing["return_url"] == "https://example.com/billing?returned=1"
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 0
    assert deliver(client, event_for(db)).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 3


def test_checkout_requires_login_configuration_and_valid_region(setup, monkeypatch):
    _, client, requests, _ = setup
    assert client.post("/api/billing/checkout", json={"region": "us"}).status_code == 401
    assert checkout(client, "xx").status_code == 422
    monkeypatch.delenv("DODO_PRODUCT_ID_US")
    assert checkout(client).status_code == 503
    assert requests == []


def test_wrong_dashboard_price_prevents_charge(setup):
    _, client, requests, prices = setup
    prices["us"] = 2000
    assert checkout(client).status_code == 503
    assert not any(r.method == "POST" for r in requests)


def test_checkout_retries_reuse_session_and_offer_cannot_be_bought_twice(setup):
    db, client, requests, _ = setup
    assert checkout(client).status_code == 200
    assert checkout(client).status_code == 200
    assert sum(r.method == "POST" for r in requests) == 1
    assert checkout(client, "in").status_code == 409
    assert deliver(client, event_for(db)).status_code == 200
    assert checkout(client).status_code == 409


def test_duplicate_webhooks_grant_only_three_credits(setup):
    db, client, _, _ = setup
    checkout(client)
    for _ in range(3):
        assert deliver(client, event_for(db)).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 3


def test_expired_unpaid_checkout_can_be_refreshed(setup):
    db, client, requests, _ = setup
    assert checkout(client).status_code == 200
    run(db.billing_orders.update_one({"userId": "user"}, {"$set": {
        "checkoutCreatedAt": datetime.now(timezone.utc) - timedelta(hours=25),
    }}))
    assert checkout(client).status_code == 200
    posts = [r for r in requests if r.method == "POST"]
    assert len(posts) == 2
    assert posts[0].headers["Idempotency-Key"] != posts[1].headers["Idempotency-Key"]


def test_expired_checkout_with_processing_payment_cannot_be_replaced(setup):
    db, client, requests, prices = setup
    assert checkout(client).status_code == 200
    run(db.billing_orders.update_one({"userId": "user"}, {"$set": {
        "checkoutCreatedAt": datetime.now(timezone.utc) - timedelta(hours=25),
    }}))
    prices["previous_status"] = "processing"
    assert checkout(client).status_code == 409
    assert sum(r.method == "POST" for r in requests) == 1


def test_checkout_creation_lock_prevents_competing_sessions(setup):
    db, client, requests, _ = setup
    assert checkout(client).status_code == 200
    run(db.billing_orders.update_one({"userId": "user"}, {
        "$unset": {"checkoutUrl": ""},
        "$set": {"checkoutLockUntil": datetime.now(timezone.utc) + timedelta(minutes=1)},
    }))
    assert checkout(client).status_code == 409
    assert sum(r.method == "POST" for r in requests) == 1


def test_unsigned_tampered_and_stale_webhooks_do_not_grant(setup):
    db, client, _, _ = setup
    checkout(client)
    assert client.post("/api/billing/webhook", json=event_for(db)).status_code == 400
    assert deliver(client, event_for(db), int(time.time()) - 1000).status_code == 400
    raw = json.dumps(event_for(db))
    ts = int(time.time())
    sig = Webhook(SECRET).sign("msg_test", datetime.fromtimestamp(ts, timezone.utc), raw)
    assert client.post("/api/billing/webhook", content=raw + " ", headers={
        "webhook-id": "msg_test", "webhook-timestamp": str(ts), "webhook-signature": sig,
    }).status_code == 400
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 0


@pytest.mark.parametrize("change", [
    {"total_amount": 1}, {"currency": "INR"}, {"product_cart": []},
    {"status": "failed"}, {"billing": {"country": "IN"}},
    {"product_cart": [{"product_id": "wrong", "quantity": 1}]},
    {"product_cart": [{"product_id": "pdt_us", "quantity": 2}]},
    {"metadata": {"order_id": "unknown"}},
])
def test_wrong_payment_does_not_grant(setup, change):
    db, client, _, _ = setup
    checkout(client)
    assert deliver(client, event_for(db, **change)).status_code == 400
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 0


def test_payment_with_included_tax_grants_credits(setup):
    db, client, _, _ = setup
    checkout(client)
    assert deliver(client, event_for(db, total_amount=500, tax=50)).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 3


@pytest.mark.parametrize("refund_first", [False, True])
def test_refund_revokes_unused_credits_and_success_replay_cannot_restore(setup, refund_first):
    db, client, _, _ = setup
    checkout(client)
    if not refund_first:
        assert deliver(client, event_for(db)).status_code == 200
    refund = {"type": "refund.succeeded", "data": {"payment_id": "pay_test"}}
    assert deliver(client, refund).status_code == 200
    assert deliver(client, event_for(db)).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json() == {
        "credits": 0, "purchased": True, "refunded": True,
    }


def report_body():
    return {"input": {"ctc": 1200000}, "country": "in", "requestId": str(uuid4())}


def test_three_saved_reports_idempotent_retry_and_no_fourth(setup):
    db, client, _, _ = setup
    checkout(client)
    deliver(client, event_for(db))
    body = report_body()
    response = client.post("/api/reports", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert client.post("/api/reports", json=body, headers=HEADERS).json() == response.json()
    for _ in range(2):
        assert client.post("/api/reports", json=report_body(), headers=HEADERS).status_code == 200
    assert client.post("/api/reports", json=report_body(), headers=HEADERS).status_code == 402
    rid = response.json()["id"]
    assert client.get(f"/api/reports/{rid}", headers=HEADERS).status_code == 200
    assert client.post(f"/api/reports/{rid}/share", headers=HEADERS).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 0
    assert client.delete(f"/api/my/reports/{rid}", headers=HEADERS).status_code == 200
    assert client.post("/api/reports", json=body, headers=HEADERS).status_code == 410


def test_save_without_credits_and_changed_idempotency_payload(setup):
    db, client, _, _ = setup
    body = report_body()
    assert client.post("/api/reports", json=body, headers=HEADERS).status_code == 402
    checkout(client)
    deliver(client, event_for(db))
    assert client.post("/api/reports", json=body, headers=HEADERS).status_code == 200
    changed = copy.deepcopy(body)
    changed["input"]["ctc"] = 1500000
    assert client.post("/api/reports", json=changed, headers=HEADERS).status_code == 409
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 2


def test_retry_after_report_insert_failure_does_not_charge_twice(setup, monkeypatch):
    db, client, _, _ = setup
    checkout(client)
    deliver(client, event_for(db))
    body = report_body()
    async def fail(*args, **kwargs):
        raise RuntimeError("Simulated database interruption")

    monkeypatch.setattr(server, "db", SimpleNamespace(
        users=db.users, sessions=db.sessions, reports=SimpleNamespace(update_one=fail),
    ))
    with pytest.raises(RuntimeError):
        client.post("/api/reports", json=body, headers=HEADERS)
    monkeypatch.setattr(server, "db", db)
    assert client.post("/api/reports", json=body, headers=HEADERS).status_code == 200
    assert client.get("/api/billing/status", headers=HEADERS).json()["credits"] == 2


def test_atomic_reservations_do_not_overspend(setup):
    db, _, _, _ = setup

    async def scenario():
        await db.users.update_one({"_id": "user"}, {"$set": {"reportCredits": 3}})
        results = await asyncio.gather(*[
            billing.reserve_report(db, "user", str(uuid4()), {"input": {"ctc": 1200000}})
            for _ in range(10)
        ], return_exceptions=True)
        assert sum(isinstance(r, tuple) for r in results) == 3
        assert (await db.users.find_one({"_id": "user"}))["reportCredits"] == 0

    run(scenario())
