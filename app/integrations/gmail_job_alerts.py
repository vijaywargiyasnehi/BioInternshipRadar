"""Placeholder for future Gmail job-alert ingestion.

Not implemented yet. The intended shape, once built:
1. Authenticate with Gmail API (OAuth) using a scoped, read-only token.
2. Search for job-alert emails (e.g. from LinkedIn, Indeed, Greenhouse "new posting" digests).
3. Parse each email into one or more OpportunityCandidate objects.
4. Call opportunity_service.upsert_opportunity() for each one — same path as scanners
   and the /api/opportunities/import endpoint use, so dedup/scoring/notifications all
   apply automatically.

Kept as a stub so the integration point is obvious without committing to a Gmail
API client/dependency until this is actually built.
"""
from app.schemas import OpportunityCandidate


def fetch_job_alert_candidates() -> list[OpportunityCandidate]:
    raise NotImplementedError("Gmail job alert integration is not implemented yet.")
