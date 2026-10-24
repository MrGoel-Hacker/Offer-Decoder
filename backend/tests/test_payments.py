"""Unit tests for payments.py: off-by-default gating and Standard Webhooks signature checks."""
import base64
import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import payments  # noqa: E402

KEY = base64.b64encode(b"unit-test-secret-key-0123456789").decode()
SECRET = "whsec_" + KEY


def _sign(wid, ts, body):
    mac = hmac.new(base64.b64decode(KEY), f"{wid}.{ts}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(mac).decode()


def test_disabled_by_default(monkeypatch):
    for k in ("PAYMENTS_ENABLED", "DODO_PAYMENTS_API_KEY", "DODO_PAYMENTS_WEBHOOK_KEY", "DODO_PRODUCT_ID"):
        monkeypatch.delenv(k, raising=False)
    assert payments.is_enabled() is False


def test_needs_flag_and_all_vars(monkeypatch):
    monkeypatch.setenv("DODO_PAYMENTS_API_KEY", "k")
    monkeypatch.setenv("DODO_PAYMENTS_WEBHOOK_KEY", SECRET)
    monkeypatch.setenv("DODO_PRODUCT_ID", "pdt_x")
    monkeypatch.delenv("PAYMENTS_ENABLED", raising=False)
    assert payments.is_enabled() is False
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    assert payments.is_enabled() is True


def test_valid_signature():
    body = b'{"type":"payment.succeeded"}'
    h = {"webhook-id": "msg_1", "webhook-timestamp": "1000", "webhook-signature": _sign("msg_1", "1000", body)}
    assert payments.verify_webhook(SECRET, h, body, now=1000) is True


def test_rejects_tampered_body_old_timestamp_and_missing_headers():
    body = b'{"type":"payment.succeeded"}'
    h = {"webhook-id": "msg_1", "webhook-timestamp": "1000", "webhook-signature": _sign("msg_1", "1000", body)}
    assert payments.verify_webhook(SECRET, h, body + b" ", now=1000) is False
    assert payments.verify_webhook(SECRET, h, body, now=1000 + 10_000) is False
    assert payments.verify_webhook(SECRET, {}, body, now=1000) is False
    assert payments.verify_webhook("", h, body, now=1000) is False
