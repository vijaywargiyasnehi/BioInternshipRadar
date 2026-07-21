"""Searches USAJobs.gov for bioengineering/pharma/biomedical internships.

USAJobs is the official US federal government job board (NIH, FDA, CDC, DoD, etc.).
It requires a free API key — register at https://developer.usajobs.gov

Set in .env:
  USAJOBS_API_KEY=your_key_here
  USAJOBS_EMAIL=your@email.com

Without these, the scanner returns manual_review_required.

To add to companies.yaml:
  - name: "Federal Agencies (USAJobs)"
    category: Federal / Government
    platform: usajobs
    board_id: ""
    priority: High
    active: true
"""
import requests

from app.config import settings
from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger

_API_BASE = "https://data.usajobs.gov/api/search"

# Each search term is issued as a separate API call so we get broad coverage.
_SEARCH_TERMS = [
    "bioengineering intern",
    "biomedical engineering intern",
    "biotechnology intern",
    "pharmaceutical sciences intern",
    "bioinformatics intern",
    "life sciences student trainee",
    "health science intern",
    "medical device intern",
    "regulatory affairs intern",
    "quality engineering intern",
    "process engineering intern",
    "computational biology intern",
    "biomanufacturing intern",
    "biological sciences intern",
]


def _fetch_usajobs(keyword: str, api_key: str, email: str) -> list[dict]:
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": email,
        "Authorization-Key": api_key,
    }
    params = {
        "Keyword": keyword,
        "ResultsPerPage": "50",
        "WhoMayApply": "All",
    }
    resp = requests.get(_API_BASE, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("SearchResult", {}).get("SearchResultItems", [])


class USAJobsScanner(BaseScanner):
    name = "usajobs"

    def scan_company(self, company: Company) -> ScanResult:
        api_key = settings.usajobs_api_key
        email = settings.usajobs_email
        if not api_key or not email:
            return ScanResult(
                [],
                status="manual_review_required",
                error_message=(
                    "USAJobs API credentials not configured. "
                    "Register at https://developer.usajobs.gov then set "
                    "USAJOBS_API_KEY and USAJOBS_EMAIL in your .env file."
                ),
            )

        seen_ids: set[str] = set()
        candidates: list[OpportunityCandidate] = []
        errors = 0

        for term in _SEARCH_TERMS:
            try:
                items = _fetch_usajobs(term, api_key, email)
            except requests.exceptions.RequestException as exc:
                scanner_logger.warning(f"[usajobs] '{term}': {exc}")
                errors += 1
                continue

            for item in items:
                m = item.get("MatchedObjectDescriptor", {})
                job_id = m.get("PositionID", "")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                apply_uris = m.get("ApplyURI") or []
                apply_url = apply_uris[0] if apply_uris else m.get("PositionURI", "")
                start_date = (m.get("PublicationStartDate") or "")[:10]

                candidates.append(
                    OpportunityCandidate(
                        company_name=m.get("OrganizationName", "Federal Agency"),
                        job_title=m.get("PositionTitle", ""),
                        job_url=apply_url,
                        location=m.get("PositionLocationDisplay", ""),
                        posted_date=start_date,
                        description=m.get("QualificationSummary", ""),
                        source_platform="usajobs",
                        source_url=_API_BASE,
                    )
                )

        scanner_logger.info(
            f"[usajobs] {len(candidates)} unique federal postings across {len(_SEARCH_TERMS)} queries "
            f"({errors} query errors)"
        )
        return ScanResult(candidates, status="success")
