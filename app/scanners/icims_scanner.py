"""Best-effort iCIMS scanner.

Like Workday, iCIMS career portals vary significantly between tenants and many require
JS rendering or session-specific search parameters. This best-effort implementation marks
companies for manual review rather than guess at a fragile per-tenant scrape.
"""
from app.models import Company
from app.scanners.base_scanner import BaseScanner, ScanResult


class IcimsScanner(BaseScanner):
    name = "icims"

    def scan_company(self, company: Company) -> ScanResult:
        return ScanResult(
            [],
            status="manual_review_required",
            error_message=(
                "iCIMS career portals require tenant-specific configuration. "
                "Use manual opportunity entry or paste a specific search URL in company notes."
            ),
        )
