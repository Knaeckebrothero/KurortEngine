"""Synchronous plain-text mail with a durable queued row before network I/O."""

import re
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from sqlalchemy.orm import Session

from kurort_app import audit
from kurort_app.config import Settings, get_settings
from kurort_app.models import EmailMessageRow


def validate_settings(settings: Settings) -> None:
    if settings.mail_transport != "smtp":
        return
    missing = [
        name for name in ("smtp_host", "smtp_from") if not (getattr(settings, name) or "").strip()
    ]
    if missing:
        raise ValueError(
            "E-Mail-Versand benötigt: " + ", ".join("KURORT_" + name.upper() for name in missing)
        )
    if any(c in (settings.smtp_from or "") for c in "\r\n"):
        raise ValueError("KURORT_SMTP_FROM muss eine Zeile sein.")


def validate_recipient(address: str) -> str:
    address = address.strip()
    if len(address) > 160 or not re.fullmatch(
        r"[^\s@<>;,\x00-\x1f]+@[^\s@<>;,\x00-\x1f]+\.[^\s@<>;,\x00-\x1f]+", address
    ):
        raise ValueError("Bitte eine gültige E-Mail-Adresse angeben.")
    return address


def _event(session: Session, row: EmailMessageRow, action: str) -> None:
    audit.record(
        session,
        action=action,
        entity="reservation",
        entity_id=row.reservation_id or "entfernt",
        summary={
            "email_sent": "E-Mail gesendet",
            "email_logged": "E-Mail protokolliert – nicht versendet",
            "email_failed": "E-Mail fehlgeschlagen",
            "email_retried": "E-Mail erneut gesendet",
        }[action],
        payload={
            "message_id": row.id,
            "template_key": row.template_key,
            "recipient": row.to_address,
        },
    )


def send(
    session: Session, message: EmailMessageRow, *, settings: Settings | None = None
) -> EmailMessageRow:
    settings = settings or get_settings()
    validate_settings(settings)
    message.to_address = validate_recipient(message.to_address)
    wire = EmailMessage()
    wire["From"] = settings.smtp_from or "Hotel Rheinland <noreply@example.invalid>"
    wire["To"] = message.to_address
    wire["Subject"] = message.subject
    wire["Date"] = format_datetime(datetime.now(UTC))
    wire["Message-ID"] = make_msgid()
    wire.set_content(message.body, charset="utf-8")
    retry = (message.attempts or 0) > 0
    message.attempts = (message.attempts or 0) + 1
    message.transport = settings.mail_transport
    message.status, message.error, message.sent_at = "queued", None, None
    session.add(message)
    session.flush()
    if retry:
        _event(session, message, "email_retried")
    session.commit()
    if settings.mail_transport == "log":
        message.status = "logged"
    else:
        try:
            smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
            with smtp_class(settings.smtp_host, settings.smtp_port, timeout=10) as connection:
                if settings.smtp_security == "starttls":
                    connection.starttls(context=ssl.create_default_context())
                if settings.smtp_user:
                    connection.login(settings.smtp_user, settings.smtp_password or "")
                connection.send_message(wire)
            message.status = "sent"
        except (smtplib.SMTPException, OSError) as exc:
            message.status = "failed"
            # A server may echo mail content (including a safe code) in its reply.
            message.error = (
                "SMTP-Versand fehlgeschlagen (" + type(exc).__name__ + ")."
                if message.template_key == "spaetanreise"
                else str(exc)
            )
    if message.status in ("sent", "logged"):
        message.sent_at = datetime.now(UTC)
    _event(
        session,
        message,
        {"sent": "email_sent", "logged": "email_logged", "failed": "email_failed"}[message.status],
    )
    session.commit()
    return message
