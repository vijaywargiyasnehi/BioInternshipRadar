"""Scans Ashby job boards via their public API.

Ashby exposes: POST https://jobs.ashbyhq.com/api/non-user-facing/job-board/job-postings
with body {"organizationHostedJobsPageName": "<slug>"}

Configure in companies.yaml:
  platform: ashby
  board_id: your-company-slug
"""
import requests

from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import wait_for_slot

_API_URL = "https://jobs.ashbyhq.com/api/non-user-facing/job-board/job-postings"


class AshbyScanner(BaseScanner):
    name = "ashby"

    def scan_company(self, company: Company) -> ScanResult:
        board_id = getattr(company, "board_id", "") or ""
        if not board_id:
            return ScanResult(
                [],
                status="manual_review_required",
                error_message="No Ashby slug configured — set board_id: <slug> in companies.yaml (platform: ashby)",
            )

        wait_for_slot(company.name)
        try:
            resp = requests.post(
                _API_URL,
                json={"organizationHostedJobsPageName": board_id},
                headers={"Content-Type": "application/json", "User-Agent": "BioInternshipRadar/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            scanner_logger.warning(f"[ashby] {company.name}: {exc}")
            return ScanResult([], status="error", error_message=str(exc))
        except ValueError as exc:
            return ScanResult([], status="error", error_message=f"Invalid JSON: {exc}")

        candidates = []
        for job in data.get("jobPostings", []):
            locs = [loc.get("locationStr", "") for loc in job.get("jobLocations", []) if loc.get("locationStr")]
            dept = job.get("department", {})
            dept_name = dept.get("name", "") if isinstance(dept, dict) else ""
            job_id = job.get("id", "")
            candidates.append(
                OpportunityCandidate(
                    company_name=company.name,
                    job_title=job.get("title", ""),
                    job_url=f"https://jobs.ashbyhq.com/{board_id}/{job_id}" if job_id else "",
                    location=", ".join(locs),
                    department=dept_name,
                    job_type=job.get("employmentType", ""),
                    description=job.get("descriptionPlain", "") or "",
                    source_platform="ashby",
                    source_url=f"https://jobs.ashbyhq.com/{board_id}",
                )
            )

        return ScanResult(candidates, status="success")
