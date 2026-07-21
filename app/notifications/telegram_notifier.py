"""Telegram bot notifier (optional)."""
import requests

from app.config import settings


def is_configured() -> bool:
    return bool(settings.telegram_enabled and settings.telegram_bot_token and settings.telegram_chat_id)


def send_telegram(message: str) -> tuple[bool, str]:
    if not is_configured():
        return False, "Telegram notifications are not enabled/configured in .env"

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        resp = requests.post(
            url, json={"chat_id": settings.telegram_chat_id, "text": message}, timeout=10
        )
        resp.raise_for_status()
        return True, ""
    except requests.exceptions.RequestException as exc:
        return False, str(exc)
