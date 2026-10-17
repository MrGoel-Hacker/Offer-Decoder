"""Plain-English 'why it matters' / 'what to ask' for every red flag (deterministic)."""
import re

GUIDE = [
    (r"take[\s-]*home|in[\s-]*hand", "A big gap between CTC and in-hand usually means the headline includes non-cash, deferred or one-time items.", "Can you share a monthly salary breakup showing the expected in-hand amount?"),
    (r"\bbasic\b", "PF and gratuity are calculated on basic, so a low basic quietly shrinks your retirement savings.", "Can the basic be raised to 40-50% of CTC without changing the total?"),
    (r"bond|service\s*agreement|minimum\s*service|liquidated", "A bond means you may owe money if you leave before the term. Indian courts usually enforce only reasonable, actually-incurred costs, but it still makes leaving harder.", "What is the exact bond amount and period, is it pro-rated, and what cost does it cover?"),
    (r"claw|repay|refund|joining|sign[\s-]*on", "One-time bonuses are fully taxed and usually must be paid back if you leave within 12-24 months.", "Is there a clawback, for how long, and is it pro-rated by months served?"),
    (r"notice", "Long notice periods make switching jobs harder - many employers will not wait 90 days or buy it out.", "Can the notice period be 30-60 days, and is notice buyout allowed?"),
    (r"compet|solicit", "Post-employment non-competes are generally void under Section 27 of the Indian Contract Act, but can still be used to pressure you or delay a switch.", "Can this be limited to non-solicitation of clients and only during employment?"),
    (r"probation", "During probation, notice is shorter and confirmation, leave or benefits can be withheld.", "What is the probation length, the notice during probation, and the criteria for confirmation?"),
    (r"esop|rsu|vest|cliff|stock", "ESOPs are worth nothing until they vest and you can sell them. A cliff means you get zero if you leave early.", "What is the vesting schedule and cliff, the latest FMV/409A, the strike price, and is there a buyback?"),
    (r"variable|payout|incentive|performance", "Variable pay depends on company and personal ratings - many people get 60-80% of target, often paid once a year.", "What was the average payout % for this team last year, and how often is it paid?"),
    (r"gratuity", "Gratuity is only paid after about 5 years of service; leave earlier and that part of CTC never reaches you.", "Is gratuity counted inside the CTC? If yes, can that amount move to fixed pay?"),
    (r"transfer|location|relocat", "A transfer-anywhere clause means you can be moved to another city with little say.", "Which locations are realistic, and is relocation support provided if I am moved?"),
]
DEFAULT = ("This clause can affect your money or your freedom to leave - get it clarified before you sign.", "Can you explain this clause and confirm the details in writing?")


def enrich(flag):
    if isinstance(flag, str):
        flag = {"level": "warn", "text": flag, "source": "clause"}
    text = str(flag.get("text", ""))
    why, ask = DEFAULT
    for pat, w, a in GUIDE:
        if re.search(pat, text, re.I):
            why, ask = w, a
            break
    return {"level": flag.get("level", "warn"), "text": text, "source": flag.get("source", "math"), "why": why, "ask": ask}
