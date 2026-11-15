"""One checkout buys one immutable report; redirects never prove payment."""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import Response
import auth
from report_pdf import render_report

PRICES = {
    "IN": {"currency": "INR", "original": 50000, "amount": 12500},
    "US": {"currency": "USD", "original": 2000, "amount": 500},
}


class PrivateReportAccessFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        return not any(path in message for path in ("/checkout/", "/payments/orders/", "/paid-report/", "/payments/reports/"))


def enabled():
    return os.environ.get("DODO_PAYMENTS_ENABLED", "false").lower() == "true"


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def payment_matches(payment, order):
    """Bind fulfillment to the exact server-created checkout and price."""
    return (
        payment.status == "succeeded"
        and payment.checkout_session_id == order["session_id"]
        and payment.currency == order["currency"]
        and payment.total_amount >= order["amount"]
        and payment.billing.country == order["country"]
        and not payment.refunds
        and not payment.disputes
        and not payment.subscription_ids
        and [(p.product_id, p.quantity) for p in (payment.product_cart or [])]
        == [(order["product_id"], 1)]
    )


def dodo_client():
    from dodopayments import AsyncDodoPayments

    key = os.environ.get("DODO_PAYMENTS_API_KEY", "").strip()
    mode = os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode")
    if not key or mode not in ("test_mode", "live_mode"):
        raise HTTPException(503, "Payments are not configured yet.")
    return AsyncDodoPayments(bearer_token=key, environment=mode, timeout=20, max_retries=0)


class CheckoutRequest(BaseModel):
    country: Literal["in", "us"] = "in"
    billingCountry: Literal["IN", "US"]
    input: dict[str, Any]
    clauseFlags: list[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=5000)
    company: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=120)
    source: str = Field(default="manual", max_length=20)


def make_router(db, decode_request, clean_input, bump, today, client_ip):
    router = APIRouter(prefix="/payments")

    async def verify(doc, request):
        if not doc or doc["expiresAt"].replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(404, "Report not found or expired.")
        if not doc.get("session_id"):
            return "pending"
        if not await bump(db, f"payment-check:{today()}:{client_ip(request)}", 600):
            raise HTTPException(429, "Too many payment checks. Please try again later.")
        async with dodo_client() as client:
            try:
                session = await client.checkout_sessions.retrieve(doc["session_id"])
                if not session.payment_id:
                    return "pending"
                payment = await client.payments.retrieve(session.payment_id)
            except Exception:
                raise HTTPException(502, "Payment verification is temporarily unavailable. Keep this page and retry.")
        if not payment_matches(payment, doc):
            return "review_required" if payment.status == "succeeded" else "failed" if payment.status in ("failed", "cancelled") else "pending"
        await db.payment_orders.update_one({"_id": doc["_id"]}, {"$set": {"payment_id": payment.payment_id, "verifiedAt": datetime.now(timezone.utc)}})
        return "paid"

    def report_data(doc, user=None):
        return {"status": "paid", "session": doc["payload"], "result": doc["result"],
                "reportId": doc.get("reportId"), "shared": bool(doc.get("shared")),
                "canShare": bool(user and doc.get("ownerUserId") == user["_id"]),
                "expiresAt": doc["expiresAt"].isoformat()}

    async def accessible_report(rid, request):
        doc = await db.payment_orders.find_one({"reportId": rid})
        if not doc:
            raise HTTPException(404, "Report not found or expired.")
        user = await auth.get_session_user(db, request)
        if not doc.get("shared") and (not user or user["_id"] != doc.get("ownerUserId")):
            raise HTTPException(404, "Report not found or expired.")
        if await verify(doc, request) != "paid":
            raise HTTPException(403, "This report does not have a verified payment.")
        return doc

    @router.get("/my-reports")
    async def my_reports(request: Request):
        user = await auth.require_user(db, request)
        cursor = db.payment_orders.find({"ownerUserId": user["_id"], "verifiedAt": {"$exists": True},
                                        "hidden": {"$ne": True}, "expiresAt": {"$gt": datetime.now(timezone.utc)}},
                                       {"payload.company": 1, "payload.role": 1, "createdAt": 1, "expiresAt": 1, "reportId": 1, "shared": 1}).sort("createdAt", -1).limit(100)
        return {"reports": [{"id": d["reportId"], "company": d["payload"].get("company", ""),
                             "role": d["payload"].get("role", ""), "createdAt": d["createdAt"].isoformat(),
                             "expiresAt": d["expiresAt"].isoformat(), "shared": bool(d.get("shared")), "paid": True}
                            async for d in cursor]}

    @router.get("/reports/{rid}")
    async def saved_report(rid: str, request: Request):
        return report_data(await accessible_report(rid, request), await auth.get_session_user(db, request))

    @router.get("/reports/{rid}/pdf")
    async def saved_pdf(rid: str, request: Request):
        doc = await accessible_report(rid, request)
        return Response(render_report(doc["payload"], doc["result"], doc["createdAt"]), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="OfferDecode-Report.pdf"'})

    @router.post("/reports/{rid}/share")
    async def share_report(rid: str, request: Request):
        user = await auth.require_user(db, request)
        doc = await db.payment_orders.find_one({"reportId": rid, "ownerUserId": user["_id"]})
        if not doc:
            raise HTTPException(404, "Report not found.")
        if await verify(doc, request) != "paid":
            raise HTTPException(403, "Payment must be verified before sharing.")
        await db.payment_orders.update_one({"_id": doc["_id"]}, {"$set": {"shared": True}})
        return {"id": rid, "shared": True}

    @router.delete("/reports/{rid}")
    async def hide_report(rid: str, request: Request):
        user = await auth.require_user(db, request)
        res = await db.payment_orders.update_one({"reportId": rid, "ownerUserId": user["_id"]}, {"$set": {"hidden": True}})
        if not res.matched_count:
            raise HTTPException(404, "Report not found.")
        return {"ok": True}

    @router.get("/config")
    async def config(country: Literal["in", "us"] | None = None):
        configured = all(os.environ.get(key, "").strip() for key in (
            "DODO_PAYMENTS_API_KEY", "DODO_PRODUCT_IN", "DODO_PRODUCT_US", "APP_PUBLIC_URL",
        ))
        # Region pages request only their price. Preserve the unscoped response
        # for older clients that may still be open during a deployment.
        prices = {country.upper(): PRICES[country.upper()]} if country else PRICES
        return {"enabled": enabled(), "configured": configured, "testMode": os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode") != "live_mode", "prices": prices}

    @router.post("/checkout")
    async def checkout(body: CheckoutRequest, request: Request):
        user = await auth.require_user(db, request)
        if not enabled():
            raise HTTPException(503, "Payments are not enabled yet.")
        if body.billingCountry != body.country.upper():
            raise HTTPException(400, "Your billing country must match the selected report region.")
        public_url = os.environ.get("APP_PUBLIC_URL", "").rstrip("/")
        product_id = os.environ.get(f"DODO_PRODUCT_{body.billingCountry}", "").strip()
        if not public_url.startswith("https://") or not product_id:
            raise HTTPException(503, "Payments are not configured yet.")
        if not await bump(db, f"checkout:{today()}:{client_ip(request)}", 20):
            raise HTTPException(429, "Too many checkout attempts today. Try again tomorrow.")
        # Validate and calculate before accepting any money. Store the exact result.
        payload = body.model_dump()
        payload["input"] = clean_input(body.input, body.country)
        salary_key = "baseSalary" if body.country == "us" else "ctc"
        if not payload["input"].get(salary_key):
            raise HTTPException(400, "Enter your salary before purchasing a report.")
        result = decode_request(CheckoutRequest(**payload))
        price = PRICES[body.billingCountry]
        token = secrets.token_urlsafe(32)
        order_id = token_hash(token)
        now = datetime.now(timezone.utc)
        async with dodo_client() as client:
            try:
                product = await client.products.retrieve(product_id)
                # Preserve the regular price and apply the launch discount in Dodo.
                p = product.price
                discount_bps = getattr(p, "discount_bps", None)
                if discount_bps is None:
                    discount_bps = (getattr(p, "discount", 0) or 0) * 100
                if (p.type != "one_time_price" or p.currency != price["currency"]
                        or p.price != price["original"] or discount_bps != 7500
                        or getattr(p, "pay_what_you_want", False)
                        or getattr(p, "purchasing_power_parity", False) or product.pricing_mode):
                    raise HTTPException(503, "Checkout pricing is being configured. Please try later.")
                await db.payment_orders.insert_one({
                    "_id": order_id, "country": body.billingCountry, **price,
                    "ownerUserId": user["_id"], "reportId": secrets.token_urlsafe(24), "shared": False,
                    "product_id": product_id, "payload": payload, "result": result,
                    "createdAt": now, "expiresAt": now + timedelta(days=90),
                })
                session = await client.checkout_sessions.create(
                    product_cart=[{"product_id": product_id, "quantity": 1}],
                    billing_address={"country": body.billingCountry},
                    billing_currency=price["currency"],
                    return_url=f"{public_url}/checkout/{token}",
                    metadata={"report_order": order_id},
                    feature_flags={"allow_discount_code": False, "allow_currency_selection": False, "allow_customer_editing_country": False},
                )
                await db.payment_orders.update_one({"_id": order_id}, {"$set": {"session_id": session.session_id}})
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502, "Couldn't start checkout. No report has been unlocked. Please try again.")
        return {"checkoutUrl": session.checkout_url, "reportToken": token}

    @router.get("/orders/{token}")
    async def order(token: str, request: Request):
        if len(token) > 100:
            raise HTTPException(404, "Report not found.")
        doc = await db.payment_orders.find_one({"_id": token_hash(token)})
        status = await verify(doc, request)
        if status != "paid":
            return {"status": status}
        return report_data(doc, await auth.get_session_user(db, request))

    @router.get("/orders/{token}/pdf")
    async def order_pdf(token: str, request: Request):
        if len(token) > 100:
            raise HTTPException(404, "Report not found.")
        doc = await db.payment_orders.find_one({"_id": token_hash(token)})
        if await verify(doc, request) != "paid":
            raise HTTPException(403, "Payment must be verified before downloading.")
        return Response(render_report(doc["payload"], doc["result"], doc["createdAt"]), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="OfferDecode-Report.pdf"'})

    return router
