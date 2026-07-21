"""Computes a 0-100 fit_score for an opportunity candidate with a human-readable explanation."""
from functools import lru_cache

import yaml

from app.config import settings
from app.models import Company
from app.schemas import FitScoreResult, OpportunityCandidate
from app.services.keyword_service import match_all_categories, match_ignored
from app.utils.text_cleaning import normalize_text

# Point weights per matched category (capped contributions keep score bounded at 100).
CATEGORY_WEIGHTS = {
    "high_priority": 30,
    "biotech_bioengineering": 25,
    "data_healthtech": 15,
    "consulting": 15,
}
LOCATION_MATCH_POINTS = 10
PRIORITY_POINTS = {"High": 10, "Medium": 5, "Low": 0}
IGNORED_PENALTY_PER_HIT = 15


@lru_cache(maxsize=1)
def _preferred_locations() -> list[str]:
    if not settings.locations_yaml_path.exists():
        return []
    with open(settings.locations_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("preferred_locations", [])


def clear_location_cache() -> None:
    _preferred_locations.cache_clear()


def score_opportunity(candidate: OpportunityCandidate, company: Company | None = None) -> FitScoreResult:
    text = " ".join([candidate.job_title, candidate.description, candidate.department, candidate.job_type])
    category_matches = match_all_categories(text)
    ignored_hits = match_ignored(text)

    score = 0
    reasons: list[str] = []
    all_matched: list[str] = []

    for category, matched_terms in category_matches.items():
        if matched_terms:
            score += CATEGORY_WEIGHTS.get(category, 0)
            all_matched.extend(matched_terms)
            label = category.replace("_", "/")
            reasons.append(f"+ Matched {label} keyword(s): {', '.join(matched_terms[:5])}")

    norm_location = normalize_text(candidate.location)
    location_hit = any(normalize_text(loc) in norm_location for loc in _preferred_locations()) if norm_location else False
    if location_hit:
        score += LOCATION_MATCH_POINTS
        reasons.append("+ Location is preferred")
    elif candidate.remote_status and "remote" in candidate.remote_status.lower():
        score += LOCATION_MATCH_POINTS
        reasons.append("+ Remote role (treated as preferred)")

    if company is not None:
        priority_points = PRIORITY_POINTS.get(company.priority, 0)
        if priority_points:
            score += priority_points
            reasons.append(f"+ Company priority is {company.priority}")

    if ignored_hits:
        penalty = IGNORED_PENALTY_PER_HIT * len(ignored_hits)
        score -= penalty
        reasons.append(f"- Excluded term(s) found: {', '.join(ignored_hits)} (-{penalty})")

    if not category_matches.get("high_priority"):
        reasons.append("- No explicit internship/early-career wording found")

    score = max(0, min(100, score))

    return FitScoreResult(
        score=score,
        matched_keywords=sorted(set(all_matched)),
        ignored_keywords_hit=ignored_hits,
        reasons=reasons,
    )
