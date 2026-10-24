"""Dodo Payments plumbing. OFF by default: nothing here is reachable until PAYMENTS_ENABLED=true
and the Dodo env vars are set. No product, price or paywall is defined in code - the product id
comes from DODO_PRODUCT_ID, and no existing feature checks for a purchase.

Env vars (secrets only via the host's secret store, never committed):
  PAYMENTS_ENABLED          "true" to turn the endpoints on (default off)
  DODO_PAYMENTS_ENV         "test" (default) or "live"
  DODO_PAYMENTS_API_KEY     Dodo API key
  DODO_PAYMENTS_WEBHOOK_KEY Dodo webhook signing secret (whsec_...)
  DODO_PRODUCT_ID           id of the one-time product created in the Dodo dashboard
  APP_PUBLIC_URL            site origin used for the return URL
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

API_BASES = {"test": "https://test.dodopayments.com", "live": "https://live.dodopayments.com"}
WEBHOOK_TOLERANCE_SECONDS = 300


def settings() -> dict:
    env = os.environ.get("DODO_PAYMENTS_ENV", "test").strip().lower()
    return {
        "flag": os.environ.get("PAYMENTS_ENABLED", "").strip().lower() == "true",
        "env": env if env in API_BASES else "test",
        "api_key": os.environ.get("DODO_PAYMENTS_API_KEY", ""),
        "webhook_key": os.environ.get("DODO_PAYMENTS_WEBHOOK_KEY", ""),
        "product_id": os.environ.get("DODO_PRODUCT_ID", ""),
        "public_url": os.environ.get("APP_PUBLIC_URL", "https://offerdecoder.online").rstrip("/"),
    }


def is_enabled() -> bool:
    s = settings()
    return bool(s["flag"] and s["api_key"] and s["webhook_key"] and s["product_id"])


def verify_webhook(secret: str, headers, body: bytes, now: float = None) -> bool:
    """Standard Webhooks signature check (webhook-id, webhook-timestamp, webhook-signature)."""
    wid = headers.get("webhook-id", "")
    ts = headers.get("webhook-timestamp", "")
    sigs = headers.get("webhook-signature", "")
    if not (secret and wid and ts and sigs):
        return False
    try:
        if abs((now if now is not None else time.time()) - int(ts)) > WEBHOOK_TOLERANCE_SECONDS:
            return False
        raw = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
        key = base64.b64decode(raw)
    except Exception:
        return False
    signed = f"{wid}.{ts}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for part in sigs.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


async def create_checkout(user: dict, report_id: str, purchase_id: str) -> dict:
    s = settings()
    payload = {
        "product_cart": [{"product_id": s["product_id"], "quantity": 1}],
        "customer": {"email": user.get("email", ""), "name": user.get("name", "")},
        "return_url": f"{s['public_url']}/pack/{report_id}?from=checkout",
        "metadata": {"purchase_id": purchase_id, "report_id": report_id},
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"{API_BASES[s['env']]}/checkouts",
                json=payload,
                headers={"Authorization": f"Bearer {s['api_key']}"},
            )
    except httpx.HTTPError:
        raise HTTPException(502, "Payment provider is unreachable. Please try again.")
    if r.status_code >= 400:
        raise HTTPException(502, "Could not start checkout. Please try again.")
    data = r.json()
    if not data.get("checkout_url"):
        raise HTTPException(502, "Could not start checkout. Please try again.")
    return data


async def start_checkout(db, user: dict, report_id: str) -> dict:
    if not is_enabled():
        raise HTTPException(503, "Payments are not available yet.")
    report = await db.reports.find_one({"_id": report_id, "ownerUserId": user["_id"]})
    if not report:
        raise HTTPException(404, "Report not found.")
    purchase_id = secrets.token_urlsafe(18)
    session = await create_checkout(user, report_id, purchase_id)
    await db.purchases.insert_one({
        "_id": purchase_id, "userId": user["_id"], "reportId": report_id,
        "sessionId": session.get("session_id"), "status": "pending",
        "createdAt": datetime.now(timezone.utc),
    })
    return {"checkoutUrl": session["checkout_url"]}


async def handle_webhook(db, headers, body: bytes) -> dict:
    s = settings()
    if not is_enabled():
        raise HTTPException(503, "Payments are not available yet.")
    if not verify_webhook(s["webhook_key"], headers, body):
        raise HTTPException(401, "Invalid signature.")
    wid = headers.get("webhook-id", "")
    try:
        event = json.loads(body)
    except ValueError:
        raise HTTPException(400, "Bad payload.")
    if await db.webhook_events.find_one({"_id": wid}):
        return {"received": True}
    etype = event.get("type", "")
    data = event.get("data") or {}
    purchase_id = (data.get("metadata") or {}).get("purchase_id")
    if purchase_id and etype in ("payment.succeeded", "payment.failed", "payment.cancelled"):
        status = "paid" if etype == "payment.succeeded" else "failed"
        update = {"status": status, "paymentId": data.get("payment_id"), "updatedAt": datetime.now(timezone.utc)}
        await db.purchases.update_one({"_id": purchase_id, "status": {"$ne": "paid"}}, {"$set": update})
    await db.webhook_events.insert_one({"_id": wid, "type": etype, "createdAt": datetime.now(timezone.utc)})
    return {"received": True}


async def has_paid(db, user_id: str, report_id: str) -> bool:
    """True when this user has a confirmed (webhook-verified) purchase for this report."""
    return bool(await db.purchases.find_one({"userId": user_id, "reportId": report_id, "status": "paid"}))
