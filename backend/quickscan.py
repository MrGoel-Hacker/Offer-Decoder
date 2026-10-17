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
