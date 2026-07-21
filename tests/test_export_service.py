import os

from app.schemas import CompanyIn, OpportunityCandidate
from app.services import export_service
from app.services.company_service import create_company
from app.services.opportunity_service import upsert_opportunity


def test_export_opportunities_csv_writes_file(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(export_service.settings, "export_dir", str(tmp_path))

    upsert_opportunity(db_session, OpportunityCandidate(
        company_name="Regeneron", job_title="Process Development Intern", description="Internship in biologics.",
    ))

    path = export_service.export_opportunities_csv(db_session)
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Regeneron" in content


def test_export_companies_csv_writes_file(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(export_service.settings, "export_dir", str(tmp_path))
    create_company(db_session, CompanyIn(name="Test Export Co"))

    path = export_service.export_companies_csv(db_session)
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Test Export Co" in content
