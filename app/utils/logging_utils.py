"""Structured logging setup writing to logs/app.log and logs/scanner.log."""
import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_configured: set[str] = set()


def get_logger(name: str, filename: str = "app.log") -> logging.Logger:
    logger = logging.getLogger(name)
    if name in _configured:
        return logger

    logger.setLevel(logging.INFO)
    log_path = settings.resolved_path(settings.log_dir) / filename
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)

    # Windows consoles often default to a non-UTF-8 codepage; reconfigure stdout so log
    # messages with characters like em-dashes don't get mangled or raise on write.
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    console = logging.StreamHandler(stream)
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(console)

    logger.propagate = False
    _configured.add(name)
    return logger


app_logger = get_logger("bioradar.app", "app.log")
scanner_logger = get_logger("bioradar.scanner", "scanner.log")
