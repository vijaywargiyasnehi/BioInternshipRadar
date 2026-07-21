"""Stable opportunity hashing for duplicate detection.

Hash is based on company_name + normalized_job_title + normalized_location + normalized_job_url
so that re-scans of the same posting don't create duplicate rows / duplicate notifications.
If the URL is present, it dominates the hash (titles get reworded; URLs rarely change),
so we hash on (company, url) when a url exists, otherwise fall back to (company, title, location).
"""
import hashlib

from app.utils.text_cleaning import normalize_text, normalize_url


def compute_opportunity_hash(company_name: str, job_title: str, location: str, job_url: str) -> str:
    norm_company = normalize_text(company_name)
    norm_title = normalize_text(job_title)
    norm_location = normalize_text(location)
    norm_url = normalize_url(job_url)

    if norm_url:
        key = f"{norm_company}|{norm_url}"
    else:
        key = f"{norm_company}|{norm_title}|{norm_location}"

    return hashlib.sha256(key.encode("utf-8")).hexdigest()
