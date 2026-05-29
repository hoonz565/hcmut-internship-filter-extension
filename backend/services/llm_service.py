"""
services/llm_service.py
-----------------------
Wrapper around the Google Gemini API using the new `google-genai` SDK.

Migrated from the deprecated `google-generativeai` package to `google.genai`
as the old package no longer receives updates (FutureWarning raised on import).

Public API
----------
  classify_jd(jd_text: str) -> dict
      Sends `jd_text` to Gemini and returns a dict with:
        { "industry_tags": [...], "key_skills": [...] }

  Raises
  ------
  ValueError  — if the model returns an empty or malformed response.
  Exception   — any underlying network / API error.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# ── Initialise the client once at import time ─────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are an IT Recruiter. "
    "Analyze the provided company description or job description (JD). "
    "Classify the main tech industry into 1-2 short tags "
    "(e.g. 'Web', 'AI', 'Mobile', 'Data', 'Embedded', 'Security', 'DevOps', 'Game'). "
    "Extract the top 3-5 technical skills required. "
    "Return ONLY a valid JSON object — no markdown, no extra text — with exactly "
    "two keys: 'industry_tags' (array of strings) and 'key_skills' (array of strings)."
)

# ── Generation config ─────────────────────────────────────────────────────────
_GENERATE_CONFIG = types.GenerateContentConfig(
    system_instruction=_SYSTEM_PROMPT,
    temperature=0.2,           # low temperature → consistent, factual output
    max_output_tokens=256,
    response_mime_type="application/json",  # forces structured JSON output
)


def classify_jd(jd_text: str) -> dict[str, Any]:
    """
    Send `jd_text` to Gemini and parse the JSON response.

    Parameters
    ----------
    jd_text : str
        The raw job description / company description text.

    Returns
    -------
    dict
        ``{ "industry_tags": List[str], "key_skills": List[str] }``

    Raises
    ------
    ValueError
        If the API returns an empty response or the JSON is malformed /
        missing required keys.
    Exception
        Any network or API error from the `google-genai` SDK.
    """
    logger.info("Calling Gemini model '%s' for JD classification.", GEMINI_MODEL)

    # Truncate extremely long JDs to avoid token-limit errors
    truncated_jd = jd_text[:8000] if len(jd_text) > 8000 else jd_text

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=truncated_jd,
        config=_GENERATE_CONFIG,
    )

    # ── Validate the response ─────────────────────────────────────────────────
    if not response.text:
        logger.error("Gemini returned an empty response.")
        raise ValueError("Gemini returned an empty response for the provided JD text.")

    logger.debug("Raw Gemini response: %s", response.text)

    try:
        parsed: dict[str, Any] = json.loads(response.text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON: %s | raw: %s", exc, response.text)
        raise ValueError(
            f"Gemini response was not valid JSON: {response.text[:200]}"
        ) from exc

    # ── Ensure required keys are present ─────────────────────────────────────
    missing = [k for k in ("industry_tags", "key_skills") if k not in parsed]
    if missing:
        raise ValueError(
            f"Gemini response is missing required keys: {missing}. "
            f"Got: {list(parsed.keys())}"
        )

    # Normalise: make sure values are lists of strings
    result = {
        "industry_tags": [str(t) for t in parsed.get("industry_tags", [])],
        "key_skills": [str(s) for s in parsed.get("key_skills", [])],
    }

    logger.info(
        "Classification complete — tags: %s | skills: %s",
        result["industry_tags"],
        result["key_skills"],
    )
    return result
