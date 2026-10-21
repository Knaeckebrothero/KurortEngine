"""Today's rows and front-desk extension points.

Register a provider by appending it to FLAG_PROVIDERS, CHECKIN_BLOCKERS,
CHECKOUT_WARNINGS or DASHBOARD_NOTICES in a feature module imported at the end
of this module. Providers return lists; they do not replace F1's providers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    MELDESCHEIN_SIGNED,
    NO_SHOW,
    RESERVED,
    Payment,
    Reservation,
    ReservationGuest,
)
from kurort_app.services import engine


@dataclass(frozen=True)
class Flag:
    text: str
    kind: str
    href: str | None = None


@dataclass
class TodayRow:
    kind: str
    reservation: Reservation
    flags: list[Flag]


# Lists that show each guest's Meldeschein status leave this flag out.
UNSIGNED_FLAG = "Unterschrift fehlt"

FlagProvider = Callable[[Session, TodayRow], list[Flag]]
CheckinBlocker = Callable[[Session, Reservation], list[engine.Blocker]]
CheckoutWarning = Callable[[Session, Reservation], list[Flag]]
DashboardNotice = Callable[[Session, date], list[Flag]]


def arrival_flags(session: Session, row: TodayRow) -> list[Flag]:
    if row.kind != "anreise":
        return []
    r = row.reservation
    if r.status in (CHECKED_IN, CHECKED_OUT):
        return [Flag("Angekommen", "success")]
    if r.status == NO_SHOW:
        return [Flag("No-Show", "warning")]
    flags = []
    labels = {
        "birth_date": "Geburtsdatum",
        "first_name": "Vorname",
        "last_name": "Familienname",
        "street": "Adresse",
        "postal_code": "PLZ",
        "city": "Ort",
        "nationality": "Staatsangehörigkeit",
        "id_document_number": "Ausweisnummer",
    }
    missing = sorted(
        {labels.get(key, key) for rg in r.guests for key in engine.guest_data_errors(rg)}
    )
    if missing or not r.guests:
        flags.append(
            Flag(
                "Gästedaten fehlen" + (" · " + " & ".join(missing) if missing else ""),
                "warning",
                f"/check-in/{r.id}/gaeste",
            )
        )
    if any(rg.exemption_category and not (rg.exemption_evidence or "").strip() for rg in r.guests):
        flags.append(
            Flag("Kurtaxe klären · Nachweis fehlt", "danger", f"/check-in/{r.id}/abschluss#kurtaxe")
        )
    if r.room is None:
        flags.append(Flag("Kein Zimmer", "danger", f"/reservierungen/{r.id}/bearbeiten"))
    elif session.scalar(
        select(Reservation.id)
        .where(
            Reservation.id != r.id,
            Reservation.room_id == r.room_id,
            Reservation.departure == r.arrival,
            Reservation.status == CHECKED_IN,
        )
        .limit(1)
    ):
        flags.append(Flag("Zimmer noch belegt", "info"))
    return flags


def departure_flags(session: Session, row: TodayRow) -> list[Flag]:
    if row.kind != "abreise":
        return []
    r = row.reservation
    if r.status == CHECKED_OUT:
        return [Flag("Abgereist", "success")]
    flags = []
    if any(rg.meldeschein_status != MELDESCHEIN_SIGNED for rg in r.guests):
        flags.append(Flag(UNSIGNED_FLAG, "warning", f"/reservierungen/{r.id}#gaeste"))
    if r.kurtaxe is None:
        flags.append(Flag("Kurtaxe fehlt", "warning"))
    return flags


def unsigned_warning(session: Session, reservation: Reservation) -> list[Flag]:
    return [
        Flag(
            f"Meldeschein von {rg.guest.full_name} nicht unterschrieben",
            "warning",
            f"/reservierungen/{reservation.id}#gaeste",
        )
        for rg in reservation.guests
        if rg.meldeschein_status != MELDESCHEIN_SIGNED
    ]


def tax_warning(session: Session, reservation: Reservation) -> list[Flag]:
    return [] if reservation.kurtaxe else [Flag("Kurtaxe noch nicht berechnet", "warning")]


FLAG_PROVIDERS: list[FlagProvider] = [arrival_flags, departure_flags]
CHECKIN_BLOCKERS: list[CheckinBlocker] = []
CHECKOUT_WARNINGS: list[CheckoutWarning] = [unsigned_warning, tax_warning]
DASHBOARD_NOTICES: list[DashboardNotice] = []


def flags_for(session: Session, kind: str, reservation: Reservation) -> list[Flag]:
    row = TodayRow(kind, reservation, [])
    for provider in FLAG_PROVIDERS:
        row.flags.extend(provider(session, row))
    if kind == "anreise" and reservation.status == RESERVED and not row.flags:
        row.flags.append(Flag("Anreisebereit", "success"))
    return row.flags


def _rows(session: Session, day: date, kind: str) -> list[TodayRow]:
    stmt = select(Reservation).options(
        selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
        selectinload(Reservation.room),
        selectinload(Reservation.kurtaxe),
        selectinload(Reservation.payments).selectinload(Payment.method),
    )
    if kind == "anreise":
        stmt = stmt.where(Reservation.arrival == day, Reservation.status != CANCELLED).order_by(
            Reservation.eta.nulls_last(), Reservation.code
        )
    else:
        stmt = stmt.where(
            Reservation.departure == day, Reservation.status.in_((CHECKED_IN, CHECKED_OUT))
        ).order_by(Reservation.code)
    reservations = list(session.scalars(stmt))
    if kind == "abreise":
        reservations.sort(
            key=lambda r: (
                r.status == CHECKED_OUT,
                int(r.room.number) if r.room and r.room.number.isdigit() else 9999,
                r.code,
            )
        )
    return [TodayRow(kind, r, flags_for(session, kind, r)) for r in reservations]


def arrival_rows(session: Session, day: date) -> list[TodayRow]:
    return _rows(session, day, "anreise")


def departure_rows(session: Session, day: date) -> list[TodayRow]:
    return _rows(session, day, "abreise")


def today_rows(session: Session, day: date) -> list[TodayRow]:
    return departure_rows(session, day) + arrival_rows(session, day)


def checkin_blockers(session: Session, reservation: Reservation) -> list[engine.Blocker]:
    return [b for provider in CHECKIN_BLOCKERS for b in provider(session, reservation)]


def checkout_warnings(session: Session, reservation: Reservation) -> list[Flag]:
    return [flag for provider in CHECKOUT_WARNINGS for flag in provider(session, reservation)]


def dashboard_notices(session: Session, day: date) -> list[Flag]:
    return [flag for provider in DASHBOARD_NOTICES for flag in provider(session, day)]


from kurort_app.services import housekeeping, payments  # noqa: E402, F401
