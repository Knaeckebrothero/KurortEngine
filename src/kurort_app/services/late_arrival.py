"""Safe compartments and the human-confirmed late-arrival routine."""

import secrets
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kurort_app import audit
from kurort_app.auth import current_actor
from kurort_app.config import get_settings
from kurort_app.config import today as business_today
from kurort_app.models import (
    CHECKED_IN,
    MELDESCHEIN_SIGNED,
    NO_SHOW,
    RESERVED,
    EmailMessageRow,
    EmailTemplate,
    LateArrival,
    Reservation,
    SafeCompartment,
)
from kurort_app.services import engine, mail, mail_templates, today

DEFAULT_SAFE_COMPARTMENTS = ("Fach 1", "Fach 2", "Fach 3")


def ensure_safe_compartments(session: Session) -> None:
    existing = set(session.scalars(select(SafeCompartment.label)))
    for position, label in enumerate(DEFAULT_SAFE_COMPARTMENTS):
        if label not in existing:
            session.add(SafeCompartment(label=label, active=True, position=position))
    session.flush()


def generate_pin() -> str:
    while True:
        pin = "".join(str(secrets.randbelow(10)) for _ in range(4))
        if len(set(pin)) > 1 and pin not in "0123456789" and pin not in "9876543210":
            return pin


def record(session, r, action, summary, payload=None):
    audit.record(
        session,
        action="late_arrival_" + action,
        entity="reservation",
        entity_id=r.id,
        summary=summary,
        payload=payload,
    )


def available_compartments(session: Session) -> list[SafeCompartment]:
    occupied = select(LateArrival.compartment_id).where(LateArrival.status == "vorbereitet")
    return list(
        session.scalars(
            select(SafeCompartment)
            .where(SafeCompartment.active, SafeCompartment.id.not_in(occupied))
            .order_by(SafeCompartment.position, SafeCompartment.id)
        )
    )


def prepare(
    session: Session,
    r: Reservation,
    compartment_id: int,
    key_in_safe: bool,
    meldeschein_in_safe: bool,
    *,
    settings=None,
) -> tuple[LateArrival, str]:
    if r.status != RESERVED or r.arrival != business_today():
        raise ValueError("Nur heutige reservierte Anreisen können vorbereitet werden.")
    if not r.guests or any(
        rg.meldeschein_status not in ("gedruckt", MELDESCHEIN_SIGNED) for rg in r.guests
    ):
        raise ValueError("Meldeschein erst in AVS drucken")
    if not r.room:
        raise ValueError("Bitte zuerst ein Zimmer zuweisen.")
    if not key_in_safe or not meldeschein_in_safe:
        raise ValueError("Bitte Schlüssel und Meldeschein im Safe hinterlegen und bestätigen.")
    c = session.scalar(
        select(SafeCompartment).where(SafeCompartment.id == compartment_id).with_for_update()
    )
    if not c or not c.active:
        raise ValueError("Bitte ein aktives Safe-Fach wählen.")
    if session.scalar(
        select(LateArrival.id).where(
            LateArrival.compartment_id == c.id, LateArrival.status == "vorbereitet"
        )
    ):
        raise ValueError("Dieses Safe-Fach ist bereits belegt.")
    late = session.scalar(select(LateArrival).where(LateArrival.reservation_id == r.id))
    if late and late.status != "abgebrochen":
        raise ValueError("Diese Spätanreise wurde bereits bearbeitet.")
    pin = c.fixed_pin or generate_pin()
    address = r.primary_guest.email if r.primary_guest else None
    message = None
    if address:
        t = session.scalar(
            select(EmailTemplate).where(EmailTemplate.key == "spaetanreise", EmailTemplate.active)
        )
        if not t:
            raise ValueError("Die Systemvorlage Spätanreise fehlt.")
        subject, body = mail_templates.render(
            t.subject, t.body, mail_templates.context_for(r, {"fach": c.label, "pin": pin})
        )
        if pin in subject:
            raise ValueError("Der Safe-PIN darf nur im Nachrichtentext stehen, nicht im Betreff.")
        message = EmailMessageRow(
            reservation_id=r.id,
            template_key=t.key,
            to_address=mail.validate_recipient(address),
            subject=subject,
            body=body,
            created_by=current_actor.get() or "rezeption",
        )
        session.add(message)
        session.flush()
    late = late or LateArrival(reservation_id=r.id)
    late.compartment_id, late.pin = c.id, None if c.fixed_pin else pin
    late.status, late.key_in_safe, late.meldeschein_in_safe = "vorbereitet", True, True
    late.prepared_at, late.prepared_by = datetime.now(UTC), current_actor.get() or "rezeption"
    late.closed_at = late.phone_notified_at = late.arrived_confirmed_at = (
        late.meldeschein_returned_at
    ) = None
    late.email_message_id = message.id if message else None
    session.add(late)
    record(
        session,
        r,
        "prepared",
        "Spätanreise vorbereitet",
        {"compartment": c.label, "fixed": bool(c.fixed_pin)},
    )
    session.commit()
    if message:
        mail.send(session, message, settings=settings)
    return late, pin


def clear_pin(session: Session, late: LateArrival) -> None:
    pin = late.compartment.fixed_pin or late.pin
    if pin:
        for message in session.scalars(
            select(EmailMessageRow).where(
                EmailMessageRow.reservation_id == late.reservation_id,
                EmailMessageRow.template_key == "spaetanreise",
            )
        ):
            message.body = message.body.replace(pin, "••••")
    late.pin = None
    late.key_in_safe = late.meldeschein_in_safe = False


def transition(session: Session, late: LateArrival, action: str) -> None:
    r, now = late.reservation, datetime.now(UTC)
    if (
        action in ("arrived", "no_show", "cancelled", "phone_notified", "pin_viewed")
        and late.status != "vorbereitet"
    ):
        raise ValueError("Diese Spätanreise ist nicht mehr vorbereitet.")
    if action == "arrived":
        if r.status != RESERVED:
            raise ValueError("Der Aufenthalt ist nicht mehr reserviert.")
        engine.assess_kurtaxe(session, r)
        r.status, r.checked_in_at = CHECKED_IN, now
        late.arrived_confirmed_at = now
        late.status = (
            "abgeschlossen"
            if late.meldeschein_returned_at
            or all(g.meldeschein_status == MELDESCHEIN_SIGNED for g in r.guests)
            else "angereist"
        )
        clear_pin(session, late)
        if late.status == "abgeschlossen":
            late.closed_at = now
    elif action == "meldeschein_returned":
        if late.status not in ("vorbereitet", "angereist"):
            raise ValueError("Diese Spätanreise ist bereits abgeschlossen.")
        for rg in r.guests:
            rg.meldeschein_status, rg.meldeschein_signed_at = MELDESCHEIN_SIGNED, now
        late.meldeschein_returned_at = now
        if late.status == "angereist":
            late.status, late.closed_at = "abgeschlossen", now
    elif action in ("no_show", "cancelled"):
        if r.status != RESERVED:
            raise ValueError("Der Aufenthalt ist nicht mehr reserviert.")
        if action == "no_show":
            r.status = NO_SHOW
        late.status, late.closed_at = (
            ("nicht_angereist" if action == "no_show" else "abgebrochen"),
            now,
        )
        clear_pin(session, late)
    elif action == "phone_notified":
        late.phone_notified_at = now
    elif action != "pin_viewed":
        raise ValueError("Unbekannte Aktion.")
    labels = {
        "arrived": "Spätanreise angekommen",
        "meldeschein_returned": "Meldeschein abgegeben",
        "no_show": "Spätanreise nicht angereist",
        "cancelled": "Spätanreise abgebrochen",
        "phone_notified": "Gast telefonisch informiert",
        "pin_viewed": "Safe-PIN angezeigt",
    }
    record(session, r, action, labels[action])
    session.commit()


def morning_records(session: Session, day: date) -> list[LateArrival]:
    return list(
        session.scalars(
            select(LateArrival)
            .join(Reservation)
            .options(selectinload(LateArrival.reservation), selectinload(LateArrival.compartment))
            .where(Reservation.arrival < day, LateArrival.status.in_(("vorbereitet", "angereist")))
            .order_by(Reservation.arrival, LateArrival.id)
        )
    )


def late_flags(session: Session, row: today.TodayRow) -> list[today.Flag]:
    r = row.reservation
    if row.kind != "anreise" or r.status != RESERVED or r.arrival != business_today():
        return []
    late = session.scalar(
        select(LateArrival).where(
            LateArrival.reservation_id == r.id, LateArrival.status == "vorbereitet"
        )
    )
    if late:
        return [today.Flag("Spätanreise vorbereitet · " + late.compartment.label, "info")]
    if r.eta is not None and r.eta >= get_settings().late_arrival_from:
        return [
            today.Flag(
                f"Spätanreise {r.eta:%H:%M} · vorbereiten", "warning", f"/spaetanreise/{r.id}"
            )
        ]
    return []


def morning_notice(session: Session, day: date) -> list[today.Flag]:
    count = len(morning_records(session, day))
    if not count:
        return []
    return [
        today.Flag(
            f"{count} "
            + ("Spätanreise" if count == 1 else "Spätanreisen")
            + ": Meldeschein ausstehend",
            "warning",
            "/spaetanreisen",
        )
    ]


today.FLAG_PROVIDERS.append(late_flags)
today.DASHBOARD_NOTICES.append(morning_notice)
