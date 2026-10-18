"""Late-arrival preparation and the next shift's paper/key check."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app.auth import require_role
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import LateArrival, Reservation
from kurort_app.services import engine, late_arrival
from kurort_app.services import today as today_service
from kurort_app.web import redirect_with_notice, templates

router = APIRouter(dependencies=[Depends(require_role("rezeption", "leitung"))])


def reservation(session, rid):
    r = session.scalar(select(Reservation).where(Reservation.id == rid).with_for_update())
    if not r:
        raise HTTPException(404, "Reservierung nicht gefunden.")
    return r


def _late(session, rid):
    # Serialize all lifecycle actions for a stay, including PIN reveal and retry.
    reservation(session, rid)
    row = session.scalar(
        select(LateArrival).where(LateArrival.reservation_id == rid).with_for_update()
    )
    if row is None:
        raise HTTPException(404, "Keine Spätanreise vorbereitet.")
    return row


def _page(request, session, r, error=None, pin=None):
    late = session.scalar(select(LateArrival).where(LateArrival.reservation_id == r.id))
    response = templates.TemplateResponse(
        request,
        "late_arrival/prepare.html",
        {
            "r": r,
            "late": late,
            "compartments": late_arrival.available_compartments(session),
            "error": error,
            "pin": pin,
            "hints": today_service.checkin_blockers(session, r),
        },
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/spaetanreise/{reservation_id}")
def preparation_page(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    return _page(request, session, reservation(session, reservation_id))


@router.post("/spaetanreise/{reservation_id}")
async def prepare(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    r = reservation(session, reservation_id)
    form = await request.form()
    try:
        compartment_id = int(str(form.get("compartment_id", "0")))
        late, pin = late_arrival.prepare(
            session,
            r,
            compartment_id,
            form.get("key_in_safe") == "on",
            form.get("meldeschein_in_safe") == "on",
            settings=request.app.state.settings,
        )
        late_arrival.transition(session, late, "pin_viewed")
        # Render the once-only PIN directly: no PIN/query flag or session copy in a URL.
        return _page(request, session, r, pin=pin)
    except (ValueError, engine.CheckinError) as exc:
        session.rollback()
        return _page(request, session, r, error=str(exc))


@router.post("/spaetanreise/{reservation_id}/pin")
def reveal(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    late = _late(session, reservation_id)
    try:
        late_arrival.transition(session, late, "pin_viewed")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    pin = late.compartment.fixed_pin or late.pin
    response = templates.TemplateResponse(request, "late_arrival/_pin.html", {"pin": pin})
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/spaetanreisen")
def morning(request: Request, session: Session = Depends(get_session)):
    evening = session.scalars(
        select(LateArrival)
        .join(Reservation)
        .where(Reservation.arrival == today(), LateArrival.status == "vorbereitet")
        .order_by(LateArrival.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "late_arrival/morning.html",
        {"earlier": late_arrival.morning_records(session, today()), "evening": evening},
    )


def _action(session, rid, action, return_to):
    late = _late(session, rid)
    try:
        late_arrival.transition(session, late, action)
    except (ValueError, engine.CheckinError) as exc:
        session.rollback()
        return redirect_with_notice(return_to, str(exc), "warning")
    return redirect_with_notice(return_to, "Spätanreise aktualisiert")


@router.post("/spaetanreise/{reservation_id}/telefonisch")
def phone(reservation_id: int, session: Session = Depends(get_session)):
    return _action(session, reservation_id, "phone_notified", f"/spaetanreise/{reservation_id}")


@router.post("/spaetanreise/{reservation_id}/abbrechen")
def cancel(reservation_id: int, session: Session = Depends(get_session)):
    return _action(session, reservation_id, "cancelled", f"/spaetanreise/{reservation_id}")


@router.post("/spaetanreise/{reservation_id}/angekommen")
def arrived(reservation_id: int, session: Session = Depends(get_session)):
    return _action(session, reservation_id, "arrived", "/spaetanreisen")


@router.post("/spaetanreise/{reservation_id}/meldeschein")
def returned(reservation_id: int, session: Session = Depends(get_session)):
    return _action(session, reservation_id, "meldeschein_returned", "/spaetanreisen")


@router.post("/spaetanreise/{reservation_id}/nicht-angereist")
def no_show(reservation_id: int, session: Session = Depends(get_session)):
    return _action(session, reservation_id, "no_show", "/spaetanreisen")
