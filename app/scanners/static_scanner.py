"""Scans plain HTML career pages using requests + BeautifulSoup.

Heuristic approach: find anchor tags whose text looks like a job title and whose href
looks like a job posting link. This is best-effort and will not work on every site —
JS-rendered pages should use playwright_scanner, and recognized ATS platforms should use
their dedicated scanner instead.
"""
import requests
from bs4 import BeautifulSoup

from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import wait_for_slot

REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "BioInternshipRadar/1.0 (personal internship tracker; respectful crawl)"

JOB_LINK_HINTS = ("job", "career", "position", "intern", "req", "posting")


class StaticScanner(BaseScanner):
    name = "company_static"

    def scan_company(self, company: Company) -> ScanResult:
        url = company.internship_url or company.career_url
        if not url:
            return ScanResult([], status="manual_review_required", error_message="No career/internship URL configured")

        wait_for_slot(company.name)

        try:
            resp = requests.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            scanner_logger.warning(f"[static] {company.name}: request failed: {exc}")
            return ScanResult([], status="error", error_message=str(exc))

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            return ScanResult([], status="error", error_message=f"Failed to parse HTML: {exc}")

        candidates = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            if not text or len(text) < 4:
                continue
            if not any(hint in href.lower() for hint in JOB_LINK_HINTS):
                continue
            full_url = href if href.startswith("http") else requests.compat.urljoin(url, href)
            candidates.append(
                OpportunityCandidate(
                    company_name=company.name,
                    job_title=text,
                    job_url=full_url,
                    description=text,
                    source_platform="company_static",
                    source_url=url,
                )
            )

        # De-dupe within this single page scan (some sites repeat the same link in nav + body).
        seen_urls = set()
        unique_candidates = []
        for c in candidates:
            if c.job_url in seen_urls:
                continue
            seen_urls.add(c.job_url)
            unique_candidates.append(c)

        return ScanResult(unique_candidates, status="success")
