from app.schemas import OpportunityCandidate
from app.services.opportunity_service import (
    list_opportunities,
    update_status,
    upsert_opportunity,
)
from app.utils.hashing import compute_opportunity_hash


def _candidate(**overrides):
    base = dict(
        company_name="Regeneron",
        job_title="Process Development Intern",
        job_url="https://regeneron.com/jobs/123",
        location="Tarrytown, NY",
        description="Summer internship in process development for biologics.",
    )
    base.update(overrides)
    return OpportunityCandidate(**base)


def test_compute_opportunity_hash_is_stable_for_same_inputs():
    h1 = compute_opportunity_hash("Regeneron", "Process Development Intern", "Tarrytown, NY", "https://regeneron.com/jobs/123")
    h2 = compute_opportunity_hash("Regeneron", "Process Development Intern", "Tarrytown, NY", "https://regeneron.com/jobs/123")
    assert h1 == h2


def test_compute_opportunity_hash_ignores_tracking_params_only():
    h1 = compute_opportunity_hash("Regeneron", "Intern", "NY", "https://regeneron.com/jobs/123?utm_source=x")
    h2 = compute_opportunity_hash("Regeneron", "Intern", "NY", "https://regeneron.com/jobs/123")
    assert h1 == h2


def test_compute_opportunity_hash_distinguishes_job_identifying_query_params():
    # Greenhouse/Lever-style URLs often differ only by a job-id query param — these must
    # NOT collapse onto the same hash, or distinct postings get silently merged.
    h1 = compute_opportunity_hash("Flatiron Health", "Solutions Manager", "", "https://flatiron.com/careers/open-positions/job?gh_jid=111")
    h2 = compute_opportunity_hash("Flatiron Health", "Data Analyst", "", "https://flatiron.com/careers/open-positions/job?gh_jid=222")
    assert h1 != h2


def test_upsert_opportunity_creates_new(db_session):
    opp, is_new = upsert_opportunity(db_session, _candidate())
    assert is_new is True
    assert opp.company_name == "Regeneron"
    assert opp.fit_score > 0


def test_upsert_opportunity_deduplicates_same_url(db_session):
    first, is_new_first = upsert_opportunity(db_session, _candidate())
    second, is_new_second = upsert_opportunity(db_session, _candidate(job_title="Process Development Intern (Updated)"))

    assert is_new_first is True
    assert is_new_second is False
    assert first.id == second.id
    assert second.job_title == "Process Development Intern (Updated)"  # title refreshed in place

    all_opps = list_opportunities(db_session)
    assert len(all_opps) == 1  # no duplicate row created


def test_update_status(db_session):
    opp, _ = upsert_opportunity(db_session, _candidate())
    updated = update_status(db_session, opp.id, "Applied")
    assert updated.status == "Applied"
