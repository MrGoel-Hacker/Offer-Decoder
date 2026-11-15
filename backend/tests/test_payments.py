"""Offline checkout tests: no Dodo credentials or real charges required."""
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

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
        self.docs[query["_id"]].update(update["$set"])

    async def find_one(self, query):
        return deepcopy(self.docs.get(query["_id"]))


class CheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "DODO_PAYMENTS_ENABLED": "true", "APP_PUBLIC_URL": "https://offerdecoder.online",
            "DODO_PRODUCT_IN": "pdt_india", "DODO_PRODUCT_US": "pdt_usa",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.orders = Orders()
        self.allowed = True
        self.country = "IN"
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
                return NS(price=NS(type="one_time_price", currency=p["currency"], price=p["amount"], discount=0), pricing_mode=None)

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
        app.include_router(payments.make_router(NS(payment_orders=self.orders), lambda req: {"ctc": req.input["ctc"]},
                                               lambda raw, country: {"ctc": raw.get("ctc")}, bump, lambda: "today", lambda req: "ip"))
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


if __name__ == "__main__":
    unittest.main()
