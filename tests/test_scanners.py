from unittest.mock import patch, MagicMock

import pytest

from app.models import Company
from app.scanners.ashby_scanner import AshbyScanner
from app.scanners.greenhouse_scanner import GreenhouseScanner, extract_board_token
from app.scanners.lever_scanner import LeverScanner, extract_company_slug
from app.scanners.scanner_router import detect_platform
from app.scanners.usajobs_scanner import USAJobsScanner
from app.scanners.workday_scanner import WorkdayScanner
from app.scanners.icims_scanner import IcimsScanner


def _company(**overrides) -> Company:
    c = Company(name="Test Co", category="Bio Companies", platform="unknown", board_id="")
    for key, value in overrides.items():
        setattr(c, key, value)
    return c


# ---------------------------------------------------------------------------
# Token / slug extraction
# ---------------------------------------------------------------------------

def test_extract_greenhouse_board_token():
    assert extract_board_token("https://boards.greenhouse.io/regeneron") == "regeneron"
    assert extract_board_token("https://job-boards.greenhouse.io/acme") == "acme"
    assert extract_board_token("https://example.com/careers") is None


def test_extract_lever_company_slug():
    assert extract_company_slug("https://jobs.lever.co/flatiron") == "flatiron"
    assert extract_company_slug("https://example.com/careers") is None


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def test_detect_platform_prefers_explicit_setting():
    company = _company(platform="greenhouse", career_url="https://example.com")
    assert detect_platform(company) == "greenhouse"


def test_detect_platform_infers_from_url():
    assert detect_platform(_company(career_url="https://boards.greenhouse.io/acme")) == "greenhouse"
    assert detect_platform(_company(career_url="https://jobs.lever.co/acme")) == "lever"
    assert detect_platform(_company(career_url="https://jobs.ashbyhq.com/acme")) == "ashby"
    assert detect_platform(_company(career_url="https://acme.wd1.myworkdayjobs.com/careers")) == "workday"


def test_detect_platform_unknown_without_url():
    assert detect_platform(_company(career_url="", internship_url="")) == "unknown"


def test_detect_platform_explicit_usajobs():
    assert detect_platform(_company(platform="usajobs")) == "usajobs"


# ---------------------------------------------------------------------------
# Greenhouse scanner uses board_id directly (no career_url needed)
# ---------------------------------------------------------------------------

def test_greenhouse_scanner_uses_board_id_when_no_url():
    company = _company(platform="greenhouse", board_id="flatironhealth", career_url="", internship_url="")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobs": [
        {"title": "Data Science Intern", "absolute_url": "https://example.com/job/1",
         "location": {"name": "New York, NY"}, "departments": [], "updated_at": "2025-01-01", "content": "Great role"}
    ]}
    mock_resp.raise_for_status = MagicMock()
    with patch("app.scanners.greenhouse_scanner.requests.get", return_value=mock_resp):
        result = GreenhouseScanner().scan_company(company)
    assert result.status == "success"
    assert len(result.candidates) == 1
    assert result.candidates[0].job_title == "Data Science Intern"


def test_greenhouse_scanner_returns_manual_review_when_no_token_or_board_id():
    company = _company(platform="greenhouse", board_id="", career_url="", internship_url="")
    result = GreenhouseScanner().scan_company(company)
    assert result.status == "manual_review_required"
    assert result.candidates == []


# ---------------------------------------------------------------------------
# Lever scanner uses board_id directly
# ---------------------------------------------------------------------------

def test_lever_scanner_uses_board_id_when_no_url():
    company = _company(platform="lever", board_id="neuralink", career_url="", internship_url="")
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"text": "Research Intern", "hostedUrl": "https://jobs.lever.co/neuralink/abc",
         "categories": {"location": "Austin, TX", "team": "Research", "commitment": "Internship"},
         "descriptionPlain": "Exciting role"}
    ]
    mock_resp.raise_for_status = MagicMock()
    with patch("app.scanners.lever_scanner.requests.get", return_value=mock_resp):
        result = LeverScanner().scan_company(company)
    assert result.status == "success"
    assert result.candidates[0].job_title == "Research Intern"


# ---------------------------------------------------------------------------
# Ashby scanner
# ---------------------------------------------------------------------------

def test_ashby_scanner_returns_manual_review_when_no_board_id():
    company = _company(platform="ashby", board_id="")
    result = AshbyScanner().scan_company(company)
    assert result.status == "manual_review_required"
    assert result.candidates == []


def test_ashby_scanner_parses_response():
    company = _company(platform="ashby", board_id="altoslabs")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobPostings": [
        {"title": "Biology Intern", "id": "job-1",
         "jobLocations": [{"locationStr": "San Francisco, CA"}],
         "department": {"name": "Research"}, "employmentType": "Internship",
         "descriptionPlain": "Longevity research"}
    ]}
    mock_resp.raise_for_status = MagicMock()
    with patch("app.scanners.ashby_scanner.requests.post", return_value=mock_resp):
        result = AshbyScanner().scan_company(company)
    assert result.status == "success"
    assert result.candidates[0].job_title == "Biology Intern"
    assert result.candidates[0].source_platform == "ashby"


# ---------------------------------------------------------------------------
# USAJobs scanner
# ---------------------------------------------------------------------------

def test_usajobs_scanner_returns_manual_review_without_credentials(monkeypatch):
    monkeypatch.setattr("app.config.settings.usajobs_api_key", "")
    monkeypatch.setattr("app.config.settings.usajobs_email", "")
    company = _company(platform="usajobs")
    result = USAJobsScanner().scan_company(company)
    assert result.status == "manual_review_required"
    assert "USAJOBS_API_KEY" in result.error_message


def test_usajobs_scanner_deduplicates_across_queries(monkeypatch):
    monkeypatch.setattr("app.config.settings.usajobs_api_key", "fakekey")
    monkeypatch.setattr("app.config.settings.usajobs_email", "test@example.com")

    item = {
        "MatchedObjectDescriptor": {
            "PositionID": "UNIQUE-123",
            "PositionTitle": "Bioengineering Intern",
            "OrganizationName": "National Institutes of Health",
            "PositionLocationDisplay": "Bethesda, MD",
            "PublicationStartDate": "2025-06-01",
            "QualificationSummary": "Must be enrolled in a degree program.",
            "ApplyURI": ["https://www.usajobs.gov/job/UNIQUE-123"],
        }
    }

    def fake_fetch(keyword, api_key, email):
        return [item]

    with patch("app.scanners.usajobs_scanner._fetch_usajobs", side_effect=fake_fetch):
        company = _company(platform="usajobs")
        result = USAJobsScanner().scan_company(company)

    assert result.status == "success"
    # The same PositionID should appear only once despite multiple search queries
    ids = [c.job_url for c in result.candidates]
    assert len(ids) == len(set(ids)), "Duplicate jobs were returned"
    assert result.candidates[0].company_name == "National Institutes of Health"


# ---------------------------------------------------------------------------
# Stubs still work
# ---------------------------------------------------------------------------

def test_workday_and_icims_scanners_require_manual_review():
    result = WorkdayScanner().scan_company(_company(career_url="https://acme.wd1.myworkdayjobs.com/careers"))
    assert result.status == "manual_review_required"
    assert result.candidates == []

    result2 = IcimsScanner().scan_company(_company(career_url="https://acme.icims.com/jobs"))
    assert result2.status == "manual_review_required"
