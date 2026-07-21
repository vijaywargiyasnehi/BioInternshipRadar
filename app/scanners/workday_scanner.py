"""Best-effort Workday scanner.

Workday career sites are heavily JS-driven and structured per-tenant (different facet
filters, different CXS API paths), so a fully generic scraper is unreliable and prone to
breaking silently. Rather than guess and risk wrong/missing results, this scanner marks
the company for manual review so a human configures a specific search URL (or pastes
opportunities manually via the dashboard / import API). A Playwright-based path can be
added per-tenant later if a company is high priority.
"""
from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult


class WorkdayScanner(BaseScanner):
    name = "workday"

    def scan_company(self, company: Company) -> ScanResult:
        return ScanResult(
            [],
            status="manual_review_required",
            error_message=(
                "Workday career sites require tenant-specific configuration. "
                "Use manual opportunity entry or paste a specific search URL in company notes."
            ),
        )
