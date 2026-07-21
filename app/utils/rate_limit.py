"""Lightweight per-company rate limiting and jitter helpers for scanning."""
import random
import time
from threading import Lock

_last_request_at: dict[str, float] = {}
_lock = Lock()

MIN_SECONDS_BETWEEN_REQUESTS = 5.0


def wait_for_slot(key: str, min_interval_seconds: float = MIN_SECONDS_BETWEEN_REQUESTS) -> None:
    """Blocks the caller until at least min_interval_seconds have passed since the last
    request for this key (e.g. a company name or domain). Keeps per-company scans from
    hammering the same site even if the scheduler queues several in a row."""
    with _lock:
        now = time.monotonic()
        last = _last_request_at.get(key, 0.0)
        wait_time = min_interval_seconds - (now - last)
        if wait_time > 0:
            time.sleep(wait_time)
        _last_request_at[key] = time.monotonic()


def jitter_sleep(min_seconds: float = 1.0, max_seconds: float = 4.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))
