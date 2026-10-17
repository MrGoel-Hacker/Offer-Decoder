"""OpenRouter (free models only) extraction with guardrails: per-IP, global breaker, 24h cache."""
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger("ai_extract")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TEXT_MODELS = ["nvidia/nemotron-3-super-120b-a12b:free", "google/gemma-4-31b-it:free", "nvidia/nemotron-3.5-super-vl:free"]
IMAGE_MODELS = ["google/gemma-4-31b-it:free", "nvidia/nemotron-3.5-super-vl:free"]

# ---- RATE LIMITS / COST GUARDRAILS live here ----
AI_PER_IP_PER_DAY = 5
AI_GLOBAL_PER_DAY = 45  # OpenRouter free tier is 50/day
CACHE_TTL_SECONDS = 24 * 3600
PER_MODEL_TIMEOUT = 45
CHAIN_DEADLINE_SECONDS = 95  # whole fallback chain must answer before the browser/ingress gives up

LIMIT_MSG = "AI limit reached for today, use Quick scan or manual entry"
UNAVAILABLE_MSG = "AI couldn't read this right now, use Quick scan or manual entry"
NOT_CONFIGURED_MSG = "AI extraction is not switched on yet, use Quick scan or manual entry"

NUM_KEYS = ["ctc", "basic", "hra", "employerPF", "gratuity", "variablePay", "joiningBonus", "esopsPerYear", "otherNonCash"]

SYSTEM_PROMPT = (
    "You extract structured data from Indian job offer letters. Reply with ONLY one JSON object, no prose, with keys: "
    "ctc, basic, hra, employerPF, gratuity, variablePay, joiningBonus, esopsPerYear, otherNonCash (all ANNUAL amounts in INR as plain numbers, 0 if absent; "
    "convert monthly figures x12 and lakhs/crores to rupees; esopsPerYear = total grant value divided by vesting years; otherNonCash = insurance/meal cards/other non-cash items inside CTC), "
    "company (string, '' if absent), role (string, '' if absent), and flags (array of short strings, max 10, about risky clauses: "
    "bond/service agreement, clawback, notice period over 60 days, non-compete, probation over 6 months, variable payout conditions, ESOP vesting cliff, anything else risky). "
    "Never invent numbers that are not in the letter."
)


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def text_hash(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode("utf-8"))
    return h.hexdigest()


async def bump(db, key, limit):
    """Atomically count one use; returns True if still within limit."""
    doc = await db.usage.find_one_and_update(
        {"_id": key},
        {"$inc": {"count": 1}, "$setOnInsert": {"expiresAt": datetime.now(timezone.utc) + timedelta(days=2)}},
        upsert=True, return_document=True,
    )
    return doc["count"] <= limit


async def usage_count(db, key):
    doc = await db.usage.find_one({"_id": key})
    return doc["count"] if doc else 0


def parse_amount(v):
    if isinstance(v, bool) or v is None:
        return 0
    if isinstance(v, (int, float)):
        return round(v) if v > 0 else 0
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("inr", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|lpa|l\b|crores?|cr\b|k\b)?", s)
    if not m:
        return 0
    n = float(m.group(1))
    u = m.group(2) or ""
    if u.startswith(("lakh", "lac", "lpa")) or u == "l":
        n *= 1e5
    elif u.startswith("cr"):
        n *= 1e7
    elif u == "k":
        n *= 1e3
    return round(n)


def parse_json(content):
    if not content:
        return None
    s = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.M).strip()
    try:
        return json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None


def sanitize(data):
    out = {k: parse_amount(data.get(k)) for k in NUM_KEYS}
    flags = data.get("flags") or []
    if not isinstance(flags, list):
        flags = [flags]
    return {
        "fields": out,
        "company": str(data.get("company") or "")[:120],
        "role": str(data.get("role") or "")[:120],
        "flags": [str(f)[:220] for f in flags if str(f).strip()][:10],
    }


async def _try_model(hc, db, model, messages, headers, deadline):
    """One model, at most one retry (only to drop response_format on HTTP 400).
    Returns (data, status) where status is 'ok' | 'rate_limited' | 'failed' | 'cap'."""
    use_rf = True
    for attempt in range(2):
        if not await bump(db, f"global:{today()}", AI_GLOBAL_PER_DAY):
            return None, "cap"
        payload = {"model": model, "messages": messages, "temperature": 0}
        if use_rf:
            payload["response_format"] = {"type": "json_object"}
        left = deadline - time.monotonic()
        if left < 8:
            return None, "failed"
        try:
            r = await hc.post(OPENROUTER_URL, json=payload, headers=headers, timeout=httpx.Timeout(min(PER_MODEL_TIMEOUT, left), connect=10))
        except httpx.HTTPError as e:
            logger.warning("openrouter %s network error: %s", model, type(e).__name__)
            return None, "failed"
        logger.info("openrouter %s -> %s", model, r.status_code)
        if r.status_code == 429:
            return None, "rate_limited"
        if r.status_code == 400 and use_rf and attempt == 0:
            use_rf = False
            continue
        if r.status_code != 200:
            return None, "failed"
        try:
            body = r.json()
        except ValueError:
            return None, "failed"
        if not isinstance(body, dict):
            return None, "failed"
        if body.get("error"):
            code = str((body["error"] or {}).get("code"))
            logger.info("openrouter %s body error code %s", model, code)
            return None, "rate_limited" if code == "429" else "failed"
        try:
            data = parse_json(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            data = None
        if isinstance(data, dict):
            return {**sanitize(data), "model": model}, "ok"
        return None, "failed"
    return None, "failed"


async def _call(db, models, messages, referer):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None, NOT_CONFIGURED_MSG
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "Offer Decode"}
    if referer:
        headers["HTTP-Referer"] = referer
    statuses = []
    deadline = time.monotonic() + CHAIN_DEADLINE_SECONDS
    async with httpx.AsyncClient() as hc:
        for model in models:  # any failure (429, 5xx, 4xx, timeout, bad JSON) -> next model
            data, status = await _try_model(hc, db, model, messages, headers, deadline)
            if status == "ok":
                return data, None
            if status == "cap":
                return None, LIMIT_MSG
            statuses.append(status)
    if statuses and all(s == "rate_limited" for s in statuses):
        return None, LIMIT_MSG
    return None, UNAVAILABLE_MSG


async def extract(db, ip, cache_key, messages, models, referer):
    cached = await db.ai_cache.find_one({"_id": cache_key})
    if cached:
        return {"ok": True, "cached": True, **cached["data"]}
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return {"ok": False, "message": NOT_CONFIGURED_MSG}
    if await usage_count(db, f"global:{today()}") >= AI_GLOBAL_PER_DAY:
        return {"ok": False, "message": LIMIT_MSG}
    if not await bump(db, f"ip:{today()}:{ip}", AI_PER_IP_PER_DAY):
        return {"ok": False, "message": LIMIT_MSG}
    data, err = await _call(db, models, messages, referer)
    if err:
        return {"ok": False, "message": err}
    await db.ai_cache.replace_one(
        {"_id": cache_key}, {"_id": cache_key, "data": data, "createdAt": datetime.now(timezone.utc)}, upsert=True
    )
    return {"ok": True, "cached": False, **data}


def text_messages(text):
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Offer letter text:\n\n{text}"}]


def image_messages(data_urls):
    parts = [{"type": "text", "text": SYSTEM_PROMPT + "\n\nThe offer letter is in the attached image(s)."}]
    parts += [{"type": "image_url", "image_url": {"url": u}} for u in data_urls]
    return [{"role": "user", "content": parts}]
