"""Tests for offer_pack.py (negotiation scenarios, scripts, comparison) and the payment entitlement check."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import offer_pack  # noqa: E402
import payments  # noqa: E402
from decoder import decode  # noqa: E402
from us_decoder import decode_us  # noqa: E402

IN_INPUT = {"ctc": 1800000, "basic": 720000, "hra": 360000, "employerPF": 86400, "gratuity": 34632,
            "variablePay": 180000, "joiningBonus": 100000}
US_INPUT = {"baseSalary": 150000, "targetBonus": 15000, "rsuPerYear": 40000, "k401": 10000, "state": "TX"}


def _in(inp=IN_INPUT, company=""):
    return {"country": "in", "input": inp, "result": decode(inp), "company": company}


def _us(inp=US_INPUT):
    return {"country": "us", "input": inp, "result": decode_us(inp), "company": ""}


def test_scale_fixed_keeps_variable_and_bonus():
    out = offer_pack.scale_fixed(IN_INPUT, "in", 10)
    assert out["variablePay"] == IN_INPUT["variablePay"] and out["joiningBonus"] == IN_INPUT["joiningBonus"]
    assert out["basic"] == 792000
    assert out["ctc"] == 1800000 + round((1800000 - 180000 - 100000) * 0.10)
    us = offer_pack.scale_fixed(US_INPUT, "us", 10)
    assert us["baseSalary"] == 165000 and us["targetBonus"] == 15000


def test_scenarios_increase_in_hand_and_do_not_mutate_input():
    snapshot = dict(IN_INPUT)
    pack = offer_pack.negotiation_pack(_in())
    assert IN_INPUT == snapshot
    gains = [s["monthlyGain"] for s in pack["scenarios"]]
    assert all(g > 0 for g in gains) and gains == sorted(gains)
    assert pack["currentMonthlyFixed"] == decode(IN_INPUT)["monthlyFixed"]
    assert "not market salary data" in pack["note"]


def test_ask_pct_is_clamped_and_scripts_use_real_numbers():
    pack = offer_pack.negotiation_pack(_in(), ask_pct=500)
    assert pack["askPct"] == offer_pack.MAX_ASK_PCT
    cur = offer_pack.money("in", pack["currentMonthlyFixed"])
    assert cur in pack["scripts"]["email"] and cur in pack["scripts"]["chat"]
    assert "[Recruiter name]" in pack["scripts"]["email"]


def test_us_pack_and_priorities():
    pack = offer_pack.negotiation_pack(_us())
    assert pack["country"] == "us" and pack["scenarios"][0]["text"].count("$") >= 1
    assert any("401(k)" in p for p in pack["priorities"])
    assert any("Equity" in p for p in pack["priorities"])


def test_compare_offers_and_country_mismatch():
    better = _in({**IN_INPUT, "ctc": 2000000}, company="Beta")
    cmp = offer_pack.compare_offers(_in(company="Alpha"), better)
    assert "Beta" in cmp["verdict"] and cmp["monthlyFixedDifference"] < 0
    assert len(cmp["offers"]) == 2 and cmp["caveats"]
    with pytest.raises(ValueError):
        offer_pack.compare_offers(_in(), _us())


def test_compare_same_labels_become_offer_a_b():
    cmp = offer_pack.compare_offers(_in(), _in({**IN_INPUT, "ctc": 1900000}))
    assert [o["label"] for o in cmp["offers"]] == ["Offer A", "Offer B"]


class _Col:
    def __init__(self, docs):
        self.docs = docs

    async def find_one(self, q):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in q.items())), None)


class _DB:
    def __init__(self, purchases):
        self.purchases = _Col(purchases)


def test_has_paid_only_for_confirmed_purchase_of_that_report():
    db = _DB([
        {"userId": "u1", "reportId": "r1", "status": "paid"},
        {"userId": "u1", "reportId": "r2", "status": "pending"},
        {"userId": "u2", "reportId": "r3", "status": "failed"},
    ])
    run = asyncio.get_event_loop_policy().new_event_loop().run_until_complete
    assert run(payments.has_paid(db, "u1", "r1")) is True
    assert run(payments.has_paid(db, "u1", "r2")) is False
    assert run(payments.has_paid(db, "u2", "r1")) is False
    assert run(payments.has_paid(db, "u2", "r3")) is False
