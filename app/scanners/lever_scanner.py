"""Scans Lever job boards via their public read-only JSON API.

https://api.lever.co/v0/postings/{company-slug}?mode=json
"""
import re

import requests

from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import wait_for_slot

API_TEMPLATE = "https://api.lever.co/v0/postings/{slug}?mode=json"
SLUG_PATTERN = re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)")


def extract_company_slug(url: str) -> str | None:
    match = SLUG_PATTERN.search(url or "")
    return match.group(1) if match else None


class LeverScanner(BaseScanner):
    name = "lever"

    def scan_company(self, company: Company) -> ScanResult:
        slug = (
            getattr(company, "board_id", None)
            or extract_company_slug(company.career_url)
            or extract_company_slug(company.internship_url)
        )
        if not slug:
            return ScanResult([], status="manual_review_required", error_message="No Lever company slug — set board_id in companies.yaml or provide a jobs.lever.co URL")

        wait_for_slot(company.name)
        api_url = API_TEMPLATE.format(slug=slug)

        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            scanner_logger.warning(f"[lever] {company.name}: {exc}")
            return ScanResult([], status="error", error_message=str(exc))
        except ValueError as exc:
            return ScanResult([], status="error", error_message=f"Invalid JSON: {exc}")

        candidates = []
        for job in data:
            categories = job.get("categories", {}) or {}
            candidates.append(
                OpportunityCandidate(
                    company_name=company.name,
                    job_title=job.get("text", ""),
                    job_url=job.get("hostedUrl", ""),
                    location=categories.get("location", ""),
                    department=categories.get("team", ""),
                    job_type=categories.get("commitment", ""),
                    description=job.get("descriptionPlain", "") or job.get("description", ""),
                    source_platform="lever",
                    source_url=api_url,
                )
            )

        return ScanResult(candidates, status="success")
