from app.models import Company
from app.schemas import OpportunityCandidate
from app.services.scoring_service import score_opportunity


def test_score_opportunity_rewards_internship_and_biotech_keywords():
    candidate = OpportunityCandidate(
        company_name="Regeneron",
        job_title="Process Development Intern",
        location="Tarrytown, NY",
        description="Summer internship in process development for biologics manufacturing, CHO cell culture.",
    )
    result = score_opportunity(candidate)
    assert result.score > 0
    assert "intern" in result.matched_keywords or "internship" in result.matched_keywords
    assert any("Matched" in reason for reason in result.reasons)


def test_score_opportunity_penalizes_ignored_keywords():
    candidate = OpportunityCandidate(
        company_name="Acme",
        job_title="Senior Director, Manufacturing",
        description="5+ years experience required. PhD required.",
    )
    result = score_opportunity(candidate)
    assert result.score == 0
    assert result.ignored_keywords_hit


def test_score_opportunity_rewards_preferred_location_and_company_priority():
    company = Company(name="Regeneron", priority="High")
    candidate = OpportunityCandidate(
        company_name="Regeneron",
        job_title="Bioengineering Intern",
        location="Boston, MA",
        description="Summer internship in bioengineering.",
    )
    result = score_opportunity(candidate, company)
    assert "+ Location is preferred" in result.reasons
    assert "+ Company priority is High" in result.reasons


def test_score_is_clamped_between_0_and_100():
    candidate = OpportunityCandidate(company_name="Acme", job_title="", description="")
    result = score_opportunity(candidate)
    assert 0 <= result.score <= 100
