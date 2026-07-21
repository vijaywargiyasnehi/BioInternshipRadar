"""Scans Greenhouse job boards via their public read-only JSON API.

Greenhouse exposes https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
for any public job board. We derive {token} from the career_url/internship_url if it
points at boards.greenhouse.io/{token} or job-boards.greenhouse.io/{token}.
"""
import re

import requests

from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import wait_for_slot

API_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
TOKEN_PATTERN = re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([a-zA-Z0-9_-]+)")


def extract_board_token(url: str) -> str | None:
    match = TOKEN_PATTERN.search(url or "")
    return match.group(1) if match else None


class GreenhouseScanner(BaseScanner):
    name = "greenhouse"

    def scan_company(self, company: Company) -> ScanResult:
        token = (
            getattr(company, "board_id", None)
            or extract_board_token(company.career_url)
            or extract_board_token(company.internship_url)
        )
        if not token:
            return ScanResult([], status="manual_review_required", error_message="No Greenhouse board token — set board_id in companies.yaml or provide a boards.greenhouse.io URL")

        wait_for_slot(company.name)
        api_url = API_TEMPLATE.format(token=token)

        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            scanner_logger.warning(f"[greenhouse] {company.name}: {exc}")
            return ScanResult([], status="error", error_message=str(exc))
        except ValueError as exc:
            return ScanResult([], status="error", error_message=f"Invalid JSON: {exc}")

        candidates = []
        for job in data.get("jobs", []):
            location = (job.get("location") or {}).get("name", "")
            candidates.append(
                OpportunityCandidate(
                    company_name=company.name,
                    job_title=job.get("title", ""),
                    job_url=job.get("absolute_url", ""),
                    location=location,
                    department=", ".join(d.get("name", "") for d in job.get("departments", [])),
                    posted_date=job.get("updated_at", ""),
                    description=job.get("content", ""),
                    source_platform="greenhouse",
                    source_url=api_url,
                )
            )

        return ScanResult(candidates, status="success")
