"""App installation lifecycle; records deliberately have no installation FK."""

from sqlalchemy.orm import Session

from kurort_app import audit
from kurort_app.apps.models import AppInstallation
from kurort_app.apps.schema import AppDefinition
from kurort_app.auth import current_actor


def install(session: Session, app: AppDefinition, *, actor: str | None = None):
    existing = session.get(AppInstallation, app.slug)
    if existing is not None:
        return existing
    actor = actor or current_actor.get() or audit.DEFAULT_ACTOR
    row = AppInstallation(slug=app.slug, version=app.version, enabled=True, installed_by=actor)
    session.add(row)
    audit.record(
        session,
        action="app.installed",
        entity="app",
        entity_id=app.slug,
        summary=f"{app.title} installiert",
        actor=actor,
    )
    session.flush()
    return row


def change(session: Session, app: AppDefinition, action: str):
    if action == "installieren":
        return install(session, app)
    row = session.get(AppInstallation, app.slug)
    if row is None:
        return None
    if action == "deinstallieren":
        session.delete(row)
        event, summary = "uninstalled", "deinstalliert – Einträge bleiben erhalten"
    else:
        row.enabled = action == "aktivieren"
        event, summary = ("enabled", "aktiviert") if row.enabled else ("disabled", "deaktiviert")
    audit.record(
        session,
        action=f"app.{event}",
        entity="app",
        entity_id=app.slug,
        summary=f"{app.title} {summary}",
    )
    session.flush()
    return row
