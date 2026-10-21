"""Independent seminar bookings and management of function rooms."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kurort_app import audit
from kurort_app.auth import require_role
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import SPACE_SLOTS, AuditEvent, FunctionSpace, Reservation, SpaceBooking
from kurort_app.services import seminar
from kurort_app.web import (
    MONTHS,
    NAV,
    SLOT_LABELS,
    SPACE_STATUS_LABELS,
    NavItem,
    fmt_date,
    fmt_money,
    redirect_with_notice,
    templates,
)

router = APIRouter()
ICON = '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M8 4v16M16 4v16"/>'
NAV.append(NavItem("/seminarraum", "Seminarraum", ICON, "Planung"))
NAV.append(
    NavItem("/verwaltung/seminarraum", "Seminarraum-Preise", ICON, "Verwaltung", roles=("leitung",))
)


def _date(raw: str) -> date | None:
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _int(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        return 0


def _money(raw: str) -> Decimal | None:
    raw = raw.strip()
    if "," in raw:  # German input: 1.234,50
        raw = raw.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw)
        if (
            not value.is_finite()
            or abs(value) > Decimal("99999999.99")
            or value.as_tuple().exponent < -2
        ):
            return None
        return value
    except InvalidOperation:
        return None


def _money_input(value: Decimal) -> str:
    """A price as staff type it into a form field: 190,00."""
    return f"{value:.2f}".replace(".", ",")


def _spaces(session: Session) -> list[FunctionSpace]:
    return list(
        session.scalars(select(FunctionSpace).order_by(FunctionSpace.position, FunctionSpace.id))
    )


def _booking(session: Session, booking_id: int, *, lock: bool = False) -> SpaceBooking:
    query = select(SpaceBooking).where(SpaceBooking.id == booking_id)
    if lock:
        query = query.with_for_update()
    booking = session.scalar(query)
    if booking is None:
        raise HTTPException(404, "Buchung nicht gefunden.")
    return booking


def _warning(booking: SpaceBooking) -> Response:
    return redirect_with_notice(
        f"/seminarraum/{booking.id}", "Diese Buchung kann nicht mehr geändert werden.", "warning"
    )


def _week_label(day: date) -> str:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    first = (
        f"{monday.day}."
        if monday.month == sunday.month
        else f"{monday.day}. {MONTHS[monday.month - 1]}"
    )
    return f"KW {monday.isocalendar().week:02d} · {first}–{sunday.day}. {MONTHS[sunday.month - 1]} {sunday.year}"


@router.get("/seminarraum", response_class=HTMLResponse)
def booking_list(
    request: Request, von: str = "", vergangene: str = "", session: Session = Depends(get_session)
):
    day = today()
    chosen = _date(von) or day
    start = chosen - timedelta(days=chosen.weekday())
    query = (
        select(SpaceBooking)
        .options(selectinload(SpaceBooking.space))
        .order_by(SpaceBooking.start_date, SpaceBooking.id)
    )
    if vergangene != "1":
        query = query.where(SpaceBooking.end_date >= day)
    bookings = session.scalars(query).all()
    weeks: dict[str, list[SpaceBooking]] = {}
    cancelled = []
    for booking in bookings:
        if booking.status == "storniert":
            cancelled.append(booking)
        else:
            weeks.setdefault(_week_label(booking.start_date), []).append(booking)
    rows = seminar.week_rows(session, start)
    return templates.TemplateResponse(
        request,
        "seminar/list.html",
        {
            "weeks": weeks,
            "cancelled": cancelled,
            "week_rows": rows,
            "show_rooms": len(rows) > 1,
            "today": day,
            "start": start,
            "end": start + timedelta(days=6),
            "include_past": vergangene == "1",
            "prev": (start - timedelta(days=7)).isoformat(),
            "next": (start + timedelta(days=7)).isoformat(),
            "catering_text": seminar.catering_text,
        },
    )


def _form_page(
    request: Request,
    session: Session,
    form: dict[str, str],
    errors: dict[str, str],
    booking: SpaceBooking | None = None,
    status_code: int = 200,
):
    spaces = [s for s in _spaces(session) if s.active or (booking and s.id == booking.space_id)]
    selected = next((s for s in spaces if str(s.id) == form.get("raum")), None)
    first, last = _date(form.get("von", "")), _date(form.get("bis", "") or form.get("von", ""))
    slot = form.get("zeit", "ganztags")
    hint = "Preis wird aus Zeitraum und Raumpreis berechnet."
    if selected and first and last and 0 <= (last - first).days < 14:
        days = (last - first).days + 1
        rate = selected.price_full_day if slot == "ganztags" else selected.price_half_day
        hint = f"{days} × {'Ganztag' if slot == 'ganztags' else 'Halbtag'} à {fmt_money(rate)}"
    return templates.TemplateResponse(
        request,
        "seminar/form.html",
        {
            "form": form,
            "errors": errors,
            "booking": booking,
            "spaces": spaces,
            "hint": hint,
            "slots": SPACE_SLOTS,
            "rates": {
                str(s.id): {"half": str(s.price_half_day), "full": str(s.price_full_day)}
                for s in spaces
            },
        },
        status_code=status_code,
    )


@router.get("/seminarraum/neu", response_class=HTMLResponse)
def booking_new(
    request: Request,
    raum: str = "",
    von: str = "",
    zeit: str = "ganztags",
    session: Session = Depends(get_session),
):
    spaces = [s for s in _spaces(session) if s.active]
    start = _date(von) or today()
    form = {
        "raum": raum or (str(spaces[0].id) if spaces else ""),
        "von": start.isoformat(),
        "bis": start.isoformat(),
        "zeit": zeit if zeit in SPACE_SLOTS else "ganztags",
        "status": "angefragt",
    }
    return _form_page(request, session, form, {})


def _validate(
    session: Session, form: dict[str, str], booking: SpaceBooking | None = None
) -> tuple[dict, dict[str, str]]:
    errors = {}
    values = {}
    for field, column, limit in (
        ("veranstalter", "organizer_name", 160),
        ("firma", "company", 160),
        ("email", "email", 160),
        ("telefon", "phone", 40),
    ):
        raw = form.get(field, "").strip()
        values[column] = raw or None
        if len(raw) > limit:
            errors[field] = f"Bitte höchstens {limit} Zeichen eingeben."
    if not values["organizer_name"]:
        errors["veranstalter"] = "Veranstalter fehlt."
    if not (values["email"] or values["phone"]):
        errors["email"] = "Bitte E-Mail oder Telefon angeben."
    first = _date(form.get("von", ""))
    last = _date(form.get("bis", "") or form.get("von", ""))
    if first is None:
        errors["von"] = "Bitte ein gültiges Von-Datum angeben."
    elif first < today() and (booking is None or booking.start_date != first):
        errors["von"] = "Beginn liegt in der Vergangenheit."
    if last is None:
        errors["bis"] = "Bitte ein gültiges Bis-Datum angeben."
    elif first and last < first:
        errors["bis"] = "Bis muss am oder nach Von liegen."
    elif first and (last - first).days >= 14:
        errors["bis"] = "Eine Buchung darf höchstens 14 Tage dauern."
    slot = form.get("zeit", "")
    if slot not in SPACE_SLOTS:
        errors["zeit"] = "Bitte Vormittag, Nachmittag oder Ganztags wählen."
    # The room lock serialises availability checks and writes for this room.
    space = session.scalar(
        select(FunctionSpace)
        .where(FunctionSpace.id == _int(form.get("raum", "")))
        .with_for_update()
    )
    if space is None:
        errors["raum"] = "Bitte einen gültigen Raum wählen."
    elif not space.active:
        errors["raum"] = "Dieser Raum ist nicht aktiv."
    attendees = _int(form.get("personen", ""))
    if attendees < 1:
        errors["personen"] = "Bitte mindestens eine Person angeben."
    elif space and attendees > space.capacity:
        errors["personen"] = (
            f"Der {space.name} ist für höchstens {space.capacity} Personen ausgelegt."
        )
    code = form.get("reservierung", "").strip()
    reservation = (
        session.scalar(select(Reservation).where(Reservation.code == code)) if code else None
    )
    if code and reservation is None:
        errors["reservierung"] = "Reservierung wurde nicht gefunden."
    elif reservation and reservation.status == "cancelled":
        errors["reservierung"] = "Diese Reservierung ist storniert."
    raw_price = form.get("preis", "").strip()
    price = _money(raw_price) if raw_price else None
    if raw_price and price is None:
        errors["preis"] = "Bitte einen gültigen Preis angeben."
    elif price is not None and price < 0:
        errors["preis"] = "Preis darf nicht negativ sein."
    if booking is None:
        status = form.get("status", "angefragt")
        if status not in ("angefragt", "bestaetigt"):
            errors["status"] = "Bitte Angefragt oder Bestätigt wählen."
        values["status"] = status
    if not errors:
        clash = seminar.find_clash(
            session, space.id, first, last, slot, exclude_booking_id=booking.id if booking else None
        )
        if clash:
            overlap = max(first, clash.start_date)
            half = slot if clash.slot == "ganztags" else clash.slot
            label = {
                "vormittag": "vormittags",
                "nachmittag": "nachmittags",
                "ganztags": "ganztags",
            }[half]
            status = SPACE_STATUS_LABELS.get(clash.status, clash.status).lower()
            errors["zeit"] = (
                f"{space.name} ist am {fmt_date(overlap)} {label} bereits gebucht ({clash.display_name}, {status})."
            )
    values.update(
        space_id=space.id if space else None,
        start_date=first,
        end_date=last,
        slot=slot,
        attendees=attendees,
        reservation_id=reservation.id if reservation else None,
        price_manual=bool(raw_price),
        price=price,
    )
    for field, column in (
        ("kaffee", "catering_coffee"),
        ("mittagessen", "catering_lunch"),
        ("getraenke", "catering_drinks"),
    ):
        values[column] = form.get(field) == "on"
    values["catering_note"] = form.get("verpflegung_notiz", "").strip() or None
    values["notes"] = form.get("notizen", "").strip() or None
    if not errors and price is None:
        values["price"] = seminar.calculate_price(space, first, last, slot)
    return values, errors


def _record(session: Session, booking: SpaceBooking, action: str, verb: str) -> None:
    audit.record(
        session,
        action=f"space_booking.{action}",
        entity="space_booking",
        entity_id=booking.id,
        summary=(
            f"{booking.space.name} {fmt_date(booking.start_date)} "
            f"{SLOT_LABELS.get(booking.slot, booking.slot)} für {booking.display_name} {verb}"
        ),
    )


@router.post("/seminarraum/neu", response_class=HTMLResponse)
async def booking_create(request: Request, session: Session = Depends(get_session)):
    form = {k: str(v) for k, v in (await request.form()).items()}
    values, errors = _validate(session, form)
    if errors:
        return _form_page(request, session, form, errors, status_code=422)
    booking = SpaceBooking(**values)
    session.add(booking)
    session.flush()
    _record(session, booking, "created", "angelegt")
    session.commit()
    return redirect_with_notice(f"/seminarraum/{booking.id}", "Buchung angelegt.")


@router.get("/seminarraum/{booking_id:int}", response_class=HTMLResponse)
def booking_detail(request: Request, booking_id: int, session: Session = Depends(get_session)):
    booking = _booking(session, booking_id)
    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity == "space_booking", AuditEvent.entity_id == str(booking.id))
        .order_by(AuditEvent.at.desc(), AuditEvent.id.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "seminar/detail.html",
        {"b": booking, "events": events, "catering_text": seminar.catering_text},
    )


def _booking_form(booking: SpaceBooking) -> dict[str, str]:
    return {
        "raum": str(booking.space_id),
        "von": booking.start_date.isoformat(),
        "bis": booking.end_date.isoformat(),
        "zeit": booking.slot,
        "veranstalter": booking.organizer_name,
        "firma": booking.company or "",
        "email": booking.email or "",
        "telefon": booking.phone or "",
        "personen": str(booking.attendees),
        "preis": _money_input(booking.price) if booking.price_manual else "",
        "reservierung": booking.reservation.code if booking.reservation else "",
        "kaffee": "on" if booking.catering_coffee else "",
        "mittagessen": "on" if booking.catering_lunch else "",
        "getraenke": "on" if booking.catering_drinks else "",
        "verpflegung_notiz": booking.catering_note or "",
        "notizen": booking.notes or "",
    }


@router.get("/seminarraum/{booking_id:int}/bearbeiten", response_class=HTMLResponse)
def booking_edit(request: Request, booking_id: int, session: Session = Depends(get_session)):
    booking = _booking(session, booking_id)
    if booking.status == "storniert":
        return _warning(booking)
    return _form_page(request, session, _booking_form(booking), {}, booking)


@router.post("/seminarraum/{booking_id:int}/bearbeiten", response_class=HTMLResponse)
async def booking_update(
    request: Request, booking_id: int, session: Session = Depends(get_session)
):
    booking = _booking(session, booking_id, lock=True)
    if booking.status == "storniert":
        return _warning(booking)
    form = {k: str(v) for k, v in (await request.form()).items()}
    values, errors = _validate(session, form, booking)
    if errors:
        return _form_page(request, session, form, errors, booking, 422)
    for key, value in values.items():
        setattr(booking, key, value)
    session.flush()
    session.expire(booking, ["space"])
    _record(session, booking, "updated", "geändert")
    session.commit()
    return redirect_with_notice(f"/seminarraum/{booking.id}", "Buchung gespeichert.")


@router.post("/seminarraum/{booking_id:int}/bestaetigen")
def booking_confirm(booking_id: int, session: Session = Depends(get_session)):
    booking = _booking(session, booking_id, lock=True)
    if booking.status != "angefragt":
        return _warning(booking)
    booking.status = "bestaetigt"
    _record(session, booking, "confirmed", "bestätigt")
    session.commit()
    return redirect_with_notice(f"/seminarraum/{booking.id}", "Buchung bestätigt.")


@router.post("/seminarraum/{booking_id:int}/stornieren")
async def booking_cancel(
    request: Request, booking_id: int, session: Session = Depends(get_session)
):
    booking = _booking(session, booking_id, lock=True)
    if booking.status == "storniert":
        return _warning(booking)
    booking.status = "storniert"
    booking.cancelled_at = datetime.now(UTC)
    booking.cancel_reason = str((await request.form()).get("grund", "")).strip() or None
    _record(
        session,
        booking,
        "cancelled",
        "storniert" + (f": {booking.cancel_reason}" if booking.cancel_reason else ""),
    )
    session.commit()
    return redirect_with_notice(
        f"/seminarraum/{booking.id}", "Buchung storniert. Der Zeitraum ist wieder frei."
    )


def _settings_page(
    request: Request,
    session: Session,
    *,
    errors: dict | None = None,
    form: dict | None = None,
    editing: int | None = None,
    status_code: int = 200,
):
    reviewed = session.scalar(
        select(AuditEvent.id).where(AuditEvent.action == "function_space.updated").limit(1)
    )
    return templates.TemplateResponse(
        request,
        "seminar/settings.html",
        {
            "spaces": _spaces(session),
            "placeholder": reviewed is None,
            "errors": errors or {},
            "form": form or {},
            "editing": editing,
        },
        status_code=status_code,
    )


@router.get(
    "/verwaltung/seminarraum",
    dependencies=[Depends(require_role("leitung"))],
    response_class=HTMLResponse,
)
def space_settings(request: Request, session: Session = Depends(get_session)):
    return _settings_page(request, session)


async def _save_space(request: Request, session: Session, space: FunctionSpace | None = None):
    form = {k: str(v) for k, v in (await request.form()).items()}
    errors = {}
    name = form.get("name", "").strip()
    capacity = _int(form.get("kapazitaet", ""))
    half, full = _money(form.get("halbtag", "")), _money(form.get("ganztag", ""))
    if not name or len(name) > 80:
        errors["name"] = "Bitte einen Raumnamen mit höchstens 80 Zeichen angeben."
    duplicate = session.scalar(select(FunctionSpace).where(FunctionSpace.name == name))
    if duplicate and (space is None or duplicate.id != space.id):
        errors["name"] = "Ein Raum mit diesem Namen ist bereits vorhanden."
    if not 1 <= capacity <= 2147483647:
        errors["kapazitaet"] = "Bitte eine gültige Kapazität ab 1 angeben."
    for field, value in (("halbtag", half), ("ganztag", full)):
        if value is None or value < 0:
            errors[field] = "Bitte einen gültigen Preis ab 0 angeben."
    if errors:
        return _settings_page(
            request,
            session,
            errors=errors,
            form=form,
            editing=space.id if space else 0,
            status_code=422,
        )
    action = "updated" if space else "created"
    if space is None:
        space = FunctionSpace(position=len(_spaces(session)))
        session.add(space)
    space.name, space.capacity = name, capacity
    space.price_half_day, space.price_full_day = half, full
    space.active = form.get("aktiv") == "on"
    session.flush()
    audit.record(
        session,
        action=f"function_space.{action}",
        entity="function_space",
        entity_id=space.id,
        summary=f"Raum {space.name} {'geändert' if action == 'updated' else 'angelegt'}",
        payload={
            "half_day": str(half),
            "full_day": str(full),
            "capacity": capacity,
            "active": space.active,
        },
    )
    session.commit()
    return redirect_with_notice("/verwaltung/seminarraum", "Raum gespeichert.")


@router.post(
    "/verwaltung/seminarraum/neu",
    dependencies=[Depends(require_role("leitung"))],
    response_class=HTMLResponse,
)
async def space_create(request: Request, session: Session = Depends(get_session)):
    return await _save_space(request, session)


@router.post(
    "/verwaltung/seminarraum/{space_id:int}",
    dependencies=[Depends(require_role("leitung"))],
    response_class=HTMLResponse,
)
async def space_update(request: Request, space_id: int, session: Session = Depends(get_session)):
    space = session.scalar(
        select(FunctionSpace).where(FunctionSpace.id == space_id).with_for_update()
    )
    if space is None:
        raise HTTPException(404, "Raum nicht gefunden.")
    return await _save_space(request, session, space)
