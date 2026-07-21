from app.services.keyword_service import find_matches, match_all_categories, match_ignored


def test_find_matches_is_case_insensitive():
    matches = find_matches("Summer INTERN in Bioengineering", ["intern", "bioengineering"])
    assert "intern" in matches
    assert "bioengineering" in matches


def test_match_all_categories_groups_by_category():
    text = "Process Development Internship using CHO cell culture and data science analytics"
    matches = match_all_categories(text)
    assert "internship" in matches["high_priority"]
    assert "CHO" in matches["biotech_bioengineering"]
    assert "data science" in matches["data_healthtech"]


def test_match_ignored_flags_excluded_terms():
    text = "Senior Director of Manufacturing, 5+ years experience required"
    hits = match_ignored(text)
    assert "senior" in hits
    assert "director" in hits
    assert "5+ years" in hits


def test_match_ignored_returns_empty_for_clean_text():
    hits = match_ignored("Bioengineering Summer Intern, entry level role")
    assert hits == []
