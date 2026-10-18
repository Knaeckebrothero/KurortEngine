"""Front desk: today's overview, arrivals, departures, in-house, check-out."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from kurort_app import audit
from kurort_app.auth import require_role
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    NO_SHOW,
    RESERVED,
    Payment,
    Reservation,
    ReservationGuest,
    Room,
)
from kurort_app.services import housekeeping, payments
from kurort_app.services import today as desk
from kurort_app.web import STATUS_LABELS, WEEKDAYS, fmt_date, redirect_with_notice, templates

router = APIRouter(dependencies=[Depends(require_role("rezeption", "leitung"))])

CHART_NIGHTS = 14
CHART_NIGHTS_MIN, CHART_NIGHTS_MAX = 7, 60
CHART_NIGHTS_COOKIE = "kurort_tage"
# Beyond three weeks per-bar labels collide; label Mondays (and today) only.
CHART_DENSE_AFTER = 21
# Statuses that hold a room for a night.
OCCUPYING = (RESERVED, CHECKED_IN, CHECKED_OUT)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _with_relations(stmt):
    return stmt.options(
        selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
        selectinload(Reservation.room),
        selectinload(Reservation.kurtaxe),
        selectinload(Reservation.payments).selectinload(Payment.method),
    )


def _arrivals(session: Session, day: date) -> list[Reservation]:
    stmt = (
        select(Reservation)
        .where(Reservation.arrival == day, Reservation.status != CANCELLED)
        .order_by(Reservation.eta.nulls_last(), Reservation.code)
    )
    return list(session.scalars(_with_relations(stmt)))


def _departures(session: Session, day: date) -> list[Reservation]:
    stmt = (
        select(Reservation)
        .where(Reservation.departure == day, Reservation.status.in_((CHECKED_IN, CHECKED_OUT)))
        .order_by(Reservation.code)
    )
    rows = list(session.scalars(_with_relations(stmt)))
    # Open check-outs first (by room), finished ones after.
    return sorted(rows, key=lambda r: (r.status == CHECKED_OUT, _room_sort_key(r)))


def _in_house(session: Session) -> list[Reservation]:
    stmt = select(Reservation).where(Reservation.status == CHECKED_IN)
    return list(session.scalars(_with_relations(stmt)))


def _room_sort_key(reservation: Reservation) -> tuple[int, str]:
    number = reservation.room.number if reservation.room else ""
    return (int(number) if number.isdigit() else 9999, number)


def _room_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Room)) or 0


def _occupancy_by_night(session: Session, start: date, nights: int) -> list[int]:
    end = start + timedelta(days=nights)
    stays = session.execute(
        select(Reservation.arrival, Reservation.departure).where(
            Reservation.status.in_(OCCUPYING),
            Reservation.arrival < end,
            Reservation.departure > start,
        )
    ).all()
    counts = [0] * nights
    for arrival, departure in stays:
        for offset in range(nights):
            night = start + timedelta(days=offset)
            if arrival <= night < departure:
                counts[offset] += 1
    return counts


# ---------------------------------------------------------------------------
# Occupancy chart geometry (inline SVG, computed server-side)
# ---------------------------------------------------------------------------

CHART_W, CHART_H = 720, 240
CHART_PAD_L, CHART_PAD_R, CHART_PAD_T, CHART_PAD_B = 36, 8, 22, 44


def chart_nights(raw: str | None) -> int:
    """The ``tage`` query parameter, clamped to a sensible chart range."""
    try:
        value = int(raw) if raw else CHART_NIGHTS
    except ValueError:
        return CHART_NIGHTS
    return min(max(value, CHART_NIGHTS_MIN), CHART_NIGHTS_MAX)


def occupancy_chart(counts: list[int], start: date, capacity: int) -> dict:
    capacity = max(capacity, 1)
    plot_w = CHART_W - CHART_PAD_L - CHART_PAD_R
    plot_h = CHART_H - CHART_PAD_T - CHART_PAD_B
    slot = plot_w / len(counts)
    bar_w = slot * 0.62
    top = max(capacity, max(counts, default=0))
    dense = len(counts) > CHART_DENSE_AFTER
    bars = []
    for i, count in enumerate(counts):
        night = start + timedelta(days=i)
        h = plot_h * count / top
        x = CHART_PAD_L + i * slot + (slot - bar_w) / 2
        bars.append(
            {
                "x": round(x, 1),
                "y": round(CHART_PAD_T + plot_h - h, 1),
                "w": round(bar_w, 1),
                "h": round(h, 1),
                "cx": round(x + bar_w / 2, 1),
                "count": count,
                "pct": round(100 * count / capacity),
                "weekday": WEEKDAYS[night.weekday()],
                "day": f"{night:%d.%m.}",
                "date": night,
                "is_today": i == 0,
                "weekend": night.weekday() >= 5,
                "labelled": not dense or i == 0 or night.weekday() == 0,
            }
        )
    gridlines = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        value = round(top * frac)
        gridlines.append(
            {"y": round(CHART_PAD_T + plot_h - plot_h * value / top, 1), "label": value}
        )
    peak = max(bars, key=lambda b: b["count"]) if bars else None
    return {
        "width": CHART_W,
        "height": CHART_H,
        "pad_l": CHART_PAD_L,
        "pad_r": CHART_PAD_R,
        "baseline": CHART_PAD_T + plot_h,
        "label_y": CHART_PAD_T + plot_h + 18,
        "label2_y": CHART_PAD_T + plot_h + 34,
        "capacity_y": round(CHART_PAD_T + plot_h - plot_h * capacity / top, 1),
        "capacity": capacity,
        "bars": bars,
        "gridlines": gridlines,
        "peak": peak,
        "dense": dense,
        "average_pct": round(100 * sum(counts) / (capacity * len(counts))) if counts else 0,
    }


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def _parse_day(raw: str | None) -> date:
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return today()


@router.get("/anreisen", response_class=HTMLResponse)
def arrivals_page(
    request: Request,
    tag: str | None = None,
    filter: str = "alle",  # noqa: A002 - query parameter name
    session: Session = Depends(get_session),
) -> HTMLResponse:
    day = _parse_day(tag)
    business_day = today()
    all_rows = _arrivals(session, day)
    open_rows = [r for r in all_rows if r.status == RESERVED]
    arrived_rows = [r for r in all_rows if r.status in (CHECKED_IN, CHECKED_OUT)]
    if filter == "offen":
        rows = open_rows
    elif filter == "angekommen":
        rows = arrived_rows
    else:
        filter = "alle"  # noqa: A001
        rows = open_rows + arrived_rows + [r for r in all_rows if r.status == NO_SHOW]
    context = {
        "day": day,
        "is_today": day == business_day,
        "can_check_in": day <= business_day,
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
        "rows": rows,
        "filter": filter,
        "counts": {"alle": len(all_rows), "offen": len(open_rows), "angekommen": len(arrived_rows)},
        "flags": {r.id: desk.flags_for(session, "anreise", r) for r in all_rows},
        "guest_total": sum(len(r.guests) for r in all_rows),
    }
    return templates.TemplateResponse(request, "front_desk/arrivals.html", context)


@router.get("/abreisen", response_class=HTMLResponse)
def departures_page(
    request: Request, tag: str | None = None, session: Session = Depends(get_session)
) -> HTMLResponse:
    day = _parse_day(tag)
    rows = _departures(session, day)
    context = {
        "day": day,
        "is_today": day == today(),
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
        "rows": rows,
        "open_count": sum(1 for r in rows if r.status == CHECKED_IN),
        "done_count": sum(1 for r in rows if r.status == CHECKED_OUT),
        "flags": {r.id: desk.flags_for(session, "abreise", r) for r in rows},
        "balance": {r.id: payments.balance(r) for r in rows},
    }
    return templates.TemplateResponse(request, "front_desk/departures.html", context)


IN_HOUSE_SORTS = {
    "zimmer": _room_sort_key,
    "abreise": lambda r: (r.departure, _room_sort_key(r)),
    "gast": lambda r: (r.primary_guest.last_name if r.primary_guest else "", _room_sort_key(r)),
}


@router.get("/im-haus", response_class=HTMLResponse)
def in_house_page(
    request: Request, sort: str = "zimmer", session: Session = Depends(get_session)
) -> HTMLResponse:
    if sort not in IN_HOUSE_SORTS:
        sort = "zimmer"
    day = today()
    rows = sorted(_in_house(session), key=IN_HOUSE_SORTS[sort])
    context = {
        "rows": rows,
        "sort": sort,
        "day": day,
        "room_count": len({r.room_id for r in rows if r.room_id is not None}),
        "guest_count": sum(len(r.guests) for r in rows),
        "departing_today": sum(1 for r in rows if r.departure <= day),
        "remaining": {r.id: (r.departure - day).days for r in rows},
        "flags": {r.id: desk.flags_for(session, "abreise", r) for r in rows},
        "capacity": _room_count(session),
    }
    return templates.TemplateResponse(request, "front_desk/in_house.html", context)


def _get_reservation(session: Session, reservation_id: int) -> Reservation:
    reservation = session.scalar(
        _with_relations(select(Reservation).where(Reservation.id == reservation_id))
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")
    return reservation


@router.get("/check-out/{reservation_id}", response_class=HTMLResponse)
def checkout_page(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
) -> HTMLResponse:
    reservation = _get_reservation(session, reservation_id)
    context = {
        "r": reservation,
        "balance": payments.balance(reservation),
        "warnings": desk.checkout_warnings(session, reservation),
        "can_check_out": reservation.status == CHECKED_IN,
        "early": reservation.departure > today(),
        "day": today(),
    }
    context.update(
        payments.form_context(session, reservation, next_path=f"/check-out/{reservation.id}")
    )
    return templates.TemplateResponse(request, "front_desk/checkout.html", context)


@router.post("/check-out/{reservation_id}")
def checkout(reservation_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    reservation = _get_reservation(session, reservation_id)
    guest = reservation.primary_guest
    name = guest.full_name if guest else reservation.code
    if reservation.status != CHECKED_IN:
        state = STATUS_LABELS.get(reservation.status, reservation.status)
        return redirect_with_notice(
            "/abreisen",
            f"Check-out nicht möglich: {name} ({reservation.code}) ist „{state}“, nicht im Haus.",
            "danger",
        )
    reservation.status = CHECKED_OUT
    reservation.checked_out_at = datetime.now(UTC)
    housekeeping.mark_dirty_after_checkout(session, reservation)
    room = reservation.room.number if reservation.room else None
    balance = payments.balance(reservation)
    audit.record(
        session,
        action="check_out",
        entity="reservation",
        entity_id=reservation.id,
        summary=f"{name} ({reservation.code}) ausgecheckt" + (f" · Zimmer {room}" if room else ""),
        payload={
            "code": reservation.code,
            "room": room,
            "departure": reservation.departure.isoformat(),
            "early": reservation.departure > today(),
            "open": str(balance.open),
            "room_total": str(balance.room),
            "kurtaxe": str(balance.kurtaxe) if balance.kurtaxe is not None else None,
        },
    )
    session.commit()
    suffix = f" · Zimmer {room} ist frei" if room else ""
    return redirect_with_notice("/abreisen", f"{name} ausgecheckt{suffix} ({fmt_date(today())}).")
