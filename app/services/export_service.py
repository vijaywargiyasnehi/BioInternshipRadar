"""Exports opportunities, companies, and scan logs to CSV/Excel/YAML under exports/."""
import pandas as pd
import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Opportunity, Company, ScanLog


def _export_dir():
    path = settings.resolved_path(settings.export_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_opportunities_csv(session: Session) -> str:
    opps = session.query(Opportunity).all()
    df = pd.DataFrame([_opp_row(o) for o in opps])
    out_path = _export_dir() / "opportunities.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)


def export_opportunities_excel(session: Session) -> str:
    opps = session.query(Opportunity).all()
    df = pd.DataFrame([_opp_row(o) for o in opps])
    out_path = _export_dir() / "opportunities.xlsx"
    df.to_excel(out_path, index=False)
    return str(out_path)


def export_companies_csv(session: Session) -> str:
    companies = session.query(Company).all()
    df = pd.DataFrame([_company_row(c) for c in companies])
    out_path = _export_dir() / "companies.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)


def export_companies_yaml(session: Session) -> str:
    from app.services.company_service import export_companies_to_yaml

    out_path = _export_dir() / "companies_export.yaml"
    export_companies_to_yaml(session, out_path)
    return str(out_path)


def export_scan_logs_csv(session: Session) -> str:
    logs = session.query(ScanLog).all()
    df = pd.DataFrame([_log_row(l) for l in logs])
    out_path = _export_dir() / "scan_history.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)


def _opp_row(o: Opportunity) -> dict:
    return {
        "id": o.id,
        "company_name": o.company_name,
        "job_title": o.job_title,
        "job_url": o.job_url,
        "location": o.location,
        "remote_status": o.remote_status,
        "fit_score": o.fit_score,
        "status": o.status,
        "detected_date": o.detected_date,
        "matched_keywords": o.matched_keywords,
        "notification_sent": o.notification_sent,
        "resume_generated": o.resume_generated,
    }


def _company_row(c: Company) -> dict:
    return {
        "name": c.name,
        "category": c.category,
        "career_url": c.career_url,
        "internship_url": c.internship_url,
        "platform": c.platform,
        "network_contact": c.network_contact,
        "priority": c.priority,
        "active": c.active,
        "last_scanned_at": c.last_scanned_at,
        "last_scan_status": c.last_scan_status,
    }


def _log_row(l: ScanLog) -> dict:
    return {
        "company_name": l.company_name,
        "started_at": l.started_at,
        "ended_at": l.ended_at,
        "scanner_used": l.scanner_used,
        "status": l.status,
        "jobs_found": l.jobs_found,
        "new_jobs_found": l.new_jobs_found,
        "error_message": l.error_message,
        "source_url": l.source_url,
    }
