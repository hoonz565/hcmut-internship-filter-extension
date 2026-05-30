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
        "Proxy server that provides company job descriptions and tags "
        "fetched from MongoDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS middleware ───────────────────────────────────────────────────────────
# Standard origins for local development
_ALLOWED_ORIGINS = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
# (No sub-routers currently needed)


@app.get("/api/all_tags", tags=["Data"])
async def get_all_tags(request: Request):
    """Return a dictionary mapping company names to their tags."""
    try:
        db = request.app.state.db
        classifications = await db[COLLECTION_NAME].find({}).to_list(length=None)
        
        result = {}
        for doc in classifications:
            result[doc["company_name"]] = doc.get("industry_tags", [])
            
        return result
    except Exception as e:
        logger.error("Error fetching all tags: %s", e, exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/all_tags_by_id", tags=["Data"])
async def get_all_tags_by_id(request: Request):
    """Return a dictionary mapping company IDs to their tags."""
    try:
        db = request.app.state.db
        classifications = await db[COLLECTION_NAME].find({}).to_list(length=None)
        
        result = {}
        for doc in classifications:
            # Use the stored company_id, or stringified _id as fallback
            cid = doc.get("company_id")
            if not cid:
                cid = str(doc["_id"])
            result[cid] = doc.get("industry_tags", [])
            
        return result
    except Exception as e:
        logger.error("Error fetching tags by ID: %s", e, exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health_check():
    """Quick liveness probe — useful for Docker / deployment health checks."""
    return {"status": "ok", "service": "jd-classifier"}


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
