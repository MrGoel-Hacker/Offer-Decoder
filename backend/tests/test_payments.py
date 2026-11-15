"""Offline checkout tests: no Dodo credentials or real charges required."""
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import payments


class Orders:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        self.docs[doc["_id"]] = deepcopy(doc)

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc:
            self.docs[doc["_id"]].update(update["$set"])
        return NS(matched_count=1 if doc else 0)

    async def find_one(self, query):
        return deepcopy(next((d for d in self.docs.values() if all(d.get(k) == v for k, v in query.items())), None))

    def find(self, query, projection):
        def matches(doc):
            for k, v in query.items():
                if isinstance(v, dict):
                    if "$exists" in v and (k in doc) != v["$exists"]: return False
                    if "$ne" in v and doc.get(k) == v["$ne"]: return False
                    if "$gt" in v and doc.get(k) <= v["$gt"]: return False
                elif doc.get(k) != v: return False
            return True
        class Cursor:
            def sort(self, *args): return self
            def limit(self, *args): return self
            def __aiter__(self):
                async def items():
                    for doc in self.docs: yield deepcopy(doc)
                return items()
        cursor = Cursor()
        cursor.docs = [d for d in self.docs.values() if matches(d)]
        return cursor


class CheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = {"_id": "buyer-1"}
        self.auth = patch.object(payments.auth, "require_user", AsyncMock(return_value=self.user))
        self.session_user = patch.object(payments.auth, "get_session_user", AsyncMock(return_value=self.user))
        self.auth.start(); self.session_user.start()
        self.addCleanup(self.auth.stop); self.addCleanup(self.session_user.stop)
        self.env = patch.dict(os.environ, {
            "DODO_PAYMENTS_ENABLED": "true", "APP_PUBLIC_URL": "https://offerdecoder.online",
            "DODO_PRODUCT_IN": "pdt_india", "DODO_PRODUCT_US": "pdt_usa",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.orders = Orders()
        self.allowed = True
        self.country = "IN"
        self.discount_bps = 7500
        self.payment = NS(status="succeeded", checkout_session_id="cks_123", currency="INR", total_amount=12500,
                          billing=NS(country="IN"), refunds=[], disputes=[], subscription_ids=[],
                          product_cart=[NS(product_id="pdt_india", quantity=1)], payment_id="pay_123")
        self.session = NS(payment_id="pay_123")
        owner = self

        class FakeDodo:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            @property
            def products(self):
                return NS(retrieve=self.product)

            async def product(self, product_id):
                country = "IN" if product_id == "pdt_india" else "US"
                p = payments.PRICES[country]
                return NS(price=NS(type="one_time_price", currency=p["currency"], price=p["original"], discount=75, discount_bps=owner.discount_bps), pricing_mode=None)

            @property
            def checkout_sessions(self):
                return NS(create=self.create, retrieve=self.retrieve)

            async def create(self, **kwargs):
                owner.checkout_args = kwargs
                return NS(session_id="cks_123", checkout_url="https://test.checkout.dodopayments.com/session/cks_123")

            async def retrieve(self, session_id):
                return owner.session

            @property
            def payments(self):
                return NS(retrieve=self.payment)

            async def payment(self, payment_id):
                return owner.payment

        mock = patch.object(payments, "dodo_client", FakeDodo)
        mock.start()
        self.addCleanup(mock.stop)

        async def bump(*args):
            return self.allowed

        app = FastAPI()
        app.include_router(payments.make_router(NS(payment_orders=self.orders),
                                               lambda req: {"baseSalary": req.input["baseSalary"], "country": req.country} if req.country == "us" else {"ctc": req.input["ctc"]},
                                               lambda raw, country: dict(raw), bump, lambda: "today", lambda req: "ip"))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def buy(self, country="IN"):
        return await self.client.post("/payments/checkout", json={"billingCountry": country, "country": "in", "input": {"ctc": 1800000}})

    async def test_checkout_preserves_one_offer_and_server_product(self):
        response = await self.buy()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.checkout_args["product_cart"], [{"product_id": "pdt_india", "quantity": 1}])
        self.assertFalse(self.checkout_args["feature_flags"]["allow_customer_editing_country"])
        token = response.json()["reportToken"]
        self.assertNotIn(token, self.orders.docs)
        self.assertEqual((await self.client.get(f"/payments/orders/{token}")).json()["result"], {"ctc": 1800000})

    async def test_us_price_and_product(self):
        response = await self.buy("US")
        self.assertEqual(response.status_code, 200)
        order = next(iter(self.orders.docs.values()))
        self.assertEqual((order["amount"], order["currency"]), (500, "USD"))
        self.assertEqual(self.checkout_args["product_cart"][0]["product_id"], "pdt_usa")

    async def test_missing_or_incorrect_launch_discount_blocks_checkout(self):
        for discount in (0, 5000, 10000):
            with self.subTest(discount=discount):
                self.discount_bps = discount
                self.assertEqual((await self.buy()).status_code, 503)
                self.assertFalse(self.orders.docs)

    async def test_us_report_preserves_us_salary_and_country(self):
        response = await self.client.post("/payments/checkout", json={
            "country": "us", "billingCountry": "US", "input": {"baseSalary": 120000, "state": "NY"},
        })
        self.assertEqual(response.status_code, 200)
        order = next(iter(self.orders.docs.values()))
        self.assertEqual(order["payload"]["country"], "us")
        self.assertEqual(order["payload"]["input"]["state"], "NY")
        self.assertEqual(order["result"], {"baseSalary": 120000, "country": "us"})

    async def test_redirect_status_cannot_unlock_pending_payment(self):
        token = (await self.buy()).json()["reportToken"]
        self.payment.status = "processing"
        data = (await self.client.get(f"/payments/orders/{token}?status=succeeded&payment_id=fake")).json()
        self.assertEqual(data, {"status": "pending"})

    async def test_mismatched_and_refunded_payments_do_not_unlock(self):
        token = (await self.buy()).json()["reportToken"]
        original = deepcopy(self.payment)
        for field, value in [("checkout_session_id", "another"), ("currency", "USD"), ("total_amount", 100),
                             ("refunds", ["refund"]), ("disputes", ["dispute"]), ("billing", NS(country="US")),
                             ("product_cart", [NS(product_id="another", quantity=1)]), ("subscription_ids", ["sub"] )]:
            with self.subTest(field=field):
                self.payment = deepcopy(original)
                setattr(self.payment, field, value)
                self.assertNotIn("result", (await self.client.get(f"/payments/orders/{token}")).json())

    async def test_invalid_country_rate_limit_and_disabled_checkout(self):
        self.assertEqual((await self.buy("GB")).status_code, 422)
        self.allowed = False
        self.assertEqual((await self.buy()).status_code, 429)
        os.environ["DODO_PAYMENTS_ENABLED"] = "false"
        self.assertEqual((await self.buy()).status_code, 503)

    async def test_unknown_and_expired_orders(self):
        self.assertEqual((await self.client.get("/payments/orders/unknown")).status_code, 404)
        token = (await self.buy()).json()["reportToken"]
        next(iter(self.orders.docs.values()))["expiresAt"] = payments.datetime(2000, 1, 1, tzinfo=payments.timezone.utc)
        self.assertEqual((await self.client.get(f"/payments/orders/{token}")).status_code, 404)

    async def test_report_endpoints_cannot_bypass_enabled_payments(self):
        with patch.dict(os.environ, {"MONGO_URL": "mongodb://127.0.0.1:27017", "DB_NAME": "offline_payment_test"}):
            import server
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as client:
            payload = {"country": "us", "input": {"baseSalary": 120000}}
            self.assertEqual((await client.post("/api/decode", json=payload)).status_code, 402)
            self.assertEqual((await client.post("/api/reports", json=payload)).status_code, 402)
            os.environ["DODO_PAYMENTS_ENABLED"] = "false"
            free = await client.post("/api/decode", json=payload)
            self.assertEqual(free.status_code, 200)
            self.assertEqual(free.json()["country"], "us")

    async def test_checkout_requires_login_and_attaches_owner(self):
        from fastapi import HTTPException
        with patch.object(payments.auth, "require_user", AsyncMock(side_effect=HTTPException(401, "Please sign in"))):
            self.assertEqual((await self.buy()).status_code, 401)
        await self.buy()
        doc = next(iter(self.orders.docs.values()))
        self.assertEqual(doc["ownerUserId"], "buyer-1")
        self.assertTrue(doc["reportId"])
        self.assertFalse(doc["shared"])

    async def test_pdf_and_share_require_verified_payment_and_audience(self):
        from decoder import decode
        token = (await self.buy()).json()["reportToken"]
        doc = next(iter(self.orders.docs.values()))
        doc["result"] = decode({"ctc": 1800000})
        rid = doc["reportId"]
        self.payment.status = "processing"
        self.assertEqual((await self.client.get(f"/payments/orders/{token}/pdf")).status_code, 403)
        self.assertEqual((await self.client.post(f"/payments/reports/{rid}/share")).status_code, 403)
        self.assertFalse(doc["shared"])
        self.payment.status = "succeeded"
        pdf = await self.client.get(f"/payments/orders/{token}/pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        from io import BytesIO
        from pypdf import PdfReader
        contents = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
        self.assertIn("Fixed in-hand per month", contents)
        self.assertIn("Negotiation tips", contents)
        self.assertIn("attachment", pdf.headers["content-disposition"])
        with patch.object(payments.auth, "get_session_user", AsyncMock(return_value={"_id": "other-buyer"})):
            self.assertEqual((await self.client.get(f"/payments/reports/{rid}")).status_code, 404)
            self.assertEqual((await self.client.get(f"/payments/reports/{rid}/pdf")).status_code, 404)
        with patch.object(payments.auth, "require_user", AsyncMock(return_value={"_id": "other-buyer"})):
            self.assertEqual((await self.client.post(f"/payments/reports/{rid}/share")).status_code, 404)
        self.assertEqual((await self.client.post(f"/payments/reports/{rid}/share")).status_code, 200)
        with patch.object(payments.auth, "get_session_user", AsyncMock(return_value=None)):
            public = await self.client.get(f"/payments/reports/{rid}")
            self.assertEqual(public.status_code, 200)
            self.assertFalse(public.json()["canShare"])
            self.assertEqual((await self.client.get(f"/payments/reports/{rid}/pdf")).status_code, 200)
            self.payment.refunds = ["refund"]
            self.assertEqual((await self.client.get(f"/payments/reports/{rid}/pdf")).status_code, 403)
            self.assertEqual((await self.client.get(f"/payments/reports/{rid}")).status_code, 403)

    async def test_extraction_requires_sign_in_before_using_ai(self):
        from fastapi import HTTPException
        with patch.dict(os.environ, {"MONGO_URL": "mongodb://127.0.0.1:27017", "DB_NAME": "offline_payment_test"}):
            import server
        with patch.object(payments.auth, "require_user", AsyncMock(side_effect=HTTPException(401, "Please sign in"))):
            async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as client:
                for path in ("/api/decode", "/api/quickscan", "/api/extract/text", "/api/extract/pdf", "/api/extract/images"):
                    self.assertEqual((await client.post(path, json={})).status_code, 401)

    async def test_paid_purchase_appears_only_in_owners_library(self):
        token = (await self.buy()).json()["reportToken"]
        self.assertEqual((await self.client.get("/payments/my-reports")).json()["reports"], [])
        await self.client.get(f"/payments/orders/{token}")
        items = (await self.client.get("/payments/my-reports")).json()["reports"]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["paid"])
        self.assertNotIn("result", items[0])
        with patch.object(payments.auth, "require_user", AsyncMock(return_value={"_id": "other-buyer"})):
            self.assertEqual((await self.client.get("/payments/my-reports")).json()["reports"], [])
        rid = items[0]["id"]
        self.assertEqual((await self.client.delete(f"/payments/reports/{rid}")).status_code, 200)
        self.assertEqual((await self.client.get("/payments/my-reports")).json()["reports"], [])
        await self.client.get(f"/payments/orders/{token}")
        self.assertEqual((await self.client.get("/payments/my-reports")).json()["reports"], [])


if __name__ == "__main__":
    unittest.main()
