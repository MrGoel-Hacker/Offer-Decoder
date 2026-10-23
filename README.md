# Offer Decode

Decode Indian and US job offer letters into what they actually pay. Paste the letter text, upload a PDF (scanned PDFs work - pages are read visually), or upload photos of the offer, and Offer Decode pulls out the numbers and shows your real monthly take-home, red-flag clauses and negotiation pointers. You can also save a shareable report link.

Live at **https://offerdecoder.online**

What you get:

- **India: CTC breakdown** - basic, HRA, PF, gratuity, variable pay, joining bonus, ESOPs, other non-cash items, with monthly in-hand from FY 2026-27 new-regime tax math (plain code, not AI)
- **USA: comp breakdown** - base, target bonus, RSUs, signing bonus, 401(k), with monthly take-home from 2026 federal brackets, FICA and state tax (single filer, standard deduction; city/local taxes not included)
- **Scanned PDF support** - pages are rendered in memory (pypdfium2) and read by the vision models
- **Red flags** - bonds, clawbacks, long notice periods, non-competes, probation and vesting gotchas, with what to ask about each
- **Dark and light themes** - toggle in the header, remembered per browser
- **Shareable report** - a link you can send someone, valid for 90 days

Stack: FastAPI + MongoDB (Motor) backend, React 19 (Create React App + craco, Tailwind, shadcn/ui) frontend. AI letter reading uses free OpenRouter models; everything else is plain code so the app keeps working when the AI limit is hit.

## Run locally

You need Python 3.10+, Node 18+ with yarn, and MongoDB (local install or a free Atlas cluster).

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in the values, see below
uvicorn server:app --reload --port 8001
```

API runs at `http://localhost:8001/api` (`/api/` is a health check, `/api/limits` shows AI quota state).

### Frontend (React)

```bash
cd frontend
yarn install
echo 'REACT_APP_BACKEND_URL=http://localhost:8001' > .env
yarn start
```

Opens at `http://localhost:3000`. If `REACT_APP_BACKEND_URL` is unset, the frontend calls a same-origin `/api` - that is how production works, where the FastAPI process also serves the built frontend.

### Production-style run (one process)

```bash
cd frontend && GENERATE_SOURCEMAP=false yarn build && cd ..
cd backend && uvicorn server:app --port 8001
```

The backend serves `frontend/build` itself; open `http://localhost:8001`.

## Environment variables (`backend/.env.example`)

| Variable | What it is |
| --- | --- |
| `MONGO_URL` | MongoDB connection string (`mongodb://localhost:27017` locally, or an Atlas URI) |
| `DB_NAME` | Database name, e.g. `offer_decode` |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API cross-origin. Production uses `https://offerdecoder.online` with credentials off. Same-origin calls (frontend served by the backend) do not use CORS at all |
| `OPENROUTER_API_KEY` | OpenRouter key for AI offer-letter reading (free models only). Leave empty to run the app without AI |
| `APP_PUBLIC_URL` | Public site URL, sent to OpenRouter as the HTTP-Referer header |
| `GOOGLE_CLIENT_ID` | Google OAuth web client ID for sign-in (public value, embedded in the frontend too). Sign-in returns 503 until set |

Never commit a real `.env`; it is gitignored.

## How the AI limits work

AI reading (text, PDF text layer and image OCR) goes through OpenRouter **free models only** - no paid fallback - with these guardrails (all in `backend/ai_extract.py`):

- **Per-IP limit:** 5 AI reads per IP per day (`AI_PER_IP_PER_DAY`).
- **Global cap:** 45 AI calls per day across all users (`AI_GLOBAL_PER_DAY`), kept just under OpenRouter's free-tier 50/day so the key is never billed.
- **24-hour cache:** an identical letter returns the cached result and does not count again.
- **Fallback chain:** if one free model is rate-limited, times out or returns bad JSON, the next model in the chain is tried.
- **Graceful degradation:** when the limit is reached or no key is configured, the app tells the user and keeps working - Quick scan (offline regex heuristics, beta - verify the numbers) and manual entry need no AI, and the tax math is pure code.
- **Saved reports:** 10 new shareable reports per IP per day; each report link expires after 90 days.

## Running the tests

Tests live in `backend/tests/` and use pytest with pytest-xdist (settings pinned in `backend/pytest.ini`):

```bash
cd backend
pip install pytest pytest-xdist requests
uvicorn server:app --port 8001 &          # API tests need a live backend
REACT_APP_BACKEND_URL=http://localhost:8001 pytest
```

- `test_offer_decode_api.py` - decode math, quick scan, AI-extract behaviour with no key, shareable reports and rate limiting; runs against the live backend in `REACT_APP_BACKEND_URL`.
- `test_ai_fallback.py` - the AI model fallback chain with a mocked OpenRouter and a throwaway Mongo database (needs `MONGO_URL` in `backend/.env`).

Run serially with `pytest -n 0` if you ever need to.
