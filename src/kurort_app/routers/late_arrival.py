"""Late-arrival preparation and the next shift's paper/key check."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
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


def _who(r):
    return r.primary_guest.full_name if r.primary_guest else r.code


def _page(request, session, r, error=None, chosen=""):
    late = session.scalar(select(LateArrival).where(LateArrival.reservation_id == r.id))
    response = templates.TemplateResponse(
        request,
        "late_arrival/prepare.html",
        {
            "r": r,
            "late": late,
            "compartments": late_arrival.available_compartments(session),
            "error": error,
            "chosen": chosen,
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
    done = f"/spaetanreise/{r.id}"
    late = session.scalar(select(LateArrival).where(LateArrival.reservation_id == r.id))
    if late and late.status != "abgebrochen":
        # A reload or second click of the same form: show the stay as it is now.
        return RedirectResponse(done, status_code=303)
    form = await request.form()
    chosen = str(form.get("compartment_id") or "")
    try:
        if not chosen.isdigit():
            raise ValueError("Bitte ein Safe-Fach wählen.")
        late, _pin = late_arrival.prepare(
            session,
            r,
            int(chosen),
            form.get("key_in_safe") == "on",
            form.get("meldeschein_in_safe") == "on",
            settings=request.app.state.settings,
        )
    except (ValueError, engine.CheckinError) as exc:
        session.rollback()
        return _page(request, session, r, error=str(exc), chosen=chosen)
    # Post/redirect/get: the page masks the PIN until staff press "PIN anzeigen".
    return redirect_with_notice(
        done, f"Spätanreise für {_who(r)} vorbereitet · {late.compartment.label}"
    )


@router.post("/spaetanreise/{reservation_id}/pin")
def reveal(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    late = _late(session, reservation_id)
    try:
        late_arrival.transition(session, late, "pin_viewed")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    pin = late.compartment.fixed_pin or late.pin
    response = templates.TemplateResponse(
        request, "late_arrival/_pin.html", {"pin": pin, "late": late}
    )
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
        {
            "earlier": late_arrival.morning_records(session, today()),
            "evening": evening,
            "pending": late_arrival.to_prepare(session, today()),
        },
    )


def _done_message(late, action):
    r, fach = late.reservation, late.compartment.label
    if action == "arrived":
        text = f"{_who(r)} eingecheckt" + (f" · Zimmer {r.room.number}" if r.room else "")
        return text + (" · Meldeschein noch ausstehend" if late.status == "angereist" else "")
    if action == "meldeschein_returned":
        text = f"Meldeschein von {_who(r)} abgegeben"
        return text + (" · Spätanreise abgeschlossen" if late.status == "abgeschlossen" else "")
    return {
        "no_show": f"{_who(r)} als nicht angereist markiert – Schlüssel und Meldeschein "
        f"aus {fach} nehmen",
        "cancelled": f"Vorbereitung abgebrochen – Schlüssel und Meldeschein aus {fach} nehmen",
        "phone_notified": "Vermerkt: Gast telefonisch informiert",
    }[action]


def _action(session, rid, action, return_to):
    late = _late(session, rid)
    try:
        late_arrival.transition(session, late, action)
    except (ValueError, engine.CheckinError) as exc:
        session.rollback()
        return redirect_with_notice(return_to, str(exc), "warning")
    return redirect_with_notice(return_to, _done_message(late, action))


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
