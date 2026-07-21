"""Slack incoming-webhook notifier (optional)."""
import requests

from app.config import settings


def is_configured() -> bool:
    return bool(settings.slack_enabled and settings.slack_webhook_url)


def send_slack(message: str) -> tuple[bool, str]:
    if not is_configured():
        return False, "Slack notifications are not enabled/configured in .env"

    try:
        resp = requests.post(settings.slack_webhook_url, json={"text": message}, timeout=10)
        resp.raise_for_status()
        return True, ""
    except requests.exceptions.RequestException as exc:
        return False, str(exc)
