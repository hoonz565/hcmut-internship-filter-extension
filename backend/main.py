"""
main.py
-------
FastAPI application entry point.

Startup / Shutdown
------------------
  - Connects to MongoDB via motor on startup; stores the database handle on
    `app.state.db` so all routers can access it via `request.app.state.db`.
  - Closes the motor client gracefully on shutdown.

CORS
----
  The extension runs as `chrome-extension://<id>/*`, which is an opaque origin.
  We use a custom `CORSMiddleware` regex pattern to allow all chrome-extension
  origins alongside localhost origins used during development.

Usage
-----
  cd backend
  uvicorn main:app --reload --port 8000
"""

import logging
import re
from contextlib import asynccontextmanager

import motor.motor_asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.v1.classify import router as classify_router
from config import COLLECTION_NAME, DB_NAME, MONGO_URI

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan: MongoDB connect / disconnect ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the motor client lifecycle."""
    logger.info("Connecting to MongoDB at %s …", MONGO_URI)
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    app.state.db = db

    # Ensure a unique index on company_name for fast cache lookups and upserts
    try:
        await db[COLLECTION_NAME].create_index("company_name", unique=True)
        logger.info("MongoDB index on 'company_name' ensured.")
    except Exception as exc:
        logger.warning("Could not create index (may already exist): %s", exc)

    logger.info("MongoDB connected. Database: '%s'", DB_NAME)
    yield  # ← server is running

    logger.info("Shutting down. Closing MongoDB connection …")
    client.close()


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="HCMUT Internship — JD Classifier API",
    description=(
        "Proxy server that classifies company job descriptions using Google Gemini "
        "and caches results in MongoDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS middleware ───────────────────────────────────────────────────────────
# Standard origins for local development
_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"chrome-extension://.*",  # allow any installed extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(classify_router, prefix="/api/v1")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health_check():
    """Quick liveness probe — useful for Docker / deployment health checks."""
    return {"status": "ok", "service": "jd-classifier"}


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
