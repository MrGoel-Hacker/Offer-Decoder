"""1:1 port of the Offer Decoder JS core math (India FY 2026-27, new regime)."""
import math

SLABS = [  # new regime, FY 2026-27
    (400000, 0),
    (800000, 0.05),
    (1200000, 0.10),
    (1600000, 0.15),
    (2000000, 0.20),
    (2400000, 0.25),
    (math.inf, 0.30),
]
STANDARD_DEDUCTION = 75000
REBATE_MAX = 60000
REBATE_LIMIT = 1200000
CESS_RATE = 0.04
PROF_TAX_DEFAULT = 2400


def js_round(x):
    # JS Math.round semantics (half rounds toward +infinity)
    return int(math.floor(x + 0.5))


def _clean(x):
    return int(x) if isinstance(x, float) and x.is_integer() else x


def slab_tax(taxable):
    tax, prev = 0, 0
    for up_to, rate in SLABS:
        if taxable <= prev:
            break
        tax += (min(taxable, up_to) - prev) * rate
        prev = up_to
    return tax


def compute_tax(taxable_income):
    taxable = max(0, js_round(taxable_income))
    gross = slab_tax(taxable)
    rebate = 0
    if taxable <= REBATE_LIMIT:
        rebate = min(gross, REBATE_MAX)
    else:
        excess = taxable - REBATE_LIMIT
        if gross > excess:
            rebate = gross - excess
    after_rebate = max(0, gross - rebate)
    cess = after_rebate * CESS_RATE
    return {
        "taxable": taxable,
        "slabTax": js_round(gross),
        "rebate": js_round(rebate),
        "cess": js_round(cess),
        "totalTax": js_round(after_rebate + cess),
    }


def num(v):
    # JS: isFinite(+v) && +v > 0 ? +v : 0
    if v is None or isinstance(v, (list, dict)):
        return 0
    if isinstance(v, bool):
        v = 1 if v else 0
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return 0
        try:
            v = float(s)
        except ValueError:
            return 0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    return _clean(f) if math.isfinite(f) and f > 0 else 0


def js_falsy(v):
    if v is None or v is False or v == "":
        return True
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v == 0 or (isinstance(v, float) and math.isnan(v))
    return False


def decode(inp):
    ctc = num(inp.get("ctc"))
    variable = num(inp.get("variablePay"))
    joining = num(inp.get("joiningBonus"))
    esops = num(inp.get("esopsPerYear"))
    other_non_cash = num(inp.get("otherNonCash"))
    assumptions = []

    basic = num(inp.get("basic"))
    if not basic:
        basic = js_round(ctc * 0.4)
        assumptions.append("Basic salary not given - assumed 40% of CTC (edit it if your letter says otherwise).")
    employer_pf = num(inp.get("employerPF"))
    if not employer_pf:
        employer_pf = js_round(basic * 0.12)
        assumptions.append("Employer PF assumed at 12% of basic.")
    gratuity = num(inp.get("gratuity"))
    if inp.get("gratuityInCTC") is not False and js_falsy(inp.get("gratuity")):
        gratuity = js_round(basic * 0.0481)
        assumptions.append("Gratuity assumed inside CTC at 4.81% of basic (standard practice).")
    employee_pf = num(inp.get("employeePF")) or js_round(basic * 0.12)
    prof_tax = num(inp.get("profTax")) or PROF_TAX_DEFAULT

    fixed_ctc = ctc - variable - joining - esops
    cash_gross = max(0, fixed_ctc - employer_pf - gratuity - other_non_cash)

    fixed_taxable = max(0, cash_gross - STANDARD_DEDUCTION)
    tax_fixed = compute_tax(fixed_taxable)
    tax_with_variable = compute_tax(fixed_taxable + variable)
    tax_on_variable = tax_with_variable["totalTax"] - tax_fixed["totalTax"]

    annual_take_home_fixed = cash_gross - employee_pf - prof_tax - tax_fixed["totalTax"]
    monthly_fixed = annual_take_home_fixed / 12
    monthly_with_variable = (annual_take_home_fixed + variable - tax_on_variable) / 12

    hra = num(inp.get("hra"))
    derived = {
        "basic": basic,
        "hra": hra,
        "employerPF": employer_pf,
        "gratuity": gratuity,
        "employeePF": employee_pf,
        "profTax": prof_tax,
        "variable": variable,
        "joining": joining,
        "esops": esops,
        "otherNonCash": other_non_cash,
        "specialAndOther": max(0, fixed_ctc - basic - hra - employer_pf - gratuity - other_non_cash),
    }

    flags = []

    def pct(x):
        return (x / ctc) * 100 if ctc else 0

    def fixed0(x):
        return str(js_round(x))

    if ctc and pct(variable) > 15:
        flags.append({"level": "warn", "text": f"Variable pay is {fixed0(pct(variable))}% of CTC. It is not guaranteed - ask what payout % people actually got last year and what the conditions are."})
    if ctc and pct(esops) > 10:
        flags.append({"level": "warn", "text": f"ESOPs make up {fixed0(pct(esops))}% of CTC. That is paper value, not salary - check vesting, the cliff, and what the stock is worth today in cash terms."})
    if joining > 0:
        flags.append({"level": "info", "text": "Joining bonus is one-time. Check for a clawback clause (repay if you leave within 12-24 months) and remember it is fully taxed."})
    if gratuity > 0:
        flags.append({"level": "info", "text": "Gratuity sits inside your CTC but only pays out after ~5 years. Standard practice, but it inflates the headline number."})
    if ctc and pct(basic) < 35:
        flags.append({"level": "info", "text": f"Basic is only {fixed0(pct(basic))}% of CTC. Low basic means lower PF and gratuity contributions - and lower tax-free growth on those."})
    if ctc and monthly_fixed * 12 < ctc * 0.62:
        flags.append({"level": "warn", "text": "Your fixed take-home is well under 65% of the CTC headline. Recheck what is counted inside CTC (ESOPs, insurance, joining bonus)."})
    for t in inp.get("textFlags") or []:
        flags.append(t)

    tips = []
    if pct(variable) > 10:
        tips.append("Ask for the variable-pay payout history and get the payout formula in writing.")
    if esops > 0:
        tips.append("Ask for the ESOP vesting schedule, the latest 409A/FMV, and the total pool size so you can value your grant.")
    if joining > 0:
        tips.append("If there is a clawback on the joining bonus, negotiate the window down or the amount up.")
    if ctc and pct(basic) < 40:
        tips.append("Ask if the basic can be raised - it compounds into PF, gratuity and HRA benefits.")
    tips.append("If comparing offers, compare fixed take-home per month, not CTC headlines.")
    tips.append("Get the final numbers in the written offer, not over a call.")

    return {
        "ctc": ctc, "derived": {k: _clean(v) for k, v in derived.items()}, "assumptions": assumptions,
        "fixedCTC": _clean(fixed_ctc), "cashGross": _clean(cash_gross), "standardDeduction": STANDARD_DEDUCTION,
        "taxFixed": tax_fixed, "taxOnVariable": tax_on_variable,
        "annualTakeHomeFixed": js_round(annual_take_home_fixed),
        "monthlyFixed": js_round(monthly_fixed),
        "monthlyWithVariable": js_round(monthly_with_variable),
        "joiningAfterTax": js_round(joining * 0.7),
        "flags": flags, "tips": tips,
        "meta": {
            "regime": "New tax regime, FY 2026-27 (AY 2027-28)",
            "slabsVerifiedAgainst": "incometaxindia.gov.in; Budget 2026-27 made no slab changes",
        },
    }


def inr(n):
    if n is None or not math.isfinite(n):
        return "-"
    neg = n < 0
    s = str(abs(js_round(n)) if not neg else js_round(abs(n)))
    out = s[-3:] if len(s) > 3 else s
    rest = s[:-3]
    while len(rest) > 2:
        out = rest[-2:] + "," + out
        rest = rest[:-2]
    if rest:
        out = rest + "," + out
    return ("-" if neg else "") + "\u20B9" + out
