"""Picks the right scanner for a company based on its configured platform / URL."""
from app.config import settings
from app.models import Company
from app.scanners.ashby_scanner import AshbyScanner
from app.scanners.base_scanner import BaseScanner, ScanResult
from app.scanners.greenhouse_scanner import GreenhouseScanner, extract_board_token
from app.scanners.icims_scanner import IcimsScanner
from app.scanners.lever_scanner import LeverScanner, extract_company_slug
from app.scanners.playwright_scanner import PlaywrightScanner
from app.scanners.static_scanner import StaticScanner
from app.scanners.usajobs_scanner import USAJobsScanner
from app.scanners.workday_scanner import WorkdayScanner

_SCANNERS: dict[str, BaseScanner] = {
    "greenhouse": GreenhouseScanner(),
    "lever": LeverScanner(),
    "ashby": AshbyScanner(),
    "usajobs": USAJobsScanner(),
    "workday": WorkdayScanner(),
    "icims": IcimsScanner(),
    "company_static": StaticScanner(),
}


def detect_platform(company: Company) -> str:
    """Returns the ATS platform for this company, preferring an explicit platform field."""
    if company.platform and company.platform != "unknown":
        return company.platform

    url = company.career_url or company.internship_url or ""
    if extract_board_token(url):
        return "greenhouse"
    if extract_company_slug(url):
        return "lever"
    if "ashbyhq.com" in url.lower():
        return "ashby"
    if "workday" in url.lower() or "myworkdayjobs.com" in url.lower():
        return "workday"
    if "icims.com" in url.lower():
        return "icims"
    return "company_static" if url else "unknown"


def scan_company(company: Company) -> ScanResult:
    platform = detect_platform(company)

    if platform == "unknown":
        return ScanResult(
            [],
            status="manual_review_required",
            error_message="No career URL or board_id configured — set platform + board_id in companies.yaml",
        )

    scanner = _SCANNERS.get(platform, StaticScanner())
    result = scanner.scan_company(company)

    # Playwright fallback for JS-heavy static pages that failed.
    if (
        result.status == "error"
        and platform == "company_static"
        and settings.enable_playwright
    ):
        fallback = PlaywrightScanner().scan_company(company)
        if fallback.candidates or fallback.status == "success":
            return fallback

    return result
