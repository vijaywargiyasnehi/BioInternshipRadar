"""Scans JavaScript-heavy career pages using Playwright (headless Chromium).

Only imports playwright lazily inside scan_company so the rest of the app (dashboard,
static/ATS scanners, tests) works fine even if `playwright install` hasn't been run yet.
"""
from app.config import settings
from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.schemas import OpportunityCandidate
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import wait_for_slot

JOB_LINK_HINTS = ("job", "career", "position", "intern", "req", "posting")
PAGE_TIMEOUT_MS = 20_000


class PlaywrightScanner(BaseScanner):
    name = "playwright"

    def scan_company(self, company: Company) -> ScanResult:
        if not settings.enable_playwright:
            return ScanResult([], status="manual_review_required", error_message="Playwright disabled in settings")

        url = company.internship_url or company.career_url
        if not url:
            return ScanResult([], status="manual_review_required", error_message="No career/internship URL configured")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ScanResult([], status="error", error_message="Playwright not installed. Run: pip install playwright && playwright install")

        wait_for_slot(company.name)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=settings.headless_browser)
                page = browser.new_page()
                page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="networkidle")
                links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
                )
                browser.close()
        except Exception as exc:
            scanner_logger.warning(f"[playwright] {company.name}: {exc}")
            return ScanResult([], status="error", error_message=str(exc))

        candidates = []
        seen = set()
        for link in links:
            text, href = link.get("text", ""), link.get("href", "")
            if not text or len(text) < 4 or href in seen:
                continue
            if not any(hint in href.lower() for hint in JOB_LINK_HINTS):
                continue
            seen.add(href)
            candidates.append(
                OpportunityCandidate(
                    company_name=company.name,
                    job_title=text,
                    job_url=href,
                    description=text,
                    source_platform="playwright",
                    source_url=url,
                )
            )

        return ScanResult(candidates, status="success")
