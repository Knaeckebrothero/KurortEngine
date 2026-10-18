"""Reservations: list/search, detail, new reservation, edit/cancel, room plan."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from kurort_app import audit
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import (
    CANCELLED,
    CHANNELS,
    CHECKED_IN,
    CHECKED_OUT,
    MELDESCHEIN_SIGNED,
    NO_SHOW,
    RESERVED,
    AuditEvent,
    Guest,
    Reservation,
    ReservationGuest,
    Room,
)
from kurort_app.services.availability import NON_BLOCKING, free_rooms, occupied_room_ids
from kurort_app.services.seminar import plan_rows as seminar_plan_rows
from kurort_app.web import CHANNEL_LABELS, fmt_date, redirect_with_notice, templates
from kurort_engine.kurpaket_templates import TEMPLATES as KURPAKETE

router = APIRouter()

PAGE_SIZE = 50
PLAN_DAYS = 14
MAX_NIGHTS = 90
EXTRA_GUEST_SLOTS = 3

STATUS_FILTERS = (
    ("", "Alle"),
    (RESERVED, "Reserviert"),
    (CHECKED_IN, "Im Haus"),
    (CHECKED_OUT, "Abgereist"),
    (CANCELLED, "Storniert"),
)
ROOM_CATEGORY_ORDER = ("Einzelzimmer", "Doppelzimmer", "Komfort-Doppelzimmer", "Suite")
COUNTRIES = (
    ("DE", "Deutschland"),
    ("AT", "Österreich"),
    ("CH", "Schweiz"),
    ("NL", "Niederlande"),
    ("BE", "Belgien"),
    ("LU", "Luxemburg"),
    ("FR", "Frankreich"),
    ("IT", "Italien"),
    ("ES", "Spanien"),
    ("PL", "Polen"),
    ("CZ", "Tschechien"),
    ("DK", "Dänemark"),
    ("SE", "Schweden"),
    ("GB", "Vereinigtes Königreich"),
    ("US", "Vereinigte Staaten"),
)
BAND_LABELS = {
    "adult": "Erwachsene",
    "adult_disabled_70": "Erwachsene · GdB ab 70",
    "youth": "Jugendliche 6–15",
    "youth_disabled_70": "Jugendliche · GdB ab 70",
    "child": "Kinder bis 5",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    """ISO (2026-10-14, from <input type=date>) or German (14.10.2026)."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: str | None) -> time | None:
    value = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value or default)
    except ValueError:
        return default


def _age(birth: date | None, anchor: date) -> int | None:
    if birth is None:
        return None
    return anchor.year - birth.year - ((anchor.month, anchor.day) < (birth.month, birth.day))


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _wants_partial(request: Request) -> bool:
    return bool(request.headers.get("HX-Request")) and not request.headers.get(
        "HX-History-Restore-Request"
    )


def _load_reservation(session: Session, reservation_id: int) -> Reservation | None:
    return session.scalar(
        select(Reservation)
        .options(
            selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
            selectinload(Reservation.room),
            selectinload(Reservation.kurtaxe),
        )
        .where(Reservation.id == reservation_id)
    )


def _not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "reservations/not_found.html", {}, status_code=404)


# ---------------------------------------------------------------------------
# List / search
# ---------------------------------------------------------------------------


@router.get("/reservierungen", response_class=HTMLResponse)
def reservation_list(
    request: Request,
    q: str = "",
    status: str = "",
    von: str = "",
    bis: str = "",
    alle: str = "",
    seite: str = "1",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    day = today()
    q = q.strip()
    status = status if status in dict(STATUS_FILTERS) else ""
    arrival_from, arrival_to = _parse_date(von), _parse_date(bis)
    include_past = bool(alle) or bool(q) or arrival_from is not None or arrival_to is not None

    conditions: list[Any] = []
    if q:
        pattern = _like(q)
        guest_match = (
            select(ReservationGuest.reservation_id)
            .join(Guest, Guest.id == ReservationGuest.guest_id)
            .where(
                or_(
                    Guest.first_name.ilike(pattern, escape="\\"),
                    Guest.last_name.ilike(pattern, escape="\\"),
                    (Guest.first_name + " " + Guest.last_name).ilike(pattern, escape="\\"),
                )
            )
        )
        room_match = select(Room.id).where(Room.number == q)
        conditions.append(
            or_(
                Reservation.id.in_(guest_match),
                Reservation.code.ilike(pattern, escape="\\"),
                Reservation.room_id.in_(room_match),
            )
        )
    if arrival_from:
        conditions.append(Reservation.arrival >= arrival_from)
    if arrival_to:
        conditions.append(Reservation.arrival <= arrival_to)
    if not include_past:
        conditions.append(Reservation.departure >= day)

    counts = dict(
        session.execute(
            select(Reservation.status, func.count()).where(*conditions).group_by(Reservation.status)
        ).all()
    )
    chip_counts = {key: counts.get(key, 0) for key, _ in STATUS_FILTERS if key}
    chip_counts[""] = sum(counts.values())

    filtered = [*conditions, Reservation.status == status] if status else conditions
    total = session.scalar(select(func.count()).select_from(Reservation).where(*filtered)) or 0
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(1, _parse_int(seite, 1)), pages)

    is_past = case((Reservation.departure < day, 1), else_=0)
    current_arrival = case((Reservation.departure >= day, Reservation.arrival))
    rows = session.scalars(
        select(Reservation)
        .options(
            selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
            selectinload(Reservation.room),
        )
        .where(*filtered)
        .order_by(is_past, current_arrival.asc(), Reservation.arrival.desc(), Reservation.id)
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()

    params = {"q": q, "status": status, "von": von, "bis": bis, "alle": alle}

    def list_url(**overrides: Any) -> str:
        merged = {**params, **overrides}
        if merged.get("seite") in (1, "1"):
            merged.pop("seite")
        query = {k: v for k, v in merged.items() if v not in ("", None)}
        return "/reservierungen" + (f"?{urlencode(query)}" if query else "")

    context = {
        "rows": rows,
        "q": q,
        "status": status,
        "von": von,
        "bis": bis,
        "alle": alle,
        "include_past": include_past,
        "default_window": not include_past,
        "status_filters": STATUS_FILTERS,
        "chip_counts": chip_counts,
        "total": total,
        "page": page,
        "pages": pages,
        "list_url": list_url,
        "today": day,
    }
    template = "reservations/_results.html" if _wants_partial(request) else "reservations/list.html"
    return templates.TemplateResponse(request, template, context)


# ---------------------------------------------------------------------------
# New reservation
# ---------------------------------------------------------------------------


@dataclass
class StayInput:
    arrival: date | None = None
    departure: date | None = None
    room: Room | None = None
    channel: str = "direct"
    eta: time | None = None
    package_code: str | None = None
    notes: str | None = None
    errors: dict[str, str] = field(default_factory=dict)


def _rooms_by_number(session: Session) -> dict[str, Room]:
    return {room.number: room for room in session.scalars(select(Room).order_by(Room.number))}


def _validate_stay(
    session: Session,
    form: dict[str, str],
    *,
    party_size: int,
    exclude_reservation_id: int | None = None,
    original_arrival: date | None = None,
) -> StayInput:
    """Validate the stay half of the new/edit forms (German messages)."""
    day = today()
    stay = StayInput()
    errors = stay.errors

    raw_arrival, raw_departure = form.get("anreise", ""), form.get("abreise", "")
    stay.arrival, stay.departure = _parse_date(raw_arrival), _parse_date(raw_departure)
    if not raw_arrival.strip():
        errors["anreise"] = "Anreise fehlt."
    elif stay.arrival is None:
        errors["anreise"] = "Anreisedatum ist ungültig."
    elif stay.arrival < day and stay.arrival != original_arrival:
        errors["anreise"] = "Anreise liegt in der Vergangenheit."
    if not raw_departure.strip():
        errors["abreise"] = "Abreise fehlt."
    elif stay.departure is None:
        errors["abreise"] = "Abreisedatum ist ungültig."
    elif stay.arrival and stay.departure <= stay.arrival:
        errors["abreise"] = "Abreise muss nach der Anreise liegen."
    elif stay.arrival and (stay.departure - stay.arrival).days > MAX_NIGHTS:
        errors["abreise"] = f"Aufenthalt ist länger als {MAX_NIGHTS} Nächte."

    number = form.get("zimmer", "").strip()
    stay.room = _rooms_by_number(session).get(number) if number else None
    if not number:
        errors["zimmer"] = "Bitte ein Zimmer wählen."
    elif stay.room is None:
        errors["zimmer"] = f"Zimmer {number} gibt es nicht."
    elif party_size > stay.room.max_occupancy:
        persons = "Person" if stay.room.max_occupancy == 1 else "Personen"
        errors["zimmer"] = (
            f"Zimmer {number} ist für höchstens {stay.room.max_occupancy} {persons} ausgelegt."
        )
    elif (
        stay.arrival
        and stay.departure
        and "anreise" not in errors
        and "abreise" not in errors
        and stay.room.id
        in occupied_room_ids(
            session,
            stay.arrival,
            stay.departure,
            exclude_reservation_id=exclude_reservation_id,
        )
    ):
        errors["zimmer"] = (
            f"Zimmer {number} ist vom {fmt_date(stay.arrival)} bis "
            f"{fmt_date(stay.departure)} bereits belegt."
        )

    channel = form.get("kanal", "direct")
    stay.channel = channel if channel in CHANNELS else "direct"
    raw_eta = form.get("eta", "").strip()
    stay.eta = _parse_time(raw_eta)
    if raw_eta and stay.eta is None:
        errors["eta"] = "Ankunftszeit ist ungültig (Format 14:30)."
    package = form.get("paket", "").strip().upper()
    stay.package_code = package if package in KURPAKETE else None
    stay.notes = form.get("notizen", "").strip() or None
    return stay


def _validate_guests(
    form: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    day = today()
    errors: dict[str, str] = {}
    primary: dict[str, Any] = {
        "first_name": form.get("vorname", "").strip(),
        "last_name": form.get("nachname", "").strip(),
        "street": form.get("strasse", "").strip() or None,
        "postal_code": form.get("plz", "").strip() or None,
        "city": form.get("ort", "").strip() or None,
        "email": form.get("email", "").strip() or None,
        "phone": form.get("telefon", "").strip() or None,
    }
    if not primary["first_name"]:
        errors["vorname"] = "Vorname fehlt."
    if not primary["last_name"]:
        errors["nachname"] = "Nachname fehlt."
    raw_birth = form.get("geburtsdatum", "").strip()
    primary["birth_date"] = _parse_date(raw_birth)
    if raw_birth and primary["birth_date"] is None:
        errors["geburtsdatum"] = "Geburtsdatum ist ungültig."
    elif primary["birth_date"] and primary["birth_date"] > day:
        errors["geburtsdatum"] = "Geburtsdatum liegt in der Zukunft."
    if primary["email"] and "@" not in primary["email"]:
        errors["email"] = "E-Mail-Adresse ist ungültig."
    codes = {code for code, _ in COUNTRIES}
    nationality = form.get("nationalitaet", "DE").strip().upper()
    country = form.get("land", "DE").strip().upper()
    primary["nationality"] = nationality if nationality in codes else "DE"
    primary["country"] = country if country in codes else "DE"

    extras: list[dict[str, Any]] = []
    for slot in range(1, EXTRA_GUEST_SLOTS + 1):
        prefix = f"mitreisende_{slot}_"
        first = form.get(prefix + "vorname", "").strip()
        last = form.get(prefix + "nachname", "").strip()
        raw = form.get(prefix + "geburtsdatum", "").strip()
        if not (first or last or raw):
            continue
        birth = _parse_date(raw)
        if not first:
            errors[prefix + "vorname"] = "Vorname der mitreisenden Person fehlt."
        if raw and birth is None:
            errors[prefix + "geburtsdatum"] = "Geburtsdatum ist ungültig."
        elif birth and birth > day:
            errors[prefix + "geburtsdatum"] = "Geburtsdatum liegt in der Zukunft."
        extras.append(
            {"first_name": first, "last_name": last or primary["last_name"], "birth_date": birth}
        )
    return primary, extras, errors


def _next_code(session: Session, arrival: date) -> str:
    serial = (session.scalar(select(func.max(Reservation.id))) or 0) + 1
    while True:
        code = f"R-{arrival:%y%m}-{serial:04d}"
        if session.scalar(select(Reservation.id).where(Reservation.code == code)) is None:
            return code
        serial += 1


def _room_field_context(
    session: Session,
    *,
    raw_arrival: str,
    raw_departure: str,
    selected: str,
    exclude_reservation_id: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    arrival, departure = _parse_date(raw_arrival), _parse_date(raw_departure)
    all_rooms = session.scalars(select(Room).order_by(Room.number)).all()
    span_ok = bool(arrival and departure and departure > arrival)
    if span_ok:
        free = free_rooms(
            session, arrival, departure, exclude_reservation_id=exclude_reservation_id
        )
    else:
        free = list(all_rooms)
    free_numbers = {room.number for room in free}
    options = list(free)
    selected_room = next((room for room in all_rooms if room.number == selected), None)
    selected_taken = bool(selected_room and span_ok and selected not in free_numbers)
    if selected_taken:
        options.append(selected_room)

    groups: dict[str, list[Room]] = {category: [] for category in ROOM_CATEGORY_ORDER}
    for room in options:
        groups.setdefault(room.category, []).append(room)
    nights = (departure - arrival).days if span_ok else None
    price = (
        selected_room.nightly_rate * nights
        if selected_room is not None and nights and not selected_taken
        else None
    )
    return {
        "room_groups": [(category, rooms) for category, rooms in groups.items() if rooms],
        "selected_room": selected,
        "selected_taken": selected_taken,
        "free_count": len(free),
        "room_total": len(all_rooms),
        "span_ok": span_ok,
        "nights": nights,
        "price": price,
        "nightly_rate": selected_room.nightly_rate if selected_room is not None else None,
        "room_error": error,
        "exclude_reservation_id": exclude_reservation_id,
    }


def _form_page(
    request: Request,
    session: Session,
    form: dict[str, str],
    errors: dict[str, str],
    *,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        "form": form,
        "errors": errors,
        "countries": COUNTRIES,
        "channels": [(c, CHANNEL_LABELS.get(c, c)) for c in CHANNELS],
        "packages": list(KURPAKETE.values()),
        "extra_slots": range(1, EXTRA_GUEST_SLOTS + 1),
        "walkin": form.get("kanal") == "walk-in",
        **_room_field_context(
            session,
            raw_arrival=form.get("anreise", ""),
            raw_departure=form.get("abreise", ""),
            selected=form.get("zimmer", ""),
            error=errors.get("zimmer"),
        ),
    }
    return templates.TemplateResponse(
        request, "reservations/new.html", context, status_code=status_code
    )


@router.get("/reservierungen/neu", response_class=HTMLResponse)
def reservation_new(
    request: Request,
    anreise: str = "",
    abreise: str = "",
    zimmer: str = "",
    walkin: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    day = today()
    form: dict[str, str] = {"kanal": "direct", "nationalitaet": "DE", "land": "DE"}
    arrival = _parse_date(anreise)
    if walkin:
        arrival = day
        form["kanal"] = "walk-in"
    if arrival:
        form["anreise"] = arrival.isoformat()
        departure = _parse_date(abreise)
        if departure is None or departure <= arrival:
            departure = arrival + timedelta(days=1)
        form["abreise"] = departure.isoformat()
    if zimmer:
        form["zimmer"] = zimmer.strip()
    return _form_page(request, session, form, {})


@router.get("/reservierungen/verfuegbare-zimmer", response_class=HTMLResponse)
def room_options(
    request: Request,
    anreise: str = "",
    abreise: str = "",
    zimmer: str = "",
    reservierung: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """htmx partial: the room <select> for the chosen dates."""
    exclude = _parse_int(reservierung, 0) or None
    context = _room_field_context(
        session,
        raw_arrival=anreise,
        raw_departure=abreise,
        selected=zimmer.strip(),
        exclude_reservation_id=exclude,
    )
    return templates.TemplateResponse(request, "reservations/_room_field.html", context)


@router.post("/reservierungen/neu", response_class=HTMLResponse)
async def reservation_create(request: Request, session: Session = Depends(get_session)) -> Response:
    form = {key: str(value) for key, value in (await request.form()).items()}
    primary, extras, errors = _validate_guests(form)
    stay = _validate_stay(session, form, party_size=1 + len(extras))
    errors.update(stay.errors)
    if errors:
        return _form_page(request, session, form, errors, status_code=422)

    assert stay.arrival and stay.departure and stay.room  # guaranteed by validation
    lead = Guest(**primary)
    party = [lead] + [
        Guest(
            first_name=extra["first_name"],
            last_name=extra["last_name"],
            birth_date=extra["birth_date"],
            nationality=lead.nationality,
            street=lead.street,
            postal_code=lead.postal_code,
            city=lead.city,
            country=lead.country,
        )
        for extra in extras
    ]
    nights = (stay.departure - stay.arrival).days
    reservation = Reservation(
        code=_next_code(session, stay.arrival),
        room=stay.room,
        arrival=stay.arrival,
        departure=stay.departure,
        status=RESERVED,
        channel=stay.channel,
        eta=stay.eta,
        rate_total=stay.room.nightly_rate * nights,
        package_code=stay.package_code,
        notes=stay.notes,
    )
    for position, guest in enumerate(party):
        reservation.guests.append(
            ReservationGuest(guest=guest, is_primary=position == 0, position=position)
        )
    session.add(reservation)
    session.flush()
    audit.record(
        session,
        action="reservation.created",
        entity="reservation",
        entity_id=reservation.id,
        summary=(
            f"Reservierung {reservation.code} angelegt "
            f"({CHANNEL_LABELS.get(stay.channel, stay.channel)}) – Zimmer {stay.room.number}, "
            f"{fmt_date(stay.arrival)} bis {fmt_date(stay.departure)}, "
            f"{len(party)} {'Person' if len(party) == 1 else 'Personen'}"
        ),
        payload={
            "code": reservation.code,
            "room": stay.room.number,
            "arrival": stay.arrival.isoformat(),
            "departure": stay.departure.isoformat(),
            "guests": len(party),
            "channel": stay.channel,
            "rate_total": str(reservation.rate_total),
        },
    )
    session.commit()
    return redirect_with_notice(
        f"/reservierungen/{reservation.id}",
        f"Reservierung {reservation.code} für {lead.first_name} {lead.last_name} angelegt.",
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


def _guest_rows(reservation: Reservation) -> list[dict[str, Any]]:
    rows = []
    for rg in reservation.guests:
        guest = rg.guest
        warnings: list[str] = []
        if reservation.status in (RESERVED, CHECKED_IN):
            if guest.birth_date is None:
                warnings.append("Geburtsdatum fehlt – für Meldeschein und Kurtaxe erforderlich.")
            if rg.is_primary and not guest.address_line:
                warnings.append("Anschrift fehlt – für den Meldeschein erforderlich.")
            if rg.exemption_category and not rg.exemption_evidence:
                warnings.append(
                    "Befreiungsnachweis fehlt. Nachweis erfassen oder Befreiung entfernen."
                )
        if reservation.status == CHECKED_IN and rg.meldeschein_status != MELDESCHEIN_SIGNED:
            warnings.append("Meldeschein ist nicht unterschrieben.")
        rows.append(
            {
                "rg": rg,
                "guest": guest,
                "age": _age(guest.birth_date, reservation.arrival),
                "warnings": warnings,
            }
        )
    return rows


@router.get("/reservierungen/{reservation_id:int}", response_class=HTMLResponse)
def reservation_detail(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
) -> HTMLResponse:
    reservation = _load_reservation(session, reservation_id)
    if reservation is None:
        return _not_found(request)
    # The stay's history includes the check-in trail, which is recorded per
    # reservation guest (Meldeschein, Kurkarte) and per guest (data changes).
    stay_guest_ids = [str(rg.id) for rg in reservation.guests]
    guest_ids = [str(rg.guest_id) for rg in reservation.guests]
    events = session.scalars(
        select(AuditEvent)
        .where(
            or_(
                (AuditEvent.entity == "reservation")
                & (AuditEvent.entity_id == str(reservation.id)),
                (AuditEvent.entity == "reservation_guest")
                & AuditEvent.entity_id.in_(stay_guest_ids),
                (AuditEvent.entity == "guest") & AuditEvent.entity_id.in_(guest_ids),
            )
        )
        .order_by(AuditEvent.at.desc(), AuditEvent.id.desc())
    ).all()
    guest_rows = _guest_rows(reservation)
    context = {
        "r": reservation,
        "guest_rows": guest_rows,
        "warning_count": sum(len(row["warnings"]) for row in guest_rows),
        "package": KURPAKETE.get((reservation.package_code or "").upper()),
        "events": events,
        "band_labels": BAND_LABELS,
        "today": today(),
        "plan_from": (reservation.arrival - timedelta(days=1)).isoformat(),
    }
    return templates.TemplateResponse(request, "reservations/detail.html", context)


# ---------------------------------------------------------------------------
# Edit / cancel
# ---------------------------------------------------------------------------


def _edit_page(
    request: Request,
    session: Session,
    reservation: Reservation,
    form: dict[str, str],
    errors: dict[str, str],
    *,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        "r": reservation,
        "form": form,
        "errors": errors,
        "channels": [(c, CHANNEL_LABELS.get(c, c)) for c in CHANNELS],
        "packages": list(KURPAKETE.values()),
        **_room_field_context(
            session,
            raw_arrival=form.get("anreise", ""),
            raw_departure=form.get("abreise", ""),
            selected=form.get("zimmer", ""),
            exclude_reservation_id=reservation.id,
            error=errors.get("zimmer"),
        ),
    }
    return templates.TemplateResponse(
        request, "reservations/edit.html", context, status_code=status_code
    )


def _not_editable(reservation: Reservation) -> Response:
    return redirect_with_notice(
        f"/reservierungen/{reservation.id}",
        "Nur reservierte, noch nicht angereiste Aufenthalte können geändert werden.",
        "warning",
    )


@router.get("/reservierungen/{reservation_id:int}/bearbeiten", response_class=HTMLResponse)
def reservation_edit(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
) -> Response:
    reservation = _load_reservation(session, reservation_id)
    if reservation is None:
        return _not_found(request)
    if reservation.status != RESERVED:
        return _not_editable(reservation)
    form = {
        "anreise": reservation.arrival.isoformat(),
        "abreise": reservation.departure.isoformat(),
        "zimmer": reservation.room.number if reservation.room else "",
        "kanal": reservation.channel,
        "eta": reservation.eta.strftime("%H:%M") if reservation.eta else "",
        "paket": reservation.package_code or "",
        "notizen": reservation.notes or "",
    }
    return _edit_page(request, session, reservation, form, {})


@router.post("/reservierungen/{reservation_id:int}/bearbeiten", response_class=HTMLResponse)
async def reservation_update(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
) -> Response:
    reservation = _load_reservation(session, reservation_id)
    if reservation is None:
        return _not_found(request)
    if reservation.status != RESERVED:
        return _not_editable(reservation)
    form = {key: str(value) for key, value in (await request.form()).items()}
    stay = _validate_stay(
        session,
        form,
        party_size=len(reservation.guests),
        exclude_reservation_id=reservation.id,
        original_arrival=reservation.arrival,
    )
    if stay.errors:
        return _edit_page(request, session, reservation, form, stay.errors, status_code=422)

    assert stay.arrival and stay.departure and stay.room
    changes: list[str] = []
    if (stay.arrival, stay.departure) != (reservation.arrival, reservation.departure):
        changes.append(
            f"Zeitraum {fmt_date(reservation.arrival)}–{fmt_date(reservation.departure)} → "
            f"{fmt_date(stay.arrival)}–{fmt_date(stay.departure)}"
        )
    old_room = reservation.room.number if reservation.room else "–"
    if stay.room.number != old_room:
        changes.append(f"Zimmer {old_room} → {stay.room.number}")
    if stay.channel != reservation.channel:
        changes.append(
            f"Kanal {CHANNEL_LABELS.get(reservation.channel, reservation.channel)} → "
            f"{CHANNEL_LABELS.get(stay.channel, stay.channel)}"
        )
    if stay.eta != reservation.eta:
        changes.append(
            "Ankunftszeit "
            + (reservation.eta.strftime("%H:%M") if reservation.eta else "–")
            + " → "
            + (stay.eta.strftime("%H:%M") if stay.eta else "–")
        )
    if stay.package_code != reservation.package_code:
        changes.append(f"Kurpaket {reservation.package_code or '–'} → {stay.package_code or '–'}")
    if stay.notes != reservation.notes:
        changes.append("Notiz geändert")
    if not changes:
        return redirect_with_notice(
            f"/reservierungen/{reservation.id}", "Keine Änderungen vorgenommen.", "info"
        )

    reservation.arrival, reservation.departure = stay.arrival, stay.departure
    reservation.room = stay.room
    reservation.channel, reservation.eta = stay.channel, stay.eta
    reservation.package_code, reservation.notes = stay.package_code, stay.notes
    reservation.rate_total = stay.room.nightly_rate * reservation.nights
    audit.record(
        session,
        action="reservation.updated",
        entity="reservation",
        entity_id=reservation.id,
        summary="Reservierung geändert: " + "; ".join(changes),
        payload={"changes": changes, "rate_total": str(reservation.rate_total)},
    )
    session.commit()
    return redirect_with_notice(
        f"/reservierungen/{reservation.id}", f"Reservierung {reservation.code} gespeichert."
    )


@router.post("/reservierungen/{reservation_id:int}/stornieren", response_class=HTMLResponse)
async def reservation_cancel(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
) -> Response:
    reservation = _load_reservation(session, reservation_id)
    if reservation is None:
        return _not_found(request)
    if reservation.status != RESERVED:
        return _not_editable(reservation)
    reason = str((await request.form()).get("grund", "")).strip()
    reservation.status = CANCELLED
    audit.record(
        session,
        action="reservation.cancelled",
        entity="reservation",
        entity_id=reservation.id,
        summary="Reservierung storniert" + (f": {reason}" if reason else ""),
        payload={"reason": reason or None},
    )
    session.commit()
    room = f" Zimmer {reservation.room.number} ist wieder frei." if reservation.room else ""
    return redirect_with_notice(
        f"/reservierungen/{reservation.id}",
        f"Reservierung {reservation.code} storniert.{room}",
    )


# ---------------------------------------------------------------------------
# Room plan
# ---------------------------------------------------------------------------


@router.get("/zimmerplan", response_class=HTMLResponse)
def room_plan(
    request: Request, von: str = "", session: Session = Depends(get_session)
) -> HTMLResponse:
    day = today()
    start = _parse_date(von) or day - timedelta(days=1)
    end = start + timedelta(days=PLAN_DAYS)
    halves = PLAN_DAYS * 2

    rooms = session.scalars(select(Room).order_by(Room.floor, Room.number)).all()
    stays = session.scalars(
        select(Reservation)
        .options(selectinload(Reservation.guests).selectinload(ReservationGuest.guest))
        .where(
            Reservation.arrival < end,
            Reservation.departure >= start,
            Reservation.status != CANCELLED,
            Reservation.room_id.is_not(None),
        )
        .order_by(Reservation.arrival)
    ).all()

    days = []
    for offset in range(PLAN_DAYS):
        current = start + timedelta(days=offset)
        days.append(
            {
                "date": current,
                "iso": current.isoformat(),
                "column": 2 + 2 * offset,
                "is_today": current == day,
                "is_weekend": current.weekday() >= 5,
                "is_past": current < day,
                "month_start": offset == 0 or current.day == 1,
                "occupied": 0,
                "arrivals": 0,
                "departures": 0,
            }
        )

    bars_by_room: dict[int, list[dict[str, Any]]] = {room.id: [] for room in rooms}
    taken: set[tuple[int, int]] = set()
    for stay in stays:
        blocking = stay.status not in NON_BLOCKING
        for offset, info in enumerate(days):
            current = info["date"]
            if blocking and stay.arrival <= current < stay.departure:
                taken.add((stay.room_id, offset))
                info["occupied"] += 1
            if blocking and stay.arrival == current:
                info["arrivals"] += 1
            if blocking and stay.departure == current:
                info["departures"] += 1
        first_half = 2 * (stay.arrival - start).days + 1
        last_half = 2 * (stay.departure - start).days + 1
        clip_left, clip_right = first_half < 0, last_half > halves
        first_half, last_half = max(first_half, 0), min(last_half, halves)
        if last_half <= first_half:
            continue
        lead = stay.primary_guest
        others = len(stay.guests) - 1
        bars_by_room.setdefault(stay.room_id, []).append(
            {
                "r": stay,
                "start": first_half + 2,
                "end": last_half + 2,
                "clip_left": clip_left,
                "clip_right": clip_right,
                "label": lead.last_name if lead else stay.code,
                "others": others,
                "title": (
                    f"{lead.full_name if lead else '–'}"
                    f"{f' +{others}' if others > 0 else ''} · {stay.code} · "
                    f"{fmt_date(stay.arrival, 'day')}–{fmt_date(stay.departure, 'day')} "
                    f"({stay.nights} {'Nacht' if stay.nights == 1 else 'Nächte'}) · "
                    f"{_STATUS_TEXT.get(stay.status, stay.status)}"
                ),
            }
        )

    floors: list[dict[str, Any]] = []
    for room in rooms:
        if not floors or floors[-1]["floor"] != room.floor:
            floors.append({"floor": room.floor, "rooms": []})
        floors[-1]["rooms"].append(
            {
                "room": room,
                "bars": bars_by_room.get(room.id, []),
                "free": [
                    offset
                    for offset in range(PLAN_DAYS)
                    if (room.id, offset) not in taken and not days[offset]["is_past"]
                ],
            }
        )

    room_count = len(rooms) or 1
    for info in days:
        info["pct"] = round(100 * info["occupied"] / room_count)

    today_info = next((info for info in days if info["is_today"]), None)
    context = {
        "start": start,
        "end": end - timedelta(days=1),
        "days": days,
        "floors": floors,
        "seminar_rows": seminar_plan_rows(session, start, end),
        "room_count": len(rooms),
        "today": day,
        "today_info": today_info,
        "prev_url": f"/zimmerplan?von={(start - timedelta(days=7)).isoformat()}",
        "next_url": f"/zimmerplan?von={(start + timedelta(days=7)).isoformat()}",
        "today_url": "/zimmerplan",
        "is_default_view": start == day - timedelta(days=1),
    }
    return templates.TemplateResponse(request, "reservations/plan.html", context)


_STATUS_TEXT = {
    RESERVED: "Reserviert",
    CHECKED_IN: "Im Haus",
    CHECKED_OUT: "Abgereist",
    NO_SHOW: "No-Show",
    CANCELLED: "Storniert",
}
