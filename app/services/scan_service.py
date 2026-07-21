"""Orchestrates a scan run: picks due companies, scans each safely, persists
opportunities/scan_logs/scan_runs, and triggers notifications for new high-fit matches.

This is the single code path used by the scheduler, run_scanner.py, and the dashboard's
"Run Scan Now" button — so behavior (rate limiting, logging, error handling) stays
consistent no matter how a scan was triggered.
"""
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Company, ScanLog, ScanRun
from app.scanners.scanner_router import scan_company as run_scanner_for_company
from app.schemas import OpportunityCandidate
from app.services.company_service import companies_due_for_scan, list_companies, update_company
from app.services.notification_service import notify_new_opportunity
from app.services.opportunity_service import upsert_opportunity
from app.utils.logging_utils import scanner_logger
from app.utils.rate_limit import jitter_sleep

_INTERNSHIP_RE = re.compile(
    r"\b(intern(ship)?|co-?op|fellow(ship)?|student trainee|student researcher|"
    r"rotational|summer associate|summer analyst|early.?career|trainee|scholar)\b",
    re.IGNORECASE,
)


def _looks_like_internship(candidate: OpportunityCandidate) -> bool:
    return bool(_INTERNSHIP_RE.search(candidate.job_title))


def run_scan(session: Session, companies: list[Company] | None = None) -> ScanRun:
    """Scans the given companies (or all companies due per their interval if None)."""
    scan_run = ScanRun(started_at=datetime.utcnow(), status="running")
    session.add(scan_run)
    session.flush()

    targets = companies if companies is not None else companies_due_for_scan(session, settings.max_companies_per_scan_batch)
    scanner_logger.info(f"Scan run #{scan_run.id} starting for {len(targets)} company(ies)")

    for company in targets:
        _scan_one_company(session, scan_run, company)
        # Only jitter when we made a real network request.
        if company.career_url or company.internship_url or getattr(company, "board_id", None):
            jitter_sleep(1.0, 3.0)

    scan_run.ended_at = datetime.utcnow()
    scan_run.status = "completed"
    session.flush()
    scanner_logger.info(
        f"Scan run #{scan_run.id} completed: {scan_run.companies_scanned} scanned, "
        f"{scan_run.new_opportunities_found} new opportunities, {scan_run.errors_count} errors"
    )
    return scan_run


def run_scan_for_company_id(session: Session, company_id: int) -> ScanRun:
    company = session.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found")
    return run_scan(session, companies=[company])


def _scan_one_company(session: Session, scan_run: ScanRun, company: Company) -> None:
    log = ScanLog(scan_run_id=scan_run.id, company_id=company.id, company_name=company.name, started_at=datetime.utcnow())
    session.add(log)
    session.flush()

    try:
        result = run_scanner_for_company(company)
    except Exception as exc:  # Scanners should not raise, but guard the whole batch anyway.
        scanner_logger.exception(f"Unexpected scanner failure for {company.name}")
        result = None
        log.status = "error"
        log.error_message = f"Unexpected error: {exc}"

    log.ended_at = datetime.utcnow()
    scan_run.companies_scanned += 1

    if result is not None:
        log.scanner_used = company.platform or "unknown"
        log.status = result.status
        log.error_message = result.error_message
        log.jobs_found = len(result.candidates)
        log.source_url = company.internship_url or company.career_url

        new_count = 0
        skipped = 0
        for candidate in result.candidates:
            if settings.internship_only and not _looks_like_internship(candidate):
                skipped += 1
                continue
            opportunity, is_new = upsert_opportunity(session, candidate, company)
            if is_new:
                new_count += 1
                notify_new_opportunity(session, opportunity)
        if skipped:
            scanner_logger.debug(f"[scan] {company.name}: skipped {skipped} non-internship roles (internship_only=true)")
        log.new_jobs_found = new_count

        scan_run.opportunities_found += log.jobs_found
        scan_run.new_opportunities_found += new_count

        if result.status == "error":
            scan_run.errors_count += 1

    update_company(
        session,
        company.id,
        {
            "last_scanned_at": datetime.utcnow(),
            "last_scan_status": log.status,
            "last_scan_error": log.error_message,
        },
    )
    session.flush()


def run_scan_all_active(session: Session) -> ScanRun:
    """Used by 'Run Scan Now' on the dashboard to scan everything regardless of interval."""
    return run_scan(session, companies=list_companies(session, active_only=True))
