"""US job offer decoding: federal + FICA + state income tax, tax year 2026, single filer.

Sources:
- Federal brackets + standard deduction: IRS Rev. Proc. 2025-32 (TY2026, OBBBA).
- FICA: SSA 2026 - Social Security 6.2% up to $184,500; Medicare 1.45% (all wages)
  + 0.9% additional over $200,000.
- 401(k) elective deferral limit 2026: $24,500 (IRS Notice 2025-67 / IR-2025-111).
- State tables: Tax Foundation 2026 (see us_states.py for simplifications).
"""
import math

from decoder import _clean, js_round, num
from us_states import STATES

FED_BRACKETS = [(0, .10), (12400, .12), (50400, .22), (105700, .24), (201775, .32), (256225, .35), (640600, .37)]
FED_STD = 16100
SS_RATE = .062
SS_WAGE_BASE = 184500
MEDICARE_RATE = .0145
ADDL_MEDICARE_RATE = .009
ADDL_MEDICARE_THRESHOLD = 200000
K401_LIMIT = 24500

INPUT_KEYS_US = ["baseSalary", "targetBonus", "signingBonus", "rsuPerYear", "k401"]


def bracket_tax(taxable, brackets):
    tax = 0.0
    for i, (thr, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else math.inf
        if taxable > thr:
            tax += (min(taxable, upper) - thr) * rate
    return tax


def _taxes(gross, k401, state_code):
    ss = SS_RATE * min(gross, SS_WAGE_BASE)
    medicare = MEDICARE_RATE * gross + ADDL_MEDICARE_RATE * max(0, gross - ADDL_MEDICARE_THRESHOLD)
    fed_taxable = max(0, gross - k401 - FED_STD)
    federal = bracket_tax(fed_taxable, FED_BRACKETS)
    st = STATES.get((state_code or "").upper())
    state_tax, state_taxable = 0.0, 0.0
    if st and not st.get("none"):
        state_taxable = max(0, gross - k401 - st.get("std", 0) - st.get("exempt", 0))
        state_tax = bracket_tax(state_taxable, st["brackets"])
    return {
        "ss": ss, "medicare": medicare, "federal": federal, "stateTax": state_tax,
        "fedTaxable": fed_taxable, "stateTaxable": state_taxable,
        "total": ss + medicare + federal + state_tax,
        "stateName": st["name"] if st else "",
    }


def decode_us(inp):
    base = num(inp.get("baseSalary"))
    bonus = num(inp.get("targetBonus"))
    signing = num(inp.get("signingBonus"))
    rsus = num(inp.get("rsuPerYear"))
    state_code = (inp.get("state") or "").strip().upper()[:2]
    assumptions = []

    k401_raw = num(inp.get("k401"))
    k401 = min(k401_raw, K401_LIMIT)
    if k401_raw > K401_LIMIT:
        assumptions.append(f"401(k) contribution capped at the 2026 limit of ${K401_LIMIT:,}.")
    if not k401_raw:
        assumptions.append("No 401(k) contribution entered - even a few percent lowers this year's tax (edit it if you contribute).")
    if not state_code or state_code not in STATES:
        state_code = ""
        assumptions.append("No work state selected - showing federal taxes and FICA only. Pick a state for the full picture.")
    elif STATES[state_code].get("none"):
        assumptions.append(f"{STATES[state_code]['name']} has no state income tax on wages.")

    gross_all = base + bonus + rsus
    comp = gross_all  # headline "total annual comp" (excludes one-time signing bonus)

    # monthlyFixed: recurring base-only view; 401(k) allocated pro-rata to base
    k_base = k401 * (base / gross_all) if gross_all else k401
    t_base = _taxes(base, k_base, state_code)
    t_all = _taxes(gross_all, k401, state_code)
    t_sign = _taxes(gross_all + signing, k401, state_code)

    take_home_base = base - k_base - t_base["total"]
    take_home_all = gross_all - k401 - t_all["total"]
    tax_on_variable = t_all["total"] - t_base["total"]

    derived = {
        "base": base, "bonus": bonus, "signing": signing, "rsus": rsus, "k401": k401,
        "variable": bonus, "joining": signing,
    }

    def pct(x):
        return (x / comp) * 100 if comp else 0

    flags = []
    if comp and pct(bonus) > 15:
        flags.append({"level": "warn", "text": f"Bonus is {js_round(pct(bonus))}% of total comp. Target bonuses are not guaranteed - ask what the actual payout % was last year."})
    if comp and pct(rsus) > 25:
        flags.append({"level": "warn", "text": f"Equity is {js_round(pct(rsus))}% of total comp. That is paper value until it vests and you can sell - check the vesting schedule and the cliff."})
    if signing > 0:
        flags.append({"level": "info", "text": "Signing bonus is one-time and fully taxed. Check for a clawback (repay if you leave within 12-24 months)."})
    if rsus > 0:
        flags.append({"level": "info", "text": "RSUs are taxed as ordinary income when they vest. Companies usually withhold only 22% federal - at higher brackets you may owe more at tax time."})
    if comp and take_home_base * 12 < comp * 0.6:
        flags.append({"level": "info", "text": "Base-only take-home is well under 65% of total comp - a lot of this offer rides on bonus or equity."})
    for t in inp.get("textFlags") or []:
        flags.append(t)

    tips = []
    tips.append("Ask about the 401(k) match - it is free money and does not show up in take-home math.")
    if rsus > 0:
        tips.append("Ask for the RSU vesting schedule, whether there is a 1-year cliff, and about refresh grants.")
    if bonus > 0:
        tips.append("Ask what percentage of target bonus the team actually received last year.")
    tips.append("If comparing offers, compare monthly take-home on base salary, not total comp headlines.")
    tips.append("Get the final numbers in the written offer, not over a call.")

    return {
        "country": "us",
        "ctc": _clean(comp),
        "derived": {k: _clean(v) for k, v in derived.items()},
        "assumptions": assumptions,
        "fixedCTC": _clean(base),
        "cashGross": _clean(gross_all),
        "standardDeduction": FED_STD,
        "k401Limit": K401_LIMIT,
        "state": state_code,
        "stateName": t_all["stateName"],
        "taxFixed": {
            "taxable": js_round(t_all["fedTaxable"]),
            "stateTaxable": js_round(t_all["stateTaxable"]),
            "federal": js_round(t_all["federal"]),
            "stateTax": js_round(t_all["stateTax"]),
            "ss": js_round(t_all["ss"]),
            "medicare": js_round(t_all["medicare"]),
            "totalTax": js_round(t_all["total"]),
        },
        "taxOnVariable": js_round(tax_on_variable),
        "annualTakeHomeFixed": js_round(take_home_base),
        "monthlyFixed": js_round(take_home_base / 12),
        "monthlyWithVariable": js_round(take_home_all / 12),
        "joiningAfterTax": js_round(signing - (t_sign["total"] - t_all["total"])),
        "flags": flags,
        "tips": tips,
        "meta": {
            "regime": "US federal + state, tax year 2026 (single filer, standard deduction)",
            "slabsVerifiedAgainst": "IRS Rev. Proc. 2025-32; SSA 2026 COLA; Tax Foundation state tables (Feb 2026)",
            "countryNote": "Estimate: single filer, standard deduction, no local/city taxes, state credit-type exemptions and phaseouts not modelled.",
        },
    }
