"""Offline heuristic pre-fill (no AI). Beta - users must verify."""
import re

AMT = re.compile(
    r"(?P<cur>₹|rs\.?|inr)?\s*(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    r"(?P<unit>lpa|lakhs?|lacs?|crores?|cr\b|l\b|k\b)?(?P<pct>\s*%)?",
    re.I,
)
MONTHLY = re.compile(r"per\s*month|monthly|p\.?\s?m\.?(?:\W|$)|/\s*month|/\s*mo\b", re.I)
ANNUAL = re.compile(r"per\s*annum|annual|yearly|p\.?\s?a\.?(?:\W|$)|/\s*year|lpa", re.I)

FIELDS = {
    "ctc": r"\bctc\b|cost\s*to\s*(?:the\s*)?company|total\s*(?:annual\s*)?(?:compensation|package|remuneration)|annual\s*(?:package|compensation)",
    "basic": r"\bbasic\b",
    "hra": r"\bhra\b|house\s*rent",
    "employerPF": r"employer'?s?\s*(?:contribution\s*(?:to|towards)\s*)?(?:pf|provident)|(?<!employee\s)(?<!employee's\s)\bpf\b|(?<!employee\s)provident\s*fund",
    "gratuity": r"gratuity",
    "variablePay": r"variable|performance\s*(?:bonus|pay|linked|incentive)|annual\s*bonus|\bincentive",
    "joiningBonus": r"joining\s*bonus|sign[\s-]*on|signing\s*bonus|one[\s-]*time\s*bonus",
    "esopsPerYear": r"\besops?\b|\brsus?\b|stock\s*option|restricted\s*stock",
}

CLAUSES = [
    (r"\bbond\b|service\s*agreement|minimum\s*service|liquidated\s*damages", "Service bond / minimum service agreement mentioned"),
    (r"claw\s*-?\s*back|\brepa(?:y|id)|refund\s*the|recover(?:y|ed)?\s.{0,40}bonus", "Clawback / repayment clause on bonus or benefits"),
    (r"non[\s-]*compet|non[\s-]*solicit|shall\s*not\s.{0,40}competitor", "Non-compete / non-solicitation clause"),
    (r"\bcliff\b", "ESOP vesting cliff"),
    (r"variable[^\n]{0,140}(?:subject\s*to|discretion|rating|performance)", "Variable payout is conditional on performance / company discretion"),
    (r"transfer(?:red)?\s*to\s*any|any\s*(?:of\s*our\s*)?(?:location|office|city)", "You can be transferred to any location"),
]


def amounts(s):
    out = []
    for m in AMT.finditer(s):
        if m.group("pct"):
            continue
        raw = m.group("num")
        n = float(raw.replace(",", ""))
        unit = (m.group("unit") or "").lower()
        if unit.startswith(("lpa", "lakh", "lac")) or unit == "l":
            n *= 1e5
        elif unit.startswith("cr"):
            n *= 1e7
        elif unit == "k":
            n *= 1e3
        elif not m.group("cur") and "," not in raw and 1900 <= n <= 2100:
            continue
        if n >= 1000:
            out.append(n)
    return out


def _value_from(lines, i, start):
    seg = lines[i][start:start + 200]
    vals = amounts(seg)
    ctx = seg
    if not vals and i + 1 < len(lines):
        ctx = lines[i + 1]
        vals = amounts(ctx)
    if not vals:
        return None
    v = max(vals)
    if len(vals) == 1 and MONTHLY.search(ctx) and not ANNUAL.search(ctx):
        v *= 12
    return round(v)


def clause_flags(text):
    t = text or ""
    flags = []
    for pat, label in CLAUSES:
        if re.search(pat, t, re.I | re.S):
            flags.append(label)
    m = re.search(r"notice\s*period[^.\n]{0,80}?(\d+)\s*(days?|months?)", t, re.I)
    if m:
        days = int(m.group(1)) * (30 if m.group(2).lower().startswith("month") else 1)
        if days > 60:
            flags.append(f"Notice period of {m.group(1)} {m.group(2)} (over 60 days)")
    m = re.search(r"probation[^.\n]{0,80}?(\d+)\s*(months?|days?)", t, re.I)
    if m:
        months = int(m.group(1)) / (30 if m.group(2).lower().startswith("day") else 1)
        if months > 6:
            flags.append(f"Probation of {m.group(1)} {m.group(2)} (over 6 months)")
    return flags


def quick_scan(text):
    lines = [ln for ln in re.split(r"[\r\n]+", text or "") if ln.strip()]
    fields, notes = {}, []
    for key, pat in FIELDS.items():
        rx = re.compile(pat, re.I)
        best = None
        for i, ln in enumerate(lines):
            m = rx.search(ln)
            if not m:
                continue
            v = _value_from(lines, i, m.start())
            if v is None:
                continue
            if key == "ctc":
                best = max(best or 0, v)
            else:
                best = v
                break
        if best:
            fields[key] = best
    if "esopsPerYear" in fields:
        m = re.search(r"(?:over|across)\s*(\d)\s*years|(\d)[\s-]*years?\s*vesting|vest\w*\s*over\s*(\d)", text, re.I)
        yrs = next((int(g) for g in (m.groups() if m else []) if g), 0)
        if yrs > 1:
            fields["esopsPerYear"] = round(fields["esopsPerYear"] / yrs)
            notes.append(f"ESOP value spread over {yrs} years of vesting.")
        else:
            notes.append("ESOP value taken as-is - if it is a multi-year grant, divide by the vesting years.")
    ctc = fields.get("ctc")
    if ctc:
        for k in list(fields):
            if k != "ctc" and fields[k] > ctc:
                notes.append(f"Dropped {k} (larger than CTC - probably mis-read).")
                fields.pop(k)
    return {"fields": fields, "flags": clause_flags(text), "notes": notes, "found": list(fields.keys())}


# ---------------------------------------------------------------- US (offline)
US_AMT = re.compile(
    r"(?P<d>\$)?\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<unit>million\b|mm?\b|thousand\b|k\b)?",
    re.I,
)
US_HOURLY = re.compile(r"per\s*hour|/\s*h(?:ou)?r\b|hourly|an\s*hour", re.I)
US_MONTHLY = re.compile(r"per\s*month|monthly|/\s*month|/\s*mo\b", re.I)
US_BIWEEKLY = re.compile(r"bi-?weekly|semi-?monthly|per\s*pay\s*period|weekly", re.I)
US_ANNUAL = re.compile(r"per\s*year|annual|yearly|/\s*year|/\s*yr\b|per\s*annum|a\s*year", re.I)
US_SKIP_BONUS = re.compile(r"sign[\s-]*on|signing|joining|relocation|retention|referral|spot", re.I)

US_FIELDS = [
    ("baseSalary", r"base\s*(?:salary|pay|compensation)|annual(?:ized)?\s*(?:base\s*)?salary|starting\s*salary|salary\s*of|\bsalary\b"),
    ("signingBonus", r"sign[\s-]*on\s*bonus|signing\s*bonus|joining\s*bonus"),
    ("targetBonus", r"(?:target|annual|performance|discretionary|incentive)\s*(?:cash\s*)?bonus|bonus\s*target|\bbonus\b|incentive\s*(?:pay|compensation)"),
    ("rsuPerYear", r"\brsus?\b|restricted\s*stock|(?:stock|equity)\s*(?:grant|award)"),
]

US_CLAUSES = [
    (r"claw\s*-?\s*back|\brepa(?:y|id|yment)|reimburse\s+(?:the\s+)?company|refund\s*(?:the|any)", "Clawback / repayment clause (bonus, relocation or benefits)"),
    (r"non[\s-]*compet|non[\s-]*solicit|shall\s*not\s.{0,40}competitor", "Non-compete / non-solicitation clause"),
    (r"\bcliff\b", "Equity vesting cliff"),
    (r"(?:bonus|incentive)[^\n]{0,160}(?:subject\s*to|discretion|must\s*be\s*employed|remain\s*employed|continued\s*employment)", "Bonus is conditional on discretion or continued employment"),
    (r"(?:mandatory|binding)\s*arbitration|arbitration\s*agreement|waive[^\n]{0,30}jury", "Mandatory arbitration clause"),
    (r"contingent\s*(?:up)?on[^\n]{0,80}(?:background|reference|drug|i-?9|work\s*authorization)", "Offer is contingent on background check / verification"),
    (r"(?:invention|intellectual\s*property)[^\n]{0,60}assign|assign[^\n]{0,60}(?:invention|intellectual\s*property)", "Invention / IP assignment agreement"),
]


def _us_amounts(seg):
    out = []
    for m in US_AMT.finditer(seg):
        raw = m.group("num")
        unit = (m.group("unit") or "").lower()
        has_d = bool(m.group("d"))
        n = float(raw.replace(",", ""))
        if unit in ("m", "mm", "million"):
            n *= 1e6
        elif unit in ("k", "thousand"):
            n *= 1e3
        elif not has_d and "," not in raw:
            continue  # bare number: could be a year, count or percent
        elif not has_d and 1900 <= n <= 2100:
            continue
        if seg[m.end():m.end() + 1] == "%":
            continue
        out.append(n)
    return out


def _us_value(lines, i, start, notes, label):
    seg = lines[i][start:start + 220]
    ctx = seg
    vals = _us_amounts(seg)
    nxt = lines[i + 1] if i + 1 < len(lines) else ""
    if not vals and nxt and "%" not in seg and not any(re.search(p, nxt, re.I) for _, p in US_FIELDS):
        ctx = nxt[:220]
        vals = _us_amounts(ctx)
    if not vals:
        return None, ctx
    v = vals[0]
    if US_HOURLY.search(ctx) and v < 1000:
        notes.append(f"{label}: found an hourly rate (${v:g}/hr) - not converted. Enter the annual figure yourself.")
        return None, ctx
    if US_BIWEEKLY.search(ctx) and not US_ANNUAL.search(ctx):
        notes.append(f"{label}: found a weekly or per-paycheck amount - not converted. Enter the annual figure yourself.")
        return None, ctx
    if US_MONTHLY.search(ctx) and not US_ANNUAL.search(ctx):
        v *= 12
        notes.append(f"{label}: monthly amount multiplied by 12.")
    return round(v), ctx


def _us_state(text):
    from us_states import STATES
    cue = re.compile(r"work\s*location|located\s*in|based\s*in|office\s*in|report(?:ing)?\s*to\s*(?:our|the)|remote|hybrid|primary\s*location|duty\s*station|\blocation\b", re.I)
    found = set()
    names = sorted(((v["name"], k) for k, v in STATES.items()), key=lambda x: -len(x[0]))
    for ln in text.splitlines():
        if not cue.search(ln):
            continue
        rest = ln
        for name, code in names:
            rx = re.compile(r"\b" + re.escape(name) + r"\b", re.I)
            if rx.search(rest):
                found.add(code)
                rest = rx.sub(" ", rest)
        for m in re.finditer(r",\s*([A-Z]{2})\b(?:\s*\d{5})?", ln):
            if m.group(1) in STATES:
                found.add(m.group(1))
    return found


def quick_scan_us(text):
    text = text or ""
    lines = [ln for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    fields, notes, hit_ctx = {}, [], {}
    for key, pat in US_FIELDS:
        rx = re.compile(pat, re.I)
        label = {"baseSalary": "Base salary", "signingBonus": "Signing bonus", "targetBonus": "Target bonus", "rsuPerYear": "RSUs"}[key]
        for i, ln in enumerate(lines):
            m = rx.search(ln)
            if not m:
                continue
            if key == "targetBonus" and (US_SKIP_BONUS.search(ln) or "bonus" not in ln.lower() and "incentive" not in ln.lower()):
                continue
            if key == "baseSalary" and re.search(r"\bsalary\b", ln, re.I) and re.search(r"sign[\s-]*on|bonus", ln[:m.start()], re.I):
                continue
            v, ctx = _us_value(lines, i, m.start(), notes, label)
            if v is None and key == "targetBonus" and "baseSalary" in fields:
                pm = re.search(r"(\d+(?:\.\d+)?)\s*%", ln[m.start():m.start() + 220])
                if pm:
                    v = round(fields["baseSalary"] * float(pm.group(1)) / 100)
                    notes.append(f"Target bonus: {pm.group(1)}% of the base salary found above = ${v:,}.")
            if v is None:
                continue
            if key == "baseSalary" and not (15000 <= v <= 5000000):
                continue
            if key == "rsuPerYear":
                yrs = re.search(r"(?:over|across|vest\w*\s*(?:over|in|for))\s*(?:a\s*(?:period\s*of\s*)?)?(\d{1,2})\s*(?:-|\s)?\s*years?|(\d{1,2})\s*-?\s*year\s*vest", ctx + " " + text[:0], re.I)
                if not yrs:
                    yrs = re.search(r"(?:over|across)\s*(\d{1,2})\s*years?|(\d{1,2})\s*-?\s*year\s*vest", text, re.I)
                n = int(next((g for g in (yrs.groups() if yrs else []) if g), 0))
                if n > 1:
                    v = round(v / n)
                    notes.append(f"RSUs: dollar value spread over {n} years of vesting (per-year value shown). Share price at vesting will differ.")
                else:
                    notes.append("RSUs: a dollar value was found but no vesting period. Not filled - enter the per-year value yourself.")
                    continue
            fields[key] = v
            break
    if re.search(r"stock\s*options?|\bISOs?\b|\bNSOs?\b", text, re.I) and "rsuPerYear" not in fields:
        notes.append("Stock options were mentioned. Options are not RSUs and are not counted - check their value and strike price separately.")
    if re.search(r"\brsus?\b|restricted\s*stock", text, re.I) and "rsuPerYear" not in fields and not any("RSUs:" in n for n in notes):
        notes.append("RSUs were mentioned without a dollar value (shares only?). Not filled - enter the per-year value yourself.")
    if "baseSalary" not in fields and re.search(r"\$\s*\d[\d,.]*\s*(?:per\s*hour|/\s*h(?:ou)?r|an\s*hour)", text, re.I) and not any("hourly" in n for n in notes):
        notes.append("An hourly rate was found - not converted to an annual salary. Enter the annual figure yourself.")
    if re.search(r"401\s*\(?k\)?", text, re.I):
        notes.append("401(k) mentioned. Your own contribution is your choice, so it is left blank - enter it if you plan to contribute.")
    states = _us_state(text)
    out = {"fields": fields, "flags": [], "notes": notes}
    if len(states) == 1:
        out["state"] = next(iter(states))
    elif len(states) > 1:
        notes.append("More than one state appears near location words. Work state not set - pick it yourself.")
    else:
        notes.append("Work state not detected. Pick it for state tax.")
    flags = []
    for pat, label in US_CLAUSES:
        if re.search(pat, text, re.I | re.S):
            flags.append(label)
    out["flags"] = flags
    out["found"] = list(fields.keys()) + (["state"] if out.get("state") else [])
    return out


def us_clause_flags(text):
    return [label for pat, label in US_CLAUSES if re.search(pat, text or "", re.I | re.S)]
