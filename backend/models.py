"""
models.py
---------
Pydantic v2 models used across the application.

  ClassifyRequest   — the JSON body sent by the Chrome Extension
  CompanyClassification — the schema stored in MongoDB and returned to clients
  ClassifyResponse  — the HTTP response body (subset of CompanyClassification)
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Payload sent by the Chrome Extension content script."""

    company_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable company name or unique portal ID.",
        examples=["FPT Software"],
    )
    jd_text: str = Field(
        ...,
        min_length=10,
        description="Raw job description / company description text to analyse.",
        examples=["We are looking for a Python engineer with ML experience..."],
    )


class CompanyClassification(BaseModel):
    """
    Document schema stored in the `classifications` MongoDB collection.

    The `company_name` field has a unique index to guarantee at-most-one
    document per company and enable efficient upserts.
    """

    company_name: str = Field(..., description="Unique company identifier / name.")
    industry_tags: List[str] = Field(
        default_factory=list,
        description="1–2 short tech-industry labels, e.g. ['AI', 'Machine Learning'].",
    )
    key_skills: List[str] = Field(
        default_factory=list,
        description="Top 3–5 technical skills extracted from the JD.",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the last classification (cache update).",
    )


class ClassifyResponse(BaseModel):
    """Returned to the Chrome Extension on both cache-hit and cache-miss paths."""

    company_name: str
    industry_tags: List[str]
    key_skills: List[str]
    updated_at: datetime
    cached: bool = Field(
        default=False,
        description="True when the result was served from the MongoDB cache.",
    )
