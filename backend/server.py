import base64
import io
import ipaddress
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, HTTPException, Request, UploadFile
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import ai_extract  # noqa: E402
import pdf_scan  # noqa: E402
from decoder import decode  # noqa: E402
from us_decoder import INPUT_KEYS_US, decode_us  # noqa: E402
from us_states import STATES  # noqa: E402
from flag_guide import enrich  # noqa: E402
from quickscan import clause_flags, quick_scan  # noqa: E402

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Offer Decode")
api = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # never log request headers/keys

# ---- RATE LIMIT: shareable report creation ----
REPORTS_PER_IP_PER_DAY = 10
REPORT_TTL_DAYS = 90
MAX_TEXT = 20000
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 4
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
INPUT_KEYS = ["ctc", "basic", "hra", "employerPF", "gratuity", "variablePay", "joiningBonus", "esopsPerYear", "otherNonCash", "employeePF", "profTax"]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: str = Field(alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc)

    def to_mongo(self):
        return self.model_dump(by_alias=True)


class ReportDoc(BaseDocument):
    input: Dict[str, Any]
    clauseFlags: List[str] = []
    notes: str = ""
    company: str = ""
    role: str = ""
    source: str = "manual"
    country: str = "in"
    result: Dict[str, Any]
    createdAt: datetime
    expiresAt: datetime


class DecodeRequest(BaseModel):
    input: Dict[str, Any]
    clauseFlags: List[str] = []
    notes: str = ""
    country: str = "in"


class ReportCreate(DecodeRequest):
    company: str = ""
    role: str = ""
    source: str = "manual"


class TextRequest(BaseModel):
    text: str
    country: str = "in"


CF_NETS = [ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22", "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32",
    "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32")]


def _is_proxy(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_private or a.is_loopback or any(a in n for n in CF_NETS)


def client_ip(request: Request):
    """Real client IP: walk X-Forwarded-For from the right (spoofed entries sit on the left),
    dropping the load balancer's own hop and any Cloudflare/private hops."""
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if len(hops) > 1:
        hops = hops[:-1]
    for ip in reversed(hops):
        if not _is_proxy(ip):
            return ip
    return hops[0] if hops else (request.client.host if request.client else "unknown")


def referer(request: Request):
    return os.environ.get("APP_PUBLIC_URL", "").strip() or request.headers.get("origin", "")


def norm_country(c):
    return "us" if c == "us" else "in"


def clean_input(raw, country="in"):
    if country == "us":
        out = {k: raw.get(k) for k in INPUT_KEYS_US if raw.get(k) not in (None, "")}
        st = str(raw.get("state") or "").strip().upper()
        if st in STATES:
            out["state"] = st
        return out
    out = {k: raw.get(k) for k in INPUT_KEYS if raw.get(k) not in (None, "")}
    if raw.get("gratuityInCTC") is False:
        out["gratuityInCTC"] = False
    return out


def run_decode(req: DecodeRequest):
    country = norm_country(req.country)
    texts = [t.strip()[:220] for t in req.clauseFlags if t and t.strip()][:12]
    texts += [t for t in clause_flags(req.notes[:5000]) if t not in texts]
    inp = {**clean_input(req.input, country), "textFlags": [{"level": "warn", "text": t, "source": "clause"} for t in texts]}
    if country == "us":
        result = decode_us(inp)
    else:
        result = decode(inp)
    result["country"] = country
    merged = []
    for f in map(enrich, result["flags"]):
        twin = next((m for m in merged if m["why"] == f["why"]), None) if f["source"] == "clause" else None
        if twin:
            twin["letter"] = (twin.get("letter", "") + "; " if twin.get("letter") else "") + f["text"]
            twin["level"] = "warn"
        else:
            merged.append(f)
    result["flags"] = merged
    return result


@api.get("/")
async def root():
    return {"app": "Offer Decode", "ok": True}


@api.get("/states")
async def states():
    """US state list for the selector (name + whether it taxes wages)."""
    return {"states": [{"code": c, "name": s["name"], "noTax": bool(s.get("none"))} for c, s in STATES.items()]}


@api.get("/limits")
async def limits(request: Request):
    day = ai_extract.today()
    ip_used = await ai_extract.usage_count(db, f"ip:{day}:{client_ip(request)}")
    g_used = await ai_extract.usage_count(db, f"global:{day}")
    return {
        "aiConfigured": bool(os.environ.get("OPENROUTER_API_KEY", "").strip()),
        "ipRemaining": max(0, ai_extract.AI_PER_IP_PER_DAY - ip_used),
        "globalAvailable": g_used < ai_extract.AI_GLOBAL_PER_DAY,
    }


@api.post("/decode")
async def decode_offer(req: DecodeRequest):
    return run_decode(req)


@api.post("/quickscan")
async def quickscan(req: TextRequest):
    return quick_scan(req.text[:MAX_TEXT])


@api.post("/extract/text")
async def extract_text(req: TextRequest, request: Request):
    country = norm_country(req.country)
    text = req.text.strip()[:MAX_TEXT]
    if len(text) < 40:
        raise HTTPException(400, "Paste a bit more of the offer letter (at least a few lines).")
    key = f"t{country[0]}:" + ai_extract.text_hash(" ".join(text.split()))
    return await ai_extract.extract(db, client_ip(request), key, ai_extract.text_messages(text, country), ai_extract.TEXT_MODELS, referer(request), country)


@api.post("/extract/pdf")
async def extract_pdf(request: Request, file: UploadFile = File(...), country: str = "in"):
    country = norm_country(country)
    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(400, "PDF is larger than 10 MB.")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:20]).strip()
    except Exception:
        raise HTTPException(400, "Couldn't read that PDF. Try pasting the text or uploading images instead.")
    if len(text) >= 40:
        text = text[:MAX_TEXT]
        key = f"t{country[0]}:" + ai_extract.text_hash(" ".join(text.split()))
        res = await ai_extract.extract(db, client_ip(request), key, ai_extract.text_messages(text, country), ai_extract.TEXT_MODELS, referer(request), country)
        return {**res, "text": text}
    # Scanned PDF (no usable text layer): render pages and read them with the vision models.
    urls = pdf_scan.render_pdf_pages(data)
    if not urls:
        raise HTTPException(400, "Couldn't read that PDF. Try uploading page photos instead.")
    key = f"p{country[0]}:" + ai_extract.text_hash(data)
    res = await ai_extract.extract(db, client_ip(request), key, ai_extract.image_messages(urls, country), ai_extract.IMAGE_MODELS, referer(request), country)
    return {**res, "scanned": True, "text": ""}


@api.post("/extract/images")
async def extract_images(request: Request, files: List[UploadFile] = File(...), country: str = "in"):
    country = norm_country(country)
    if not files or len(files) > MAX_IMAGES:
        raise HTTPException(400, f"Upload 1 to {MAX_IMAGES} images.")
    urls, blobs = [], []
    for f in files:
        ctype = (f.content_type or "").lower()
        if ctype not in IMAGE_TYPES:
            raise HTTPException(400, "Only JPG, PNG or WEBP images are supported.")
        b = await f.read()
        if len(b) > MAX_IMAGE_BYTES:
            raise HTTPException(400, "Each image must be under 5 MB.")
        blobs.append(b)
        urls.append(f"data:{ctype};base64,{base64.b64encode(b).decode()}")
    key = f"i{country[0]}:" + ai_extract.text_hash(*blobs)
    return await ai_extract.extract(db, client_ip(request), key, ai_extract.image_messages(urls, country), ai_extract.IMAGE_MODELS, referer(request), country)


@api.post("/reports")
async def create_report(req: ReportCreate, request: Request):
    country = norm_country(req.country)
    if country == "us":
        if not req.input.get("baseSalary"):
            raise HTTPException(400, "A base salary is needed to save a report.")
    elif not req.input.get("ctc"):
        raise HTTPException(400, "A CTC is needed to save a report.")
    if not await ai_extract.bump(db, f"report:{ai_extract.today()}:{client_ip(request)}", REPORTS_PER_IP_PER_DAY):
        raise HTTPException(429, "You've saved 10 reports today - try again tomorrow.")
    now = datetime.now(timezone.utc)
    doc = ReportDoc(
        _id=secrets.token_urlsafe(24), input=clean_input(req.input, country), clauseFlags=req.clauseFlags[:12],
        notes=req.notes[:5000], company=req.company[:120], role=req.role[:120], source=req.source[:20], country=country,
        result=run_decode(req), createdAt=now, expiresAt=now + timedelta(days=REPORT_TTL_DAYS),
    )
    await db.reports.insert_one(doc.to_mongo())
    return {"id": doc.id, "expiresAt": doc.expiresAt.isoformat()}


@api.get("/reports/{rid}")
async def get_report(rid: str):
    raw = await db.reports.find_one({"_id": rid})
    if not raw:
        raise HTTPException(404, "Report not found or expired.")
    doc = ReportDoc.from_mongo(raw)
    if doc.expiresAt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(404, "Report not found or expired.")
    out = doc.model_dump()
    out["createdAt"] = doc.createdAt.isoformat()
    out["expiresAt"] = doc.expiresAt.isoformat()
    return out


app.include_router(api)
app.add_middleware(
    CORSMiddleware, allow_credentials=False,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "https://offerdecoder.online").split(",") if o.strip()], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
async def indexes():
    await db.ai_cache.create_index("createdAt", expireAfterSeconds=ai_extract.CACHE_TTL_SECONDS)
    await db.reports.create_index("expiresAt", expireAfterSeconds=0)
    await db.usage.create_index("expiresAt", expireAfterSeconds=0)


@app.on_event("shutdown")
async def shutdown():
    client.close()



# --- Single-service hosting: serve the built frontend (added for free hosting) ---
from starlette.responses import FileResponse  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

BUILD_DIR = ROOT_DIR.parent / "frontend" / "build"
if BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=BUILD_DIR / "static"), name="static")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        candidate = BUILD_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(BUILD_DIR / "index.html")
