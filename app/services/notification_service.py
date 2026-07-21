"""Formats and dispatches notifications across configured channels, respecting the
minimum fit-score threshold, and logs every attempt to the notifications table."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, Opportunity
from app.notifications.email_notifier import send_email
from app.notifications.slack_notifier import send_slack
from app.notifications.telegram_notifier import send_telegram
from app.services.opportunity_service import mark_notification_sent
from app.utils.logging_utils import app_logger
from app.utils.text_cleaning import truncate


def format_email_body(opp: Opportunity) -> str:
    priority_tag = "HIGH PRIORITY — " if opp.fit_score >= 80 else ""
    return (
        f"{priority_tag}New Internship Opportunity Found\n\n"
        f"Company: {opp.company_name}\n"
        f"Role: {opp.job_title}\n"
        f"Location: {opp.location or 'Not specified'}\n"
        f"Fit Score: {opp.fit_score}\n"
        f"Detected: {opp.detected_date.strftime('%Y-%m-%d %I:%M %p')}\n\n"
        f"Job Link:\n{opp.job_url or 'Not available'}\n\n"
        f"Matched Keywords: {opp.matched_keywords or 'None'}\n\n"
        f"Why it may be relevant:\n{opp.fit_score_explanation or 'See dashboard for details.'}\n\n"
        f"Dashboard Link: {settings.dashboard_url}\n\n"
        "Suggested next action: Review role, generate tailored resume, and consider applying today."
    )


def format_short_message(opp: Opportunity) -> str:
    return (
        f"New Internship: {opp.company_name} — {opp.job_title}\n"
        f"Fit Score: {opp.fit_score} | Location: {opp.location or 'N/A'}\n"
        f"{opp.job_url}"
    )


def notify_new_opportunity(session: Session, opp: Opportunity) -> None:
    """Sends a notification across all enabled channels if the opportunity meets the
    minimum fit-score threshold. Always logs the attempt (even if skipped) for visibility."""
    if opp.fit_score < settings.min_notification_fit_score:
        app_logger.info(f"Skipping notification for {opp.company_name} - {opp.job_title}: fit_score {opp.fit_score} below threshold")
        return

    subject = f"New Internship Found: {opp.company_name} — {opp.job_title}"
    email_body = format_email_body(opp)
    short_message = format_short_message(opp)

    any_sent = False

    if settings.email_enabled:
        success, error = send_email(subject, email_body)
        _log_notification(session, opp.id, "email", settings.email_to, success, error, email_body)
        any_sent = any_sent or success

    if settings.telegram_enabled:
        success, error = send_telegram(short_message)
        _log_notification(session, opp.id, "telegram", settings.telegram_chat_id, success, error, short_message)
        any_sent = any_sent or success

    if settings.slack_enabled:
        success, error = send_slack(short_message)
        _log_notification(session, opp.id, "slack", "slack_webhook", success, error, short_message)
        any_sent = any_sent or success

    if any_sent:
        mark_notification_sent(session, opp.id)


def _log_notification(session: Session, opportunity_id: int, channel: str, recipient: str, success: bool, error: str, message: str) -> None:
    notif = Notification(
        opportunity_id=opportunity_id,
        channel=channel,
        recipient=recipient,
        sent_at=datetime.utcnow(),
        status="sent" if success else "failed",
        error_message=error,
        message_preview=truncate(message, 300),
    )
    session.add(notif)
    session.flush()
    if not success:
        app_logger.warning(f"Notification via {channel} failed for opportunity {opportunity_id}: {error}")


def send_test_notification(channel: str) -> tuple[bool, str]:
    test_message = "BioInternshipRadar test notification — if you received this, the channel is configured correctly."
    if channel == "email":
        return send_email("BioInternshipRadar Test Notification", test_message)
    if channel == "telegram":
        return send_telegram(test_message)
    if channel == "slack":
        return send_slack(test_message)
    return False, f"Unknown channel: {channel}"
