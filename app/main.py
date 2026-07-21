"""FastAPI app exposing the manual/browser-agent opportunity import endpoint.

This is intentionally tiny — the dashboard (Streamlit) is the primary UI. This API exists
so a separate browser-automation agent (or a curl/script) can push opportunities it finds
on hard-to-scrape sites (Workday, iCIMS, login-walled portals) into the same database,
without needing to bypass any site protections itself.
"""
from fastapi import FastAPI, HTTPException

from app.database import get_session, init_db
from app.schemas import OpportunityCandidate, OpportunityImportIn
from app.services.company_service import list_companies
from app.services.opportunity_service import upsert_opportunity

app = FastAPI(title="BioInternshipRadar API", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/opportunities/import")
def import_opportunity(payload: OpportunityImportIn) -> dict:
    if not payload.company_name or not payload.job_title:
        raise HTTPException(status_code=400, detail="company_name and job_title are required")

    candidate = OpportunityCandidate(
        company_name=payload.company_name,
        job_title=payload.job_title,
        job_url=payload.job_url,
        location=payload.location,
        description=payload.description,
        posted_date=payload.posted_date,
        source_platform=payload.source,
        source_url=payload.job_url,
    )

    with get_session() as session:
        matching_company = next(
            (c for c in list_companies(session) if c.name.lower() == payload.company_name.lower()), None
        )
        opportunity, is_new = upsert_opportunity(session, candidate, matching_company)
        if payload.notes:
            opportunity.notes = payload.notes
        return {
            "id": opportunity.id,
            "is_new": is_new,
            "fit_score": opportunity.fit_score,
            "status": opportunity.status,
        }
