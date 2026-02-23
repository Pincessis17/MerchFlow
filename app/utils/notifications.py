import json
import smtplib
from email.message import EmailMessage

from flask import current_app

from .. import db
from ..models import PlatformNotification, TenantNotification


def _payload_json(payload: dict | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def create_platform_notification(
    *,
    event_type: str,
    title: str,
    message: str,
    company_id: int | None = None,
    payload: dict | None = None,
    category: str = "info",
):
    notification = PlatformNotification(
        company_id=company_id,
        category=category,
        event_type=event_type,
        title=title,
        message=message,
        payload_json=_payload_json(payload),
    )
    db.session.add(notification)
    return notification


def create_tenant_notification(
    *,
    company_id: int,
    event_type: str,
    title: str,
    message: str,
    payload: dict | None = None,
    category: str = "info",
):
    notification = TenantNotification(
        company_id=company_id,
        category=category,
        event_type=event_type,
        title=title,
        message=message,
        payload_json=_payload_json(payload),
    )
    db.session.add(notification)
    return notification


def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    host = current_app.config.get("SMTP_HOST")
    port = int(current_app.config.get("SMTP_PORT") or 587)
    username = current_app.config.get("SMTP_USERNAME")
    password = current_app.config.get("SMTP_PASSWORD")
    from_email = current_app.config.get("SMTP_FROM_EMAIL") or username
    use_tls = bool(current_app.config.get("SMTP_USE_TLS"))

    if not host or not to_email or not from_email:
        current_app.logger.info("SMTP not configured; skipped email '%s' to %s", subject, to_email)
        return False

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(host=host, port=port, timeout=8) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return True
    except Exception as exc:  # pragma: no cover - network edge
        current_app.logger.warning("Email notification failed: %s", exc)
        return False
