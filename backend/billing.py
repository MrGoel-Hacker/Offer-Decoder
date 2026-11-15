"""First-pack checkout and atomic, retry-safe report credits.

The user's document is the credit ledger. A report reservation is written in the
same atomic update as its debit, so a failed report insert can be retried safely
without requiring MongoDB transactions (including on local standalone Mongo).
"""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse

from dodopayments import APIError, AsyncDodoPayments
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pymongo import ReturnDocument

import auth

PACKS = {
    "us": {"currency": "USD", "originalAmount": 2000, "amount": 500, "country": "US"},
    "in": {"currency": "INR", "originalAmount": 50000, "amount": 12500, "country": "IN"},
}


def settings(region=None):
    key = os.getenv("DODO_PAYMENTS_API_KEY", "").strip()
    secret = os.getenv("DODO_PAYMENTS_WEBHOOK_KEY", "").strip()
    mode = os.getenv("DODO_PAYMENTS_ENVIRONMENT", "test_mode")
    public = os.getenv("APP_PUBLIC_URL", "").rstrip("/")
    parsed = urlparse(public)
    if (not key or not secret or mode not in {"test_mode", "live_mode"}
            or parsed.scheme not in {"http", "https"} or not parsed.netloc
            or (mode == "live_mode" and parsed.scheme != "https")):
        raise HTTPException(503, "Payments are not configured yet.")
    product = os.getenv(f"DODO_PRODUCT_ID_{region.upper()}", "").strip() if region else None
    if region and not product:
        raise HTTPException(503, "Payments are not configured for this region yet.")
    return dict(bearer_token=key, webhook_key=secret, environment=mode), public, product


def configured(region):
    try:
        settings(region)
        return True
    except HTTPException:
        return False


class CheckoutIn(BaseModel):
    region: Literal["in", "us"]


async def fulfill(db, event):
    """Called only after signature verification; duplicate deliveries are harmless."""
    kind, data = event.get("type"), event.get("data", {})
    if kind == "refund.succeeded":
        # Any successful refund revokes unused credits. Existing reports remain.
        payment_id = data.get("payment_id")
        order_id = (data.get("metadata") or {}).get("order_id")
        order = await db.billing_orders.find_one({"_id": order_id}) if order_id else None
        if payment_id and order:
            await db.users.update_one(
                {"_id": order["userId"], "$or": [
                    {"introPackPaymentId": payment_id}, {"introPackPaymentId": {"$exists": False}},
                ]},
                {"$set": {"reportCredits": 0, "introPackRefunded": True,
                          "introPackPaymentId": payment_id, "introPackPurchased": True}},
            )
        return
    if kind != "payment.succeeded":
        return
    order_id = (data.get("metadata") or {}).get("order_id")
    order = await db.billing_orders.find_one({"_id": order_id}) if order_id else None
    if not order:
        raise HTTPException(400, "Unknown payment order.")
    cart = data.get("product_cart") or []
    if (data.get("status") != "succeeded" or not data.get("payment_id")
            or data.get("currency") != order["currency"]
            or data.get("total_amount") != order["amount"]
            or len(cart) != 1 or cart[0].get("product_id") != order["productId"]
            or cart[0].get("quantity") != 1
            or (data.get("billing") or {}).get("country") != order["billingCountry"]):
        raise HTTPException(400, "Payment does not match the report pack.")
    # The promotion may be purchased once, across both regions, per account.
    await db.users.update_one(
        {"_id": order["userId"], "introPackPaymentId": {"$exists": False}},
        {"$set": {"introPackPaymentId": data["payment_id"], "introPackPurchased": True},
         "$inc": {"reportCredits": 3}},
    )
    await db.billing_orders.update_one(
        {"_id": order_id}, {"$set": {"paymentId": data["payment_id"], "status": "paid"}},
    )


async def reserve_report(db, user_id, request_id, payload):
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    rid = hashlib.sha256(f"{user_id}:{request_id}".encode()).hexdigest()[:48]
    now = datetime.now(timezone.utc)
    reservation = {"id": rid, "fingerprint": fingerprint, "createdAt": now}
    updated = await db.users.find_one_and_update(
        {"_id": user_id, "reportCredits": {"$gt": 0}, "billingReports.id": {"$ne": rid}},
        {"$inc": {"reportCredits": -1}, "$push": {"billingReports": reservation}},
        return_document=ReturnDocument.AFTER,
    )
    ledger = updated or await db.users.find_one({"_id": user_id}) or {}
    existing = next((r for r in ledger.get("billingReports", []) if r["id"] == rid), None)
    if not existing:
        raise HTTPException(402, "Buy a report pack to save this report.")
    if existing["fingerprint"] != fingerprint:
        raise HTTPException(409, "This save request was already used for a different report.")
    created = existing["createdAt"].replace(tzinfo=timezone.utc)
    if rid in ledger.get("billingDeletedReports", []) or created + timedelta(days=90) <= now:
        raise HTTPException(410, "This saved report was deleted or expired. Start a new report.")
    return rid, created


def router(db):
    routes = APIRouter(prefix="/api/billing")

    @routes.get("/packs")
    async def packs():
        return {"packs": [{"region": r, **p, "reports": 3, "discountPercent": 75,
                           "available": configured(r)} for r, p in PACKS.items()]}

    @routes.get("/status")
    async def status(request: Request):
        user = await auth.require_user(db, request)
        return {"credits": user.get("reportCredits", 0),
                "purchased": bool(user.get("introPackPurchased")),
                "refunded": bool(user.get("introPackRefunded"))}

    @routes.post("/checkout")
    async def checkout(body: CheckoutIn, request: Request):
        user = await auth.require_user(db, request)
        if user.get("introPackPurchased"):
            raise HTTPException(409, "Your introductory report pack has already been purchased.")
        opts, public, product = settings(body.region)
        # One order per account prevents competing checkouts buying the offer twice.
        order_id = hashlib.sha256(f"intro:{user['_id']}".encode()).hexdigest()
        pack = PACKS[body.region]
        await db.billing_orders.update_one(
            {"_id": order_id}, {"$setOnInsert": {
                "userId": user["_id"], "region": body.region, "currency": pack["currency"],
                "amount": pack["amount"], "productId": product, "billingCountry": pack["country"],
                "status": "pending", "createdAt": datetime.now(timezone.utc),
            }}, upsert=True,
        )
        order = await db.billing_orders.find_one({"_id": order_id})
        if order["region"] != body.region:
            raise HTTPException(409, "A checkout already exists for your other region. Return to that region to continue.")
        now = datetime.now(timezone.utc)
        created = order.get("checkoutCreatedAt", order["createdAt"]).replace(tzinfo=timezone.utc)
        # Hosted sessions expire after 24h. Refresh only after that window,
        # and only when the previous session has no unsettled payment.
        if order.get("checkoutUrl") and created + timedelta(hours=24, minutes=1) > now:
            return {"checkoutUrl": order["checkoutUrl"]}
        lock = await db.billing_orders.find_one_and_update(
            {"_id": order_id, "sessionId": order.get("sessionId"), "$or": [
                {"checkoutLockUntil": {"$exists": False}}, {"checkoutLockUntil": {"$lt": now}},
            ]},
            {"$set": {"checkoutLockUntil": now + timedelta(minutes=2)}},
        )
        if not lock:
            raise HTTPException(409, "Checkout is being prepared. Please try again shortly.")
        try:
            async with AsyncDodoPayments(**opts, timeout=25.0, max_retries=0) as dodo:
                if order.get("sessionId"):
                    previous = await dodo.checkout_sessions.retrieve(order["sessionId"])
                    if previous.payment_status not in {None, "failed", "cancelled", "requires_payment_method"}:
                        raise HTTPException(409, "Your previous payment is awaiting confirmation. Check payment status shortly.")
                product_info = await dodo.products.retrieve(order["productId"])
                price = product_info.price
                if (product_info.is_recurring or price.type != "one_time_price"
                        or price.currency != order["currency"] or price.price != order["amount"]
                        or price.tax_inclusive is not True or price.pay_what_you_want
                        or price.purchasing_power_parity or price.discount or price.discount_bps):
                    raise HTTPException(503, "This report pack's checkout price is not configured correctly.")
                session = await dodo.checkout_sessions.create(
                    product_cart=[{"product_id": order["productId"], "quantity": 1}],
                    customer={"email": user["email"], "name": user.get("name", "")},
                    billing_address={"country": pack["country"]},
                    billing_currency=pack["currency"],
                    metadata={"order_id": order_id},
                    return_url=f"{public}/billing?returned=1",
                    cancel_url=f"{public}/billing?cancelled=1",
                    feature_flags={"allow_discount_code": False, "allow_currency_selection": False,
                                   "allow_customer_editing_country": False},
                    extra_headers={"Idempotency-Key": f"{order_id}-{order.get('checkoutGeneration', 0) + 1}"},
                )
            url = session.checkout_url
            if not url:
                raise HTTPException(502, "Checkout could not be created. Please try again.")
            await db.billing_orders.update_one(
                {"_id": order_id}, {"$set": {"checkoutUrl": url, "sessionId": session.session_id,
                                             "checkoutCreatedAt": now}, "$inc": {"checkoutGeneration": 1}},
            )
        except APIError:
            raise HTTPException(502, "Checkout is temporarily unavailable. Please try again.")
        finally:
            await db.billing_orders.update_one({"_id": order_id}, {"$unset": {"checkoutLockUntil": ""}})
        return {"checkoutUrl": url}

    @routes.post("/webhook")
    async def webhook(request: Request):
        opts, _, _ = settings()
        raw = await request.body()
        if len(raw) > 256 * 1024:
            raise HTTPException(413, "Webhook is too large.")
        try:
            async with AsyncDodoPayments(**opts) as dodo:
                dodo.webhooks.unwrap(raw.decode("utf-8"), headers=dict(request.headers))
                event = json.loads(raw)
                if event.get("type") == "refund.succeeded":
                    # Resolve the order from the provider, even if the refund
                    # arrives before payment.succeeded. Never regrant refunded credits.
                    payment = await dodo.payments.retrieve(event["data"]["payment_id"])
                    event["data"]["metadata"] = payment.metadata
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Invalid webhook.")
        except Exception as exc:
            from standardwebhooks.webhooks import WebhookVerificationError
            if isinstance(exc, WebhookVerificationError):
                raise HTTPException(400, "Invalid webhook signature.")
            raise
        await fulfill(db, event)
        return {"ok": True}

    return routes
