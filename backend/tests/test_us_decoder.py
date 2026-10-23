"""Offline unit tests for the US tax engine (TY2026, single filer). No server/Mongo needed."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from us_decoder import FED_BRACKETS, FED_STD, K401_LIMIT, bracket_tax, decode_us  # noqa: E402


def test_fed_bracket_math():
    # IRS Rev. Proc. 2025-32 single: 5800 + 22% over 50,400 at 79,400 -> 12,180
    assert bracket_tax(79400, FED_BRACKETS) == 5800 + 0.22 * (79400 - 50400)
    assert bracket_tax(0, FED_BRACKETS) == 0
    assert bracket_tax(12400, FED_BRACKETS) == 1240


def test_no_state_means_federal_and_fica_only():
    r = decode_us({"baseSalary": 120000, "state": ""})
    assert r["taxFixed"]["stateTax"] == 0
    assert r["stateName"] == ""
    assert any("No work state" in a for a in r["assumptions"])
    # federal: taxable 120000-16100=103900 -> 5800+.22*(103900-50400)=17570
    assert r["taxFixed"]["federal"] == 17570
    # SS 6.2% of 120000 = 7440; medicare 1.45% = 1740
    assert r["taxFixed"]["ss"] == 7440
    assert r["taxFixed"]["medicare"] == 1740
    assert r["monthlyFixed"] == round((120000 - (17570 + 7440 + 1740)) / 12)


def test_401k_reduces_federal_not_fica():
    r = decode_us({"baseSalary": 100000, "k401": 10000, "state": "TX"})
    assert r["taxFixed"]["federal"] == bracket_tax(100000 - 10000 - FED_STD, FED_BRACKETS)
    assert r["taxFixed"]["ss"] == 6200  # full wages


def test_401k_capped():
    r = decode_us({"baseSalary": 100000, "k401": 40000, "state": "TX"})
    assert r["derived"]["k401"] == K401_LIMIT
    assert any("capped" in a for a in r["assumptions"])


def test_state_tax_applied():
    r = decode_us({"baseSalary": 100000, "state": "CO"})
    # CO taxable: 100000-16100(std)=83900, flat 4.4%
    assert r["taxFixed"]["stateTax"] == round(83900 * 0.044)
    assert r["stateName"] == "Colorado"


def test_no_tax_state():
    r = decode_us({"baseSalary": 100000, "state": "TX"})
    assert r["taxFixed"]["stateTax"] == 0
    assert any("no state income tax" in a for a in r["assumptions"])


def test_signing_bonus_taxed_separately():
    r = decode_us({"baseSalary": 150000, "signingBonus": 20000, "state": "WA"})
    assert 0 < r["joiningAfterTax"] < 20000
    assert r["monthlyFixed"] > 0
    # signing bonus must not inflate recurring monthly take-home
    r2 = decode_us({"baseSalary": 150000, "state": "WA"})
    assert r["monthlyFixed"] == r2["monthlyFixed"]


def test_ss_wage_base_cap():
    r = decode_us({"baseSalary": 300000, "state": "TX"})
    assert r["taxFixed"]["ss"] == round(0.062 * 184500)
    # additional medicare 0.9% over 200k
    assert r["taxFixed"]["medicare"] == round(0.0145 * 300000 + 0.009 * 100000)
