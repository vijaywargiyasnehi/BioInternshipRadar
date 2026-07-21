"""SMTP email notifier."""
import smtplib
from email.mime.text import MIMEText

from app.config import settings


def is_configured() -> bool:
    return bool(
        settings.email_enabled and settings.smtp_username and settings.smtp_password and settings.email_to
    )


def send_email(subject: str, body: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    if not is_configured():
        return False, "Email notifications are not enabled/configured in .env"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.email_from or settings.smtp_username
    msg["To"] = settings.email_to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(msg["From"], [settings.email_to], msg.as_string())
        return True, ""
    except Exception as exc:
        return False, str(exc)
