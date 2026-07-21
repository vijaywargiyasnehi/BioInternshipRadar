"""Pydantic schemas for validation and API I/O."""
from datetime import datetime

from pydantic import BaseModel, Field


class CompanyIn(BaseModel):
    name: str
    category: str = ""
    career_url: str = ""
    internship_url: str = ""
    platform: str = "unknown"
    board_id: str = ""
    network_contact: str = ""
    priority: str = "Medium"
    active: bool = True
    notes: str = ""
    scan_interval_minutes: int = 15


class CompanyOut(CompanyIn):
    id: int
    last_scanned_at: datetime | None = None
    last_scan_status: str = "never_scanned"
    last_scan_error: str = ""

    model_config = {"from_attributes": True}


class OpportunityCandidate(BaseModel):
    """Normalized opportunity extracted by any scanner, before scoring/dedup."""

    company_name: str
    job_title: str
    job_url: str = ""
    location: str = ""
    remote_status: str = "unknown"
    department: str = ""
    job_type: str = ""
    posted_date: str = ""
    description: str = ""
    source_platform: str = "unknown"
    source_url: str = ""


class OpportunityImportIn(BaseModel):
    """Payload for POST /api/opportunities/import (manual or browser-agent sourced)."""

    company_name: str
    job_title: str
    job_url: str = ""
    location: str = ""
    description: str = ""
    posted_date: str = ""
    source: str = "manual"
    notes: str = ""


class OpportunityOut(BaseModel):
    id: int
    company_name: str
    job_title: str
    job_url: str
    location: str
    remote_status: str
    department: str
    job_type: str
    posted_date: str
    detected_date: datetime
    last_seen_at: datetime
    description: str
    source_platform: str
    source_url: str
    fit_score: int
    fit_score_explanation: str
    matched_keywords: str
    status: str
    notification_sent: bool
    resume_generated: bool
    resume_path: str
    notes: str

    model_config = {"from_attributes": True}


class FitScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    matched_keywords: list[str] = []
    ignored_keywords_hit: list[str] = []
    reasons: list[str] = []
