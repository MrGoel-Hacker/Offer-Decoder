"""Offline US Quick scan: no AI, no DB. Must not invent values."""
from quickscan import quick_scan_us as q

OFFER = """Primary work location: Austin, TX
Base salary: $145,000 per year
Sign-on bonus: $20,000, repayable if you leave within 12 months
Target annual bonus: 10% of base salary, subject to company performance
Equity: RSUs with a grant value of $200,000 vesting over 4 years with a 1-year cliff
Start date 2026."""


def test_us_full_offer():
    r = q(OFFER)
    assert r["fields"] == {"baseSalary": 145000, "signingBonus": 20000, "targetBonus": 14500, "rsuPerYear": 50000}
    assert r["state"] == "TX"
    assert any("Clawback" in f for f in r["flags"]) and any("cliff" in f for f in r["flags"])


def test_us_does_not_invent():
    r = q("Hourly rate $70/hour. Work location: New York or California. RSUs: 500 shares")
    assert r["fields"] == {} and "state" not in r
    assert any("hourly" in n for n in r["notes"]) and any("RSUs" in n for n in r["notes"])


def test_us_empty_and_no_india_assumptions():
    assert q("")["fields"] == {}
    assert q("CTC Rs 18,00,000 per annum")["fields"] == {}


def test_us_monthly_and_k():
    r = q("Base pay: $9,000 per month\nSigning bonus $15k")
    assert r["fields"]["baseSalary"] == 108000 and r["fields"]["signingBonus"] == 15000
