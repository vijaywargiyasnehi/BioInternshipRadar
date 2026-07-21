from app.schemas import CompanyIn
from app.services.company_service import (
    create_company,
    companies_missing_career_url,
    load_companies_yaml,
    list_companies,
    sync_companies_from_yaml,
    update_company,
)


def test_load_companies_yaml_returns_seeded_companies():
    companies = load_companies_yaml()
    assert len(companies) > 0
    names = {c.name for c in companies}
    assert "Regeneron" in names
    assert "McKinsey" in names


def test_sync_companies_from_yaml_inserts_once(db_session):
    added_first = sync_companies_from_yaml(db_session)
    assert added_first > 0

    added_second = sync_companies_from_yaml(db_session)
    assert added_second == 0  # already synced, no duplicates


def test_companies_missing_career_url(db_session):
    create_company(db_session, CompanyIn(name="No URL Co"))
    create_company(db_session, CompanyIn(name="Has URL Co", career_url="https://example.com/careers"))
    create_company(db_session, CompanyIn(name="Has Board ID Co", platform="greenhouse", board_id="sometoken"))

    missing = companies_missing_career_url(db_session)
    missing_names = {c.name for c in missing}
    assert "No URL Co" in missing_names
    assert "Has URL Co" not in missing_names
    assert "Has Board ID Co" not in missing_names  # board_id counts as configured


def test_update_company(db_session):
    company = create_company(db_session, CompanyIn(name="Editable Co"))
    update_company(db_session, company.id, {"priority": "High", "active": False})

    refreshed = next(c for c in list_companies(db_session) if c.id == company.id)
    assert refreshed.priority == "High"
    assert refreshed.active is False
