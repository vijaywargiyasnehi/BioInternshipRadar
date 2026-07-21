"""Text normalization helpers shared by hashing, keyword matching, and scanners."""
import re
import urllib.parse


def normalize_text(value: str) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


# Params known to be tracking noise, not part of a posting's identity — safe to drop.
# Many ATS platforms (Greenhouse's gh_jid, Lever's lever-id, etc.) encode the actual job
# identifier in the query string, so we must keep unrecognized params rather than
# stripping the whole query, or distinct postings collapse onto the same hash.
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "src",
}


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlsplit(url.strip().lower())
    path = parsed.path.rstrip("/")

    kept_params = [
        (k, v) for k, v in urllib.parse.parse_qsl(parsed.query)
        if k not in _TRACKING_PARAMS
    ]
    query = urllib.parse.urlencode(sorted(kept_params))

    base = f"{parsed.scheme}://{parsed.netloc}{path}"
    return f"{base}?{query}" if query else base


def truncate(text: str, length: int = 280) -> str:
    text = text or ""
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"
