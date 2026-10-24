"""Negotiation guidance and two-offer comparison for a saved report (deterministic, no AI).

Everything here is computed from the user's own offer numbers by the same tax engines as the
free report. There is no salary benchmark data: suggested asks are what-if scenarios, never
market rates. Not wired to any paywall by itself - server routes decide who may call it.
"""
from copy import deepcopy

from decoder import decode, inr
from flag_guide import enrich
from us_decoder import decode_us

MAX_ASK_PCT = 30
DEFAULT_ASK_PCT = 10
SCENARIO_PCTS = (5, 10, 15)

NOTE_NO_BENCHMARK = (
    "These numbers are what-if scenarios on your own offer. They are not market salary data, "
    "and nobody can promise a company will agree to any figure."
)


def money(country, n):
    if country == "us":
        n = int(round(n or 0))
        return ("-" if n < 0 else "") + "$" + f"{abs(n):,}"
    return inr(n)


def _num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def scale_fixed(inp: dict, country: str, pct: float) -> dict:
    """Return a copy of the input with FIXED pay raised by pct%. Variable, bonus and equity stay as they are."""
    out = deepcopy(inp)
    f = 1 + pct / 100.0
    if country == "us":
        out["baseSalary"] = round(_num(inp.get("baseSalary")) * f)
        return out
    ctc = _num(inp.get("ctc"))
    fixed = ctc - _num(inp.get("variablePay")) - _num(inp.get("joiningBonus")) - _num(inp.get("esopsPerYear"))
    out["ctc"] = round(ctc + max(0.0, fixed) * pct / 100.0)
    for k in ("basic", "hra", "employerPF", "gratuity"):
        if _num(inp.get(k)):
            out[k] = round(_num(inp.get(k)) * f)
    if _num(inp.get("employeePF")):
        out["employeePF"] = round(_num(inp.get("employeePF")) * f)
    return out


def _run(inp: dict, country: str) -> dict:
    return decode_us(inp) if country == "us" else decode(inp)


def scenarios(inp: dict, country: str, base_monthly: float) -> list:
    rows = []
    for p in SCENARIO_PCTS:
        r = _run(scale_fixed(inp, country, p), country)
        rows.append({
            "raisePct": p,
            "monthlyFixed": r["monthlyFixed"],
            "monthlyGain": r["monthlyFixed"] - base_monthly,
            "text": f"If fixed pay were {p}% higher: monthly in-hand {money(country, r['monthlyFixed'])} "
                    f"({'+' if r['monthlyFixed'] - base_monthly >= 0 else ''}{money(country, r['monthlyFixed'] - base_monthly)} a month).",
        })
    return rows


def priorities(result: dict, country: str) -> list:
    """Ordered talking points driven by the offer's own structure (reuses the red-flag logic)."""
    d = result.get("derived", {})
    ctc = _num(result.get("ctc"))
    items = []
    var = _num(d.get("variable"))
    if ctc and var / ctc > 0.10:
        items.append("Make more of the pay fixed: ask to move part of the variable pay into fixed pay, or get the payout formula and last year's payout in writing.")
    if country == "in" and ctc and _num(d.get("basic")) / ctc < 0.40:
        items.append("Ask to raise the basic salary share without changing the total - it lifts PF and gratuity.")
    if _num(d.get("joining")) > 0:
        items.append("Joining or signing bonus: ask for the clawback window to be shorter or pro-rated, or the amount higher.")
    if (country == "in" and _num(d.get("esops")) > 0) or (country == "us" and _num(d.get("rsus")) > 0):
        items.append("Equity: ask for the vesting schedule, cliff, grant value basis and refresh policy before counting it as pay.")
    if country == "us":
        items.append("Ask about the 401(k) match and any benefits cost (health premiums) that change take-home.")
    items.append("Ask for the final numbers and any notice, bond or non-compete terms in the written offer.")
    return items


def questions(result: dict) -> list:
    seen, out = set(), []
    for f in result.get("flags", []):
        f = f if "ask" in f else enrich(f)
        if f["ask"] not in seen:
            seen.add(f["ask"])
            out.append({"about": f["text"], "ask": f["ask"], "why": f["why"]})
    return out


def scripts(result: dict, country: str, ask_pct: float, scenario_monthly: float) -> dict:
    cur = money(country, result["monthlyFixed"])
    tgt = money(country, scenario_monthly)
    email = (
        "Subject: Offer - a few points to discuss\n\n"
        "Hi [Recruiter name],\n\n"
        "Thank you for the offer for the [role] position. I'm excited about the role and the team.\n\n"
        f"I went through the numbers carefully. With the current structure my estimated fixed monthly in-hand is about {cur}. "
        f"I'd like to discuss whether the fixed component can be raised by around {ask_pct:g}% (which would bring it to about {tgt} a month), "
        "or whether the structure can shift more of the pay into fixed.\n\n"
        "I'd also like to confirm a few details in the written offer: [list the questions you chose].\n\n"
        "I'm keen to make this work. Could we find 15 minutes this week to talk?\n\n"
        "Thanks,\n[Your name]"
    )
    chat = (
        "Hi [Name], thanks again for the offer, I'm really interested. "
        f"Going through the structure, my fixed in-hand comes to about {cur} a month. "
        f"Is there room to raise the fixed pay by around {ask_pct:g}% (about {tgt})? "
        "Also keen to confirm [your questions] in writing. Happy to jump on a quick call."
    )
    return {"email": email, "chat": chat}


def negotiation_pack(report: dict, ask_pct: float = DEFAULT_ASK_PCT) -> dict:
    country = report.get("country", "in")
    ask_pct = max(1.0, min(float(ask_pct or DEFAULT_ASK_PCT), float(MAX_ASK_PCT)))
    result = report["result"]
    inp = report.get("input", {})
    base = result["monthlyFixed"]
    target = _run(scale_fixed(inp, country, ask_pct), country)["monthlyFixed"]
    return {
        "country": country,
        "currentMonthlyFixed": base,
        "priorities": priorities(result, country),
        "scenarios": scenarios(inp, country, base),
        "questions": questions(result),
        "scripts": scripts(result, country, ask_pct, target),
        "askPct": ask_pct,
        "note": NOTE_NO_BENCHMARK,
    }


def _row(report: dict) -> dict:
    r = report["result"]
    country = report.get("country", "in")
    joining = _num(r.get("joiningAfterTax"))
    return {
        "label": (report.get("company") or "").strip() or "Offer",
        "country": country,
        "monthlyFixed": r["monthlyFixed"],
        "monthlyWithVariable": r["monthlyWithVariable"],
        "fourYearFixedOnly": r["monthlyFixed"] * 48 + joining,
        "fourYearWithVariable": r["monthlyWithVariable"] * 48 + joining,
        "flagCount": len(r.get("flags", [])),
    }


def compare_offers(a: dict, b: dict) -> dict:
    ca, cb = a.get("country", "in"), b.get("country", "in")
    if ca != cb:
        raise ValueError("Both offers must be from the same country to compare.")
    ra, rb = _row(a), _row(b)
    if ra["label"] == rb["label"]:
        ra["label"], rb["label"] = "Offer A", "Offer B"
    diff = ra["monthlyFixed"] - rb["monthlyFixed"]
    if diff == 0:
        verdict = "Both offers give the same fixed monthly in-hand."
    else:
        w, l = (ra, rb) if diff > 0 else (rb, ra)
        verdict = f"{w['label']} gives {money(ca, abs(diff))} more fixed in-hand per month than {l['label']}."
    return {
        "country": ca,
        "offers": [ra, rb],
        "monthlyFixedDifference": diff,
        "verdict": verdict,
        "caveats": [
            "Four-year figures add 48 months of take-home plus the one-time bonus after tax. They ignore raises, equity, ESOP/RSU value, benefits and city costs.",
            "Take-home uses the estimates from each saved report, with the assumptions shown there.",
            NOTE_NO_BENCHMARK,
        ],
    }
