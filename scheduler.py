"""Standalone scheduler process: wakes up every SCAN_INTERVAL_MINUTES and scans
companies that are due (per their own scan_interval_minutes). Run with:

    python scheduler.py

Leave this running in its own terminal/process while you use the dashboard separately.
"""
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import settings
from app.database import get_session, init_db
from app.services.company_service import sync_companies_from_yaml
from app.services.scan_service import run_scan
from app.utils.logging_utils import app_logger


def scheduled_scan_job() -> None:
    with get_session() as session:
        run_scan(session)


def main() -> None:
    init_db()
    with get_session() as session:
        added = sync_companies_from_yaml(session)
        if added:
            app_logger.info(f"Synced {added} new companies from companies.yaml")

    app_logger.info(f"Scheduler starting — scanning every {settings.scan_interval_minutes} minutes")

    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_scan_job, "interval", minutes=settings.scan_interval_minutes, next_run_time=None)
    # Run once immediately on startup, then on the regular interval.
    scheduler.add_job(scheduled_scan_job, id="startup_scan")

    def _shutdown(*_args):
        app_logger.info("Scheduler shutting down")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    scheduler.start()


if __name__ == "__main__":
    main()
