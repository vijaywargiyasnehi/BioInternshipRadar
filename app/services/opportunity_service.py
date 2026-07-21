"""Create/update opportunities with duplicate detection and status management."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Opportunity, Company
from app.schemas import OpportunityCandidate
from app.services.scoring_service import score_opportunity
from app.utils.hashing import compute_opportunity_hash


def upsert_opportunity(session: Session, candidate: OpportunityCandidate, company: Company | None = None) -> tuple[Opportunity, bool]:
    """Insert a new opportunity or refresh last_seen_at on an existing one.

    Returns (opportunity, is_new).
    """
    opp_hash = compute_opportunity_hash(
        candidate.company_name, candidate.job_title, candidate.location, candidate.job_url
    )

    existing = session.execute(
        select(Opportunity).where(Opportunity.opportunity_hash == opp_hash)
    ).scalar_one_or_none()

    if existing:
        existing.last_seen_at = datetime.utcnow()
        # Title can drift slightly (e.g. "(2027)" appended) while URL stays stable — keep latest text.
        if candidate.job_title:
            existing.job_title = candidate.job_title
        if candidate.description:
            existing.description = candidate.description
        session.flush()
        return existing, False

    fit_result = score_opportunity(candidate, company)

    opportunity = Opportunity(
        company_id=company.id if company else None,
        company_name=candidate.company_name,
        job_title=candidate.job_title,
        job_url=candidate.job_url,
        location=candidate.location,
        remote_status=candidate.remote_status,
        department=candidate.department,
        job_type=candidate.job_type,
        posted_date=candidate.posted_date,
        description=candidate.description,
        source_platform=candidate.source_platform,
        source_url=candidate.source_url,
        opportunity_hash=opp_hash,
        fit_score=fit_result.score,
        fit_score_explanation="\n".join(fit_result.reasons),
        matched_keywords=", ".join(fit_result.matched_keywords),
        ignored_keywords=", ".join(fit_result.ignored_keywords_hit),
        status="New",
    )
    session.add(opportunity)
    session.flush()
    return opportunity, True


def update_status(session: Session, opportunity_id: int, status: str) -> Opportunity | None:
    opp = session.get(Opportunity, opportunity_id)
    if opp is None:
        return None
    opp.status = status
    opp.updated_at = datetime.utcnow()
    session.flush()
    return opp


def add_note(session: Session, opportunity_id: int, note: str) -> Opportunity | None:
    opp = session.get(Opportunity, opportunity_id)
    if opp is None:
        return None
    opp.notes = note
    session.flush()
    return opp


def list_opportunities(
    session: Session,
    company_name: str | None = None,
    status: str | None = None,
    min_fit_score: int | None = None,
    new_only: bool = False,
) -> list[Opportunity]:
    stmt = select(Opportunity).order_by(Opportunity.detected_date.desc())
    if company_name:
        stmt = stmt.where(Opportunity.company_name == company_name)
    if status:
        stmt = stmt.where(Opportunity.status == status)
    if min_fit_score is not None:
        stmt = stmt.where(Opportunity.fit_score >= min_fit_score)
    results = list(session.execute(stmt).scalars().all())
    if new_only:
        results = [o for o in results if o.status == "New"]
    return results


def mark_notification_sent(session: Session, opportunity_id: int) -> None:
    opp = session.get(Opportunity, opportunity_id)
    if opp:
        opp.notification_sent = True
        opp.notification_sent_at = datetime.utcnow()
        session.flush()


def mark_resume_generated(session: Session, opportunity_id: int, resume_path: str) -> None:
    opp = session.get(Opportunity, opportunity_id)
    if opp:
        opp.resume_generated = True
        opp.resume_path = resume_path
        if opp.status == "New":
            opp.status = "Resume Generated"
        session.flush()
