"""Append-only staff audit trail (who did what to which record)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kurort_app.auth import current_actor
from kurort_app.models import AuditEvent

# Actor for events without a logged-in user (auth off, CLI seed).
DEFAULT_ACTOR = "rezeption"


def record(
    session: Session,
    *,
    action: str,
    entity: str,
    entity_id: object,
    summary: str,
    payload: dict[str, Any] | None = None,
    actor: str | None = None,
) -> AuditEvent:
    """Record an event; the actor defaults to the logged-in staff member."""
    event = AuditEvent(
        actor=actor or current_actor.get() or DEFAULT_ACTOR,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        summary=summary,
        payload=payload,
    )
    session.add(event)
    return event
