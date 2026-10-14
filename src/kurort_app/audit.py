"""Append-only staff audit trail (who did what to which record)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kurort_app.models import AuditEvent


def record(
    session: Session,
    *,
    action: str,
    entity: str,
    entity_id: object,
    summary: str,
    payload: dict[str, Any] | None = None,
    actor: str = "rezeption",
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        summary=summary,
        payload=payload,
    )
    session.add(event)
    return event
