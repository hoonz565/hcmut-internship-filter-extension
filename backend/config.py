"""
config.py
---------
Centralised configuration loaded from the `.env` file.
All other modules import from here — never read `os.environ` directly.
"""

import os
from dotenv import load_dotenv

# Load variables from .env (silently ignored if the file doesn't exist,
# so real environment variables in production still take effect)
load_dotenv()


def _require(key: str) -> str:
    """Return the value of an env var, raising a clear error if missing."""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: '{key}'. "
            "Did you copy .env.example to .env and fill it in?"
        )
    return value


# ── Gemini ────────────────────────────────────────────────────
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ── MongoDB ───────────────────────────────────────────────────
MONGO_URI: str = _require("MONGO_URI")
DB_NAME: str = os.getenv("DB_NAME", "hcmut_internship")
COLLECTION_NAME: str = "classifications"

# ── Server ────────────────────────────────────────────────────
# Origins allowed to call the API.
# "chrome-extension://*" covers any installed extension.
CORS_ORIGINS: list[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "chrome-extension://",  # prefix — handled via regex in main.py
]
