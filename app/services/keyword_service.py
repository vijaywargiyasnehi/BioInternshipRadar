"""Loads keyword lists from YAML and matches them against job text."""
from functools import lru_cache

import yaml

from app.config import settings
from app.utils.text_cleaning import normalize_text


@lru_cache(maxsize=1)
def load_keywords() -> dict[str, list[str]]:
    if not settings.keywords_yaml_path.exists():
        return {}
    with open(settings.keywords_yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_ignored_keywords() -> list[str]:
    if not settings.ignored_keywords_yaml_path.exists():
        return []
    with open(settings.ignored_keywords_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("ignore", [])


def clear_keyword_cache() -> None:
    load_keywords.cache_clear()
    load_ignored_keywords.cache_clear()


def find_matches(text: str, keywords: list[str]) -> list[str]:
    norm_text = normalize_text(text)
    matched = []
    for kw in keywords:
        if normalize_text(kw) in norm_text:
            matched.append(kw)
    return matched


def match_all_categories(text: str) -> dict[str, list[str]]:
    keyword_sets = load_keywords()
    return {category: find_matches(text, kws) for category, kws in keyword_sets.items()}


def match_ignored(text: str) -> list[str]:
    return find_matches(text, load_ignored_keywords())
