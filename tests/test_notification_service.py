from datetime import datetime

from app.models import Opportunity
from app.services.notification_service import format_email_body, format_short_message


def _sample_opportunity() -> Opportunity:
    return Opportunity(
        company_name="Regeneron",
        job_title="Process Development Intern",
        job_url="https://regeneron.com/jobs/123",
        location="Tarrytown, NY",
        fit_score=87,
        detected_date=datetime(2026, 6, 19, 10, 45),
        matched_keywords="internship, process development, CHO",
        fit_score_explanation="+ Internship role\n+ Process development\n+ Biotech/pharma match",
        opportunity_hash="abc123",
    )


def test_format_email_body_includes_required_fields():
    opp = _sample_opportunity()
    body = format_email_body(opp)

    assert "Regeneron" in body
    assert "Process Development Intern" in body
    assert "Tarrytown, NY" in body
    assert "87" in body
    assert "https://regeneron.com/jobs/123" in body
    assert "internship, process development, CHO" in body


def test_format_email_body_marks_high_priority():
    opp = _sample_opportunity()
    opp.fit_score = 90
    body = format_email_body(opp)
    assert "HIGH PRIORITY" in body


def test_format_short_message_is_concise():
    opp = _sample_opportunity()
    message = format_short_message(opp)
    assert "Regeneron" in message
    assert "87" in message
    assert len(message) < 300
