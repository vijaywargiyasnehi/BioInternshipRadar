"""Runs a single scan pass immediately and exits — useful for cron/Task Scheduler,
manual testing, or CI smoke checks. For continuous 15-minute scanning, use scheduler.py
instead.

Usage:
    python run_scanner.py            # scans companies due per their interval
    python run_scanner.py --all      # scans all active companies regardless of interval
"""
import sys

from app.database import get_session, init_db
from app.services.company_service import list_companies, sync_companies_from_yaml
from app.services.scan_service import run_scan
from app.utils.logging_utils import app_logger


def main() -> None:
    init_db()
    scan_all = "--all" in sys.argv

    with get_session() as session:
        added = sync_companies_from_yaml(session)
        if added:
            app_logger.info(f"Synced {added} new companies from companies.yaml")

        companies = list_companies(session, active_only=True) if scan_all else None
        scan_run = run_scan(session, companies=companies)

        print(f"Scan run #{scan_run.id}: {scan_run.companies_scanned} companies scanned, "
              f"{scan_run.opportunities_found} opportunities found, "
              f"{scan_run.new_opportunities_found} new, {scan_run.errors_count} errors")


if __name__ == "__main__":
    main()
