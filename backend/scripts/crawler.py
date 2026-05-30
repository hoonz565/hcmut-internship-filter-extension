"""
scripts/crawler.py
------------------
2-Step async crawler for the HCMUT Internship portal:

  STEP 1 — iter_companies()
    GET ALL_COMPANIES_API_URL → parse "items" array → yield (_id, fullname)

  STEP 2 — process_company()
    GET COMPANY_DETAIL_API_BASE + _id → regex-find first PDF/DOCX link
    → download → extract text → Gemini classification → MongoDB upsert

Run from the `backend/` directory:
    python scripts/crawler.py
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
import docx          # python-docx
import fitz          # PyMuPDF
import motor.motor_asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap: resolve backend/ root so sibling modules (config) can be imported
# when the script is run directly as `python scripts/crawler.py`.
# ─────────────────────────────────────────────────────────────────────────────
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_SCRIPT_DIR)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

from config import GEMINI_API_KEY, GEMINI_MODEL, MONGO_URI, DB_NAME, COLLECTION_NAME  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("crawler")

# ─────────────────────────────────────────────────────────────────────────────
# ① CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# STEP 1: replace with the actual paginated company-list endpoint you copied
# from the browser's Network tab.  Example:
#   "https://internship.cse.hcmut.edu.vn/home/companies?page=1&limit=999"
ALL_COMPANIES_API_URL = "https://internship.cse.hcmut.edu.vn/home/company/all?t=1780072873951&condition="

# STEP 2: company detail endpoint — _id is appended at runtime
COMPANY_DETAIL_API_BASE = "https://internship.cse.hcmut.edu.vn/home/company/id/"

PORTAL_ORIGIN = "https://internship.cse.hcmut.edu.vn"

# Delay between each company to avoid hammering the portal AND respect Gemini
# rate limits (both concerns are addressed by a single shared sleep).
ITERATION_DELAY_SECONDS = 1.5

# Gemini model override for the crawler (falls back to GEMINI_MODEL from .env)
_CRAWLER_MODEL = os.getenv("CRAWLER_GEMINI_MODEL", GEMINI_MODEL)

# ─────────────────────────────────────────────────────────────────────────────
# ② GEMINI CLIENT
# ─────────────────────────────────────────────────────────────────────────────
_gemini_client = genai.Client(api_key=GEMINI_API_KEY)

_CLASSIFY_PROMPT = (
    "Analyze this IT Job Description. "
    "Classify the main tech industry into 1-2 short tags "
    "(e.g. 'Web', 'AI', 'Mobile', 'Data', 'Embedded', 'DevOps'). "
    "Extract the top 3-5 technical skills required. "
    "Return ONLY valid JSON with exactly two keys: "
    "'industry_tags' (list of strings) and 'key_skills' (list of strings)."
)

_CLASSIFY_CONFIG = types.GenerateContentConfig(
    system_instruction=_CLASSIFY_PROMPT,
    temperature=0.2,
    max_output_tokens=256,
    response_mime_type="application/json",
)

# ─────────────────────────────────────────────────────────────────────────────
# ③ STEP 1 — Company list
# ─────────────────────────────────────────────────────────────────────────────

async def iter_companies(session: aiohttp.ClientSession):
    """
    Async generator — yields dicts: {"id": str, "name": str}.

    GETs ALL_COMPANIES_API_URL, parses the JSON, and iterates over the
    "items" array.  Each item is expected to have "_id" and "fullname".
    """
    if ALL_COMPANIES_API_URL == "PASTE_YOUR_COPIED_URL_HERE":
        logger.error(
            "ALL_COMPANIES_API_URL has not been set. "
            "Copy the real URL from the browser's Network tab and paste it "
            "into the constant at the top of this file."
        )
        return

    logger.info("Fetching company list from: %s", ALL_COMPANIES_API_URL)
    try:
        async with session.get(
            ALL_COMPANIES_API_URL,
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if not resp.ok:
                logger.error(
                    "Company list API returned HTTP %s — cannot continue.", resp.status
                )
                return
            payload = await resp.json(content_type=None)
    except Exception as exc:
        logger.error("Failed to fetch company list: %s", exc)
        return

    # Support both { "items": [...] } and a bare list at the root
    items: list = payload.get("items") or payload.get("data") or (
        payload if isinstance(payload, list) else []
    )

    if not items:
        logger.warning("Company list response contained no items.")
        return

    logger.info("Found %d companies.", len(items))
    for item in items:
        company_id   = str(item.get("_id", "")).strip()
        company_name = str(item.get("fullname", company_id)).strip()
        if company_id:
            yield {"id": company_id, "name": company_name}
        else:
            logger.warning("Skipping item with no _id: %s", item)


# ─────────────────────────────────────────────────────────────────────────────
# ④ STEP 2 — File link extraction from structured JSON
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_file_link(
    session: aiohttp.ClientSession, company_id: str
) -> str | None:
    """
    GET the company detail endpoint, parse the JSON response, and return the
    direct URL of the last file in ``item.internshipFiles``.

    The portal returns structured data like:
        { "item": { "internshipFiles": [ {"path": "/company/.../jd.pdf"}, ... ] } }

    We take the **last** entry (most recently uploaded JD) and prepend the
    portal origin to form an absolute URL.

    Returns the absolute file URL, or None if no files are found.
    """
    detail_url = COMPANY_DETAIL_API_BASE + company_id
    logger.info("  [Step 2] Fetching detail: %s", detail_url)

    try:
        async with session.get(
            detail_url,
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if not resp.ok:
                logger.warning(
                    "  Detail API returned HTTP %s for id=%s.", resp.status, company_id
                )
                return None
            data = await resp.json(content_type=None)
    except Exception as exc:
        logger.error("  Failed to fetch detail for id=%s: %s", company_id, exc)
        return None

    # Navigate: data["item"]["internshipFiles"] -> list of {"path": "...", ...}
    item            = data.get("item") or {}
    internship_files: list = item.get("internshipFiles") or []

    if not internship_files:
        logger.warning("  No internshipFiles found for id=%s.", company_id)
        return None

    # Take the last element — the most recently uploaded JD
    last_file = internship_files[-1]
    file_path = last_file.get("path", "").strip()

    if not file_path:
        logger.warning("  internshipFiles entry has no 'path' for id=%s.", company_id)
        return None

    # Ensure the path starts with '/' before prepending the origin
    if not file_path.startswith("/"):
        file_path = "/" + file_path

    file_url = f"{PORTAL_ORIGIN}{file_path}"
    logger.info("  Found file: %s", file_url)
    return file_url


# ─────────────────────────────────────────────────────────────────────────────
# ⑤ File download & text extraction
# ─────────────────────────────────────────────────────────────────────────────

async def download_bytes(
    session: aiohttp.ClientSession, url: str
) -> bytes | None:
    """Download a file into memory; returns raw bytes or None on failure."""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if not resp.ok:
                logger.warning("  Download failed — HTTP %s: %s", resp.status, url)
                return None
            return await resp.read()
    except Exception as exc:
        logger.warning("  Download error for %s: %s", url, exc)
        return None


def _ext(url: str) -> str:
    """Return the lowercase file extension from a URL path (e.g. 'pdf')."""
    return urlparse(url).path.rsplit(".", 1)[-1].lower()


def extract_text(data: bytes, file_ext: str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    try:
        if file_ext == "pdf":
            doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip()
        elif file_ext in ("docx", "doc"):
            document = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in document.paragraphs).strip()
    except Exception as exc:
        logger.warning("  Text extraction failed (%s): %s", file_ext, exc)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# ⑥ AI Classification
# ─────────────────────────────────────────────────────────────────────────────

_FALLBACK_RESULT: dict = {"industry_tags": ["Other"], "key_skills": []}


def _extract_json(raw: str) -> str:
    """
    Robustly pull a JSON object out of a potentially chatty LLM response.

    Strategy (in order):
      1. If the response contains a ```json ... ``` code fence, extract its body.
      2. Otherwise, slice from the first '{' to the last '}' (covers bare JSON
         preceded or followed by conversational text).
      3. If neither delimiter is found, return the stripped original string and
         let json.loads() raise a clear error.
    """
    text = raw.strip()

    # Strategy 1: markdown code fence
    if "```" in text:
        # Find the opening fence (```json or plain ```)
        start = text.find("```")
        # Skip past the fence line (```json\n or ```\n)
        inner_start = text.find("\n", start)
        if inner_start != -1:
            # Find the closing fence
            inner_end = text.find("```", inner_start)
            if inner_end != -1:
                return text[inner_start:inner_end].strip()

    # Strategy 2: brace slicing
    brace_open  = text.find("{")
    brace_close = text.rfind("}")
    if brace_open != -1 and brace_close > brace_open:
        return text[brace_open : brace_close + 1]

    # Strategy 3: return as-is (json.loads will surface the error)
    return text


def classify_text(jd_text: str) -> dict:
    """
    Classify `jd_text` with Gemini.

    Always returns a dict with keys 'industry_tags' and 'key_skills'.
    On any failure (API error, empty response, bad JSON, missing keys) the
    fallback ``{"industry_tags": ["Other"], "key_skills": []}`` is returned
    so the crawler never stalls on an LLM quirk.
    """
    truncated = jd_text[:8000]

    # ── API call ──────────────────────────────────────────────────────────────
    try:
        response = _gemini_client.models.generate_content(
            model=_CRAWLER_MODEL,
            contents=truncated,
            config=_CLASSIFY_CONFIG,   # includes response_mime_type="application/json"
        )
    except Exception as exc:
        logger.error("  Gemini API error: %s — using fallback.", exc)
        return _FALLBACK_RESULT

    # ── Empty / safety-filtered response ─────────────────────────────────────
    if not response.text or not response.text.strip():
        logger.warning("  Gemini returned empty text (safety filter?) — using fallback.")
        return _FALLBACK_RESULT

    # ── Extract JSON from potentially chatty output ───────────────────────────
    json_str = _extract_json(response.text)

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error(
            "  JSON parse failed (%s). Raw (200 chars): %s — using fallback.",
            exc, response.text[:200],
        )
        return _FALLBACK_RESULT

    # ── Validate & normalise ──────────────────────────────────────────────────
    if not isinstance(parsed, dict):
        logger.error("  Parsed JSON is not a dict (got %s) — using fallback.", type(parsed))
        return _FALLBACK_RESULT

    # Gracefully handle missing keys by defaulting to empty lists
    industry_tags = [str(t) for t in parsed.get("industry_tags") or ["Other"]]
    key_skills    = [str(s) for s in parsed.get("key_skills")    or []]

    result = {"industry_tags": industry_tags, "key_skills": key_skills}
    logger.info("  Classified — tags: %s | skills: %s", industry_tags, key_skills)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ⑦ MongoDB upsert
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_classification(collection, company_id: str, company_name: str, result: dict) -> None:
    """Upsert the classification document keyed on company_name."""
    document = {
        "company_id":    company_id,
        "company_name":  company_name,
        "industry_tags": result["industry_tags"],
        "key_skills":    result["key_skills"],
        "updated_at":    datetime.now(timezone.utc),
    }
    await collection.update_one(
        {"company_name": company_name},
        {"$set": document},
        upsert=True,
    )
    logger.info(
        "  DB upsert OK — tags: %s | skills: %s",
        result["industry_tags"],
        result["key_skills"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# ⑧ Per-company pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def process_company(
    session: aiohttp.ClientSession,
    collection,
    company_id: str,
    company_name: str,
) -> None:
    """
    Full 2-step pipeline for one company:
      Step 2a: fetch detail & extract file link from JSON
      Step 2b: download file bytes
      Step 2c: extract plain text (PDF/DOCX)
      Step 2d: Gemini classification (always returns a result, never None)
      Step 2e: MongoDB upsert
    """
    logger.info("─── %s (id=%s)", company_name, company_id)

    # ── 2a: Get the file URL from the detail page ─────────────────────────────
    file_url = await fetch_file_link(session, company_id)
    if not file_url:
        logger.warning("  Skipping %s — no JD file found.", company_name)
        return

    # ── 2b: Download ──────────────────────────────────────────────────────────
    logger.info("  Downloading: %s", file_url)
    data = await download_bytes(session, file_url)
    if not data:
        logger.warning("  Skipping %s — download failed.", company_name)
        return

    # ── 2c: Extract text ──────────────────────────────────────────────────────
    file_ext = _ext(file_url)
    jd_text  = extract_text(data, file_ext)

    if not jd_text.strip():
        logger.warning("  Skipping %s — no text extracted from %s.", company_name, file_ext)
        return

    logger.info("  Extracted %d characters. Classifying …", len(jd_text))

    # ── 2d: Gemini classification ─────────────────────────────────────────────
    result = classify_text(jd_text)   # always returns a dict, never None

    # ── 2e: Upsert to MongoDB ─────────────────────────────────────────────────
    await upsert_classification(collection, company_id, company_name, result)


# ─────────────────────────────────────────────────────────────────────────────
# ⑨ Main
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    # MongoDB
    logger.info("Connecting to MongoDB …")
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db         = mongo_client[DB_NAME]
    collection = db[COLLECTION_NAME]
    await collection.create_index("company_name", unique=True)
    logger.info("MongoDB ready — %s.%s", DB_NAME, COLLECTION_NAME)

    connector = aiohttp.TCPConnector(ssl=False)  # portal may use self-signed cert
    async with aiohttp.ClientSession(connector=connector) as session:
        processed = skipped = failed = 0

        async for company in iter_companies(session):
            company_id   = company["id"]
            company_name = company["name"]

            existing = await collection.find_one({"company_id": company_id})
            if existing and "Other" not in existing.get("industry_tags", []):
                logger.info("  Skipping %s — Already successfully classified.", company_name)
                skipped += 1
                continue

            try:
                await process_company(session, collection, company_id, company_name)
                processed += 1
            except Exception as exc:
                logger.error(
                    "Unhandled error for %s (id=%s): %s", company_name, company_id, exc
                )
                failed += 1

            # ── Rate-limit guard: protects both the portal and Gemini API ──────
            logger.debug("  Sleeping %.1fs …", ITERATION_DELAY_SECONDS)
            await asyncio.sleep(ITERATION_DELAY_SECONDS)

    mongo_client.close()
    logger.info(
        "Done. Processed: %d | Skipped: %d | Failed: %d | Total: %d",
        processed, skipped, failed, processed + skipped + failed,
    )


if __name__ == "__main__":
    asyncio.run(main())
