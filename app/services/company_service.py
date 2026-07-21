"""Loads companies.yaml into the database and provides CRUD helpers."""
from datetime import datetime

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Company
from app.schemas import CompanyIn

# Fields in companies.yaml that are "configuration" — propagated from YAML into DB on each
# startup so that editing the YAML file takes effect without a manual DB edit.
_YAML_CONFIG_FIELDS = ("platform", "board_id", "career_url", "internship_url", "category")


def load_companies_yaml(path=None) -> list[CompanyIn]:
    path = path or settings.companies_yaml_path
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    items = raw.get("companies", [])
    cleaned = []
    for item in items:
        item.pop("network_contact", None)  # silently discard legacy field
        cleaned.append(CompanyIn(**item))
    return cleaned


def sync_companies_from_yaml(session: Session, path=None) -> int:
    """Insert new companies from YAML; update config fields for existing ones.

    Returns count of newly inserted companies.
    """
    added = 0
    for c in load_companies_yaml(path):
        existing = session.execute(
            select(Company).where(Company.name == c.name)
        ).scalar_one_or_none()

        if existing is None:
            session.add(Company(**c.model_dump()))
            session.flush()
            added += 1
        else:
            for field in _YAML_CONFIG_FIELDS:
                yaml_val = getattr(c, field, None)
                if yaml_val is not None and hasattr(existing, field):
                    setattr(existing, field, yaml_val)
            session.flush()
    return added


def export_companies_to_yaml(session: Session, path=None) -> None:
    path = path or settings.companies_yaml_path
    companies = session.execute(
        select(Company).order_by(Company.category, Company.name)
    ).scalars().all()
    data = {
        "companies": [
            {
                "name": c.name,
                "category": c.category,
                "platform": c.platform,
                "board_id": getattr(c, "board_id", "") or "",
                "career_url": c.career_url,
                "internship_url": c.internship_url,
                "priority": c.priority,
                "active": c.active,
                "notes": c.notes,
            }
            for c in companies
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def list_companies(session: Session, active_only: bool = False) -> list[Company]:
    stmt = select(Company).order_by(Company.category, Company.name)
    if active_only:
        stmt = stmt.where(Company.active.is_(True))
    return list(session.execute(stmt).scalars().all())


def get_company(session: Session, company_id: int) -> Company | None:
    return session.get(Company, company_id)


def create_company(session: Session, data: CompanyIn) -> Company:
    company = Company(**data.model_dump())
    session.add(company)
    session.flush()
    return company


def update_company(session: Session, company_id: int, data: dict) -> Company | None:
    company = session.get(Company, company_id)
    if company is None:
        return None
    for key, value in data.items():
        if hasattr(company, key):
            setattr(company, key, value)
    company.updated_at = datetime.utcnow()
    session.flush()
    return company


def deactivate_company(session: Session, company_id: int) -> None:
    update_company(session, company_id, {"active": False})


def _is_scannable(c: Company) -> bool:
    """True if the company has enough config to attempt an automated scan."""
    if getattr(c, "board_id", None):
        return True
    return bool(c.career_url or c.internship_url)


def companies_missing_career_url(session: Session) -> list[Company]:
    """Returns companies that have no usable scan configuration."""
    return [c for c in list_companies(session) if not _is_scannable(c)]


def companies_due_for_scan(session: Session, limit: int) -> list[Company]:
    """Active companies whose last scan is older than their interval (or never scanned)."""
    now = datetime.utcnow()
    due = []
    for c in list_companies(session, active_only=True):
        if not c.last_scanned_at:
            due.append(c)
            continue
        elapsed = (now - c.last_scanned_at).total_seconds() / 60
        if elapsed >= c.scan_interval_minutes:
            due.append(c)
    due.sort(key=lambda c: {"High": 0, "Medium": 1, "Low": 2}.get(c.priority, 1))
    return due[:limit]
