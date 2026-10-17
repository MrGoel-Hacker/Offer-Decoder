"""Offer Decode API regression tests: decode math, quickscan, AI extract (no key), shareable reports + rate limit."""
import io
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

SAMPLE = """Dear Candidate,
We are pleased to offer you the role of Software Engineer at Acme Pvt Ltd.
Your total CTC will be Rs 18,00,000 per annum.
Basic salary: Rs 7,20,000 per annum
HRA: Rs 3,60,000 per annum
Variable pay: Rs 1,80,000 subject to performance rating
Joining bonus: Rs 1,00,000 (to be repaid if you leave within 12 months)
You will be under a 2-year service bond. Notice period 90 days.
"""


def ip():
    return f"10.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def minimal_pdf(text):
    # build a tiny valid PDF with a text layer
    content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    x = out.tell()
    out.write(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for o in offs:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode())
    return out.getvalue()


# --- health
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_limits_not_configured():
    r = requests.get(f"{API}/limits")
    assert r.status_code == 200
    assert r.json()["aiConfigured"] is False


# --- decode math
def test_decode_ctc_only():
    r = requests.post(f"{API}/decode", json={"input": {"ctc": 1800000}})
    assert r.status_code == 200
    d = r.json()
    assert d["monthlyFixed"] == 122045
    assert d["taxFixed"]["totalTax"] == 125625
    assert len(d["assumptions"]) == 3
    for f in d["flags"]:
        assert f["why"] and f["ask"]


def test_decode_notes_clause_flags():
    r = requests.post(f"{API}/decode", json={"input": {"ctc": 1800000}, "notes": "2-year bond of Rs 2 lakh, notice period 90 days"})
    d = r.json()
    texts = [f["text"] for f in d["flags"]]
    assert any("bond" in t.lower() for t in texts), texts
    assert any("Notice period of 90 days" in t for t in texts), texts
    clause = [f for f in d["flags"] if f["source"] == "clause"]
    assert len(clause) >= 2
    for f in d["flags"]:
        assert isinstance(f["why"], str) and len(f["why"]) > 10
        assert isinstance(f["ask"], str) and len(f["ask"]) > 10


def test_decode_empty_and_garbage():
    r = requests.post(f"{API}/decode", json={"input": {"ctc": "abc"}})
    assert r.status_code == 200
    assert r.json()["monthlyFixed"] <= 0 or isinstance(r.json()["monthlyFixed"], int)
    r = requests.post(f"{API}/decode", json={})
    assert r.status_code == 422


# --- quickscan
def test_quickscan_sample():
    r = requests.post(f"{API}/quickscan", json={"text": SAMPLE})
    assert r.status_code == 200
    d = r.json()
    assert d["fields"]["ctc"] == 1800000
    assert d["fields"]["basic"] == 720000
    assert d["fields"]["hra"] == 360000
    assert d["fields"].get("variablePay") == 180000
    assert d["fields"].get("joiningBonus") == 100000
    assert any("bond" in f.lower() for f in d["flags"])
    assert any("Notice period" in f for f in d["flags"])


def test_quickscan_empty():
    r = requests.post(f"{API}/quickscan", json={"text": ""})
    assert r.status_code == 200
    assert r.json()["fields"] == {}


# --- AI extraction without key
def test_extract_text_no_key():
    r = requests.post(f"{API}/extract/text", json={"text": SAMPLE}, headers={"x-forwarded-for": ip()})
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is False and "Quick scan" in d["message"]


def test_extract_text_too_short():
    r = requests.post(f"{API}/extract/text", json={"text": "short"})
    assert r.status_code == 400 and "detail" in r.json()


def test_extract_pdf_text_layer():
    pdf = minimal_pdf("CTC Rs 18,00,000 per annum. Basic Rs 7,20,000 per annum. Notice period 90 days.")
    r = requests.post(f"{API}/extract/pdf", files={"file": ("offer.pdf", pdf, "application/pdf")}, headers={"x-forwarded-for": ip()})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is False and d["message"]
    assert "18,00,000" in d["text"]
    assert not d.get("scanned")


def test_extract_pdf_scanned():
    pdf = minimal_pdf("")
    r = requests.post(f"{API}/extract/pdf", files={"file": ("s.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is False and d["scanned"] is True


def test_extract_pdf_invalid():
    r = requests.post(f"{API}/extract/pdf", files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
    assert r.status_code == 400 and "detail" in r.json()


def test_extract_images_no_key():
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
    files = [("files", ("a.png", png, "image/png")), ("files", ("b.jpg", png, "image/jpeg")), ("files", ("c.webp", png, "image/webp"))]
    r = requests.post(f"{API}/extract/images", files=files, headers={"x-forwarded-for": ip()})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is False and r.json()["message"]


def test_extract_images_bad_type():
    r = requests.post(f"{API}/extract/images", files=[("files", ("a.gif", b"GIF89a", "image/gif"))])
    assert r.status_code == 400 and "JPG" in r.json()["detail"]


def test_extract_images_too_many():
    files = [("files", (f"{i}.png", b"x", "image/png")) for i in range(5)]
    r = requests.post(f"{API}/extract/images", files=files)
    assert r.status_code == 400


# --- reports
def test_report_create_get_and_404():
    h = {"x-forwarded-for": ip()}
    r = requests.post(f"{API}/reports", json={"input": {"ctc": 1800000}, "notes": "bond", "company": "TEST_Acme", "role": "SDE"}, headers=h)
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert len(rid) >= 30 and r.json()["expiresAt"]
    g = requests.get(f"{API}/reports/{rid}")
    assert g.status_code == 200
    d = g.json()
    assert d["company"] == "TEST_Acme" and d["result"]["monthlyFixed"] == 122045
    assert "_id" not in d and d["id"] == rid
    assert requests.get(f"{API}/reports/doesnotexist123").status_code == 404


def test_report_missing_ctc():
    r = requests.post(f"{API}/reports", json={"input": {}}, headers={"x-forwarded-for": ip()})
    assert r.status_code == 400


def test_report_rate_limit():
    h = {"x-forwarded-for": ip()}
    codes = [requests.post(f"{API}/reports", json={"input": {"ctc": 1000000}, "company": "TEST_rl"}, headers=h).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10, codes
    assert codes[10] == 429
