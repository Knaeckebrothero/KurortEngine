"""Safe compartments and the human-confirmed late-arrival routine."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app.models import SafeCompartment

DEFAULT_SAFE_COMPARTMENTS = ("Fach 1", "Fach 2", "Fach 3")


def ensure_safe_compartments(session: Session) -> None:
    existing = set(session.scalars(select(SafeCompartment.label)))
    for position, label in enumerate(DEFAULT_SAFE_COMPARTMENTS):
        if label not in existing:
            session.add(SafeCompartment(label=label, active=True, position=position))
    session.flush()
