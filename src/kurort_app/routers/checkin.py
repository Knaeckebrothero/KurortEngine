"""Check-in flow: guests → Meldeschein → Kurtaxe → Kurkarte → completion.

Each step is its own URL; the reservation only becomes ``checked_in`` when
the last step is confirmed. Regulatory work (forms, tax, Kurkarte) is done
by ``kurort_app.services.engine`` on top of ``kurort_engine``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from starlette.datastructures import FormData

from kurort_app import audit
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import (
    CHECKED_IN,
    EXEMPTION_CATEGORIES,
    RESERVED,
    Guest,
    Reservation,
    ReservationGuest,
)
from kurort_app.services import engine
from kurort_app.services.checkin_qr import qr_svg
from kurort_app.web import STATUS_LABELS, fmt_date, fmt_money, redirect_with_notice, templates

router = APIRouter()

COUNTRIES: tuple[tuple[str, str], ...] = (
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
GUEST_FIELDS = (
    "first_name",
    "last_name",
    "birth_date",
    "nationality",
    "street",
    "postal_code",
    "city",
    "country",
    "id_document_number",
    "disability_pct",
)
# Changing any of these after a Meldeschein exists makes the form stale.
MELDESCHEIN_RELEVANT = (
    "first_name",
    "last_name",
    "birth_date",
    "nationality",
    "street",
    "postal_code",
    "city",
    "country",
    "id_document_number",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _open(session: Session, reservation_id: int) -> Reservation | RedirectResponse:
    """The reservation if it can be checked in, else a redirect explaining why."""
    reservation = engine.load_reservation(session, reservation_id)
    if reservation is None:
        return redirect_with_notice("/anreisen", "Reservierung nicht gefunden.", "danger")
    detail = f"/reservierungen/{reservation.id}"
    if reservation.status != RESERVED:
        label = STATUS_LABELS.get(reservation.status, reservation.status)
        return redirect_with_notice(
            detail, f"Check-in nicht möglich – Reservierung ist im Status „{label}“.", "warning"
        )
    if reservation.arrival > today():
        return redirect_with_notice(
            detail,
            f"Anreise erst am {fmt_date(reservation.arrival)} – Check-in frühestens am Anreisetag.",
            "warning",
        )
    return reservation


def _find_guest(reservation: Reservation, rg_id: int) -> ReservationGuest | None:
    return next((rg for rg in reservation.guests if rg.id == rg_id), None)


def _step_url(reservation: Reservation, step: str) -> str:
    return f"/check-in/{reservation.id}/{step}"


def _stepper(reservation: Reservation, current: str, state: dict[str, list[engine.Blocker]]):
    steps = []
    for number, (key, label) in enumerate(engine.STEPS, start=1):
        done = not state[key] and key != "abschluss"
        status = "current" if key == current else ("done" if done else "open")
        steps.append(
            {
                "key": key,
                "label": label,
                "number": number,
                "status": status,
                "done": done,
                "href": _step_url(reservation, key),
                "open_count": len(state[key]),
            }
        )
    return steps


def _render(
    request: Request,
    template: str,
    reservation: Reservation,
    step: str,
    **extra: Any,
) -> HTMLResponse:
    state = engine.readiness(reservation)
    keys = engine.STEP_KEYS
    idx = keys.index(step)
    context = {
        "r": reservation,
        "primary": reservation.primary_guest,
        "step": step,
        "steps": _stepper(reservation, step, state),
        "state": state,
        "blockers": state[step],
        "prev_url": _step_url(reservation, keys[idx - 1]) if idx > 0 else None,
        "next_url": _step_url(reservation, keys[idx + 1]) if idx + 1 < len(keys) else None,
        "late_arrival": reservation.arrival < today(),
        "package": engine.PACKAGE_TEMPLATES.get((reservation.package_code or "").upper()),
        "satzung_label": engine.satzung_label(),
    }
    context.update(extra)
    return templates.TemplateResponse(request, template, context)


def _audit_step(session: Session, reservation: Reservation, action: str, summary: str, **payload):
    audit.record(
        session,
        action=action,
        entity="reservation",
        entity_id=reservation.id,
        summary=summary,
        payload={"reservation": reservation.code, **payload} or None,
    )


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


@router.get("/check-in/{reservation_id}")
def start(reservation_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    return RedirectResponse(
        _step_url(reservation, engine.first_open_step(reservation)), status_code=303
    )


# ---------------------------------------------------------------------------
# Step 1 — guests & Meldeschein data
# ---------------------------------------------------------------------------


def _guest_rows(
    reservation: Reservation,
    errors: dict[int, dict[str, str]] | None = None,
    raw: dict[int, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for rg in reservation.guests:
        g = rg.guest
        values = {
            "first_name": g.first_name or "",
            "last_name": g.last_name or "",
            "birth_date": g.birth_date.isoformat() if g.birth_date else "",
            "nationality": (g.nationality or "DE").upper(),
            "street": g.street or "",
            "postal_code": g.postal_code or "",
            "city": g.city or "",
            "country": (g.country or "DE").upper(),
            "id_document_number": g.id_document_number or "",
            "disability_pct": "" if g.disability_pct is None else str(g.disability_pct),
        }
        if raw and rg.id in raw:
            values.update(raw[rg.id])
        row_errors = (errors or {}).get(rg.id)
        if row_errors is None:
            row_errors = engine.guest_data_errors(rg)
        age = None
        if g.birth_date:
            arrival = reservation.arrival
            age = (
                arrival.year
                - g.birth_date.year
                - ((arrival.month, arrival.day) < (g.birth_date.month, g.birth_date.day))
            )
        rows.append({"rg": rg, "v": values, "errors": row_errors, "age": age})
    return rows


@router.get("/check-in/{reservation_id}/gaeste", response_class=HTMLResponse)
def guests_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    return _render(
        request,
        "checkin/gaeste.html",
        reservation,
        "gaeste",
        rows=_guest_rows(reservation),
        countries=COUNTRIES,
    )


def _parse_guest(
    form: FormData, rg: ReservationGuest
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """Form → (clean values, parse errors, raw strings) for one guest."""
    prefix = f"g{rg.id}_"
    raw = {f: str(form.get(prefix + f, "")).strip() for f in GUEST_FIELDS}
    clean: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for f in ("first_name", "last_name", "street", "postal_code", "city", "id_document_number"):
        clean[f] = raw[f] or None
    clean["first_name"] = raw["first_name"]
    clean["last_name"] = raw["last_name"]
    clean["nationality"] = (raw["nationality"] or "DE").upper()[:2]
    clean["country"] = (raw["country"] or "DE").upper()[:2]
    if raw["birth_date"]:
        try:
            clean["birth_date"] = date.fromisoformat(raw["birth_date"])
        except ValueError:
            errors["birth_date"] = "Geburtsdatum im Format TT.MM.JJJJ eingeben."
    else:
        clean["birth_date"] = None
    if raw["disability_pct"]:
        try:
            pct = int(raw["disability_pct"])
            if not 20 <= pct <= 100:
                raise ValueError
            clean["disability_pct"] = pct
        except ValueError:
            errors["disability_pct"] = (
                "GdB als Zahl zwischen 20 und 100 eintragen oder leer lassen."
            )
    else:
        clean["disability_pct"] = None
    return clean, errors, raw


@router.post("/check-in/{reservation_id}/gaeste", response_class=HTMLResponse)
async def guests_save(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    form = await request.form()
    all_errors: dict[int, dict[str, str]] = {}
    raw_values: dict[int, dict[str, str]] = {}
    stale_forms: list[str] = []
    tax_inputs_changed = False

    for rg in reservation.guests:
        clean, parse_errors, raw = _parse_guest(form, rg)
        g: Guest = rg.guest
        changed = [f for f, v in clean.items() if getattr(g, f) != v]
        for f in changed:
            setattr(g, f, clean[f])
        if any(f in MELDESCHEIN_RELEVANT for f in changed) and engine.invalidate_meldeschein(rg):
            stale_forms.append(g.full_name)
        if any(f in ("birth_date", "disability_pct") for f in changed):
            tax_inputs_changed = True
        if changed:
            audit.record(
                session,
                action="guest.updated",
                entity="guest",
                entity_id=g.id,
                summary=f"Gästedaten geändert: {g.full_name}",
                payload={"fields": changed, "reservation": reservation.code},
            )
        errors = {**engine.guest_data_errors(rg), **parse_errors}
        if errors:
            all_errors[rg.id] = errors
            raw_values[rg.id] = raw
    if tax_inputs_changed:
        engine.drop_assessment(session, reservation)
    session.commit()

    if all_errors:
        return _render(
            request,
            "checkin/gaeste.html",
            reservation,
            "gaeste",
            rows=_guest_rows(reservation, all_errors, raw_values),
            countries=COUNTRIES,
            submitted=True,
            stale_forms=stale_forms,
        )
    text = "Gästedaten gespeichert."
    if stale_forms:
        text += f" Meldeschein neu erzeugen für: {', '.join(stale_forms)}."
    return redirect_with_notice(
        _step_url(reservation, "meldeschein"), text, "warning" if stale_forms else "success"
    )


@router.post("/check-in/{reservation_id}/gaeste/hinzufuegen")
async def guests_add(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    form = await request.form()
    first = str(form.get("first_name", "")).strip()
    last = str(form.get("last_name", "")).strip()
    url = _step_url(reservation, "gaeste")
    if not first or not last:
        return redirect_with_notice(
            url, "Vor- und Familienname der mitreisenden Person eintragen.", "danger"
        )
    birth: date | None = None
    if form.get("birth_date"):
        try:
            birth = date.fromisoformat(str(form["birth_date"]))
        except ValueError:
            birth = None
    lead = reservation.primary_guest
    guest = Guest(
        first_name=first,
        last_name=last,
        birth_date=birth,
        nationality=lead.nationality if lead else "DE",
        street=lead.street if lead else None,
        postal_code=lead.postal_code if lead else None,
        city=lead.city if lead else None,
        country=lead.country if lead else "DE",
    )
    position = max((rg.position for rg in reservation.guests), default=-1) + 1
    reservation.guests.append(ReservationGuest(guest=guest, is_primary=False, position=position))
    engine.drop_assessment(session, reservation)
    session.flush()
    _audit_step(session, reservation, "guest.added", f"Mitreisende Person ergänzt: {first} {last}")
    session.commit()
    notice = f"{first} {last} ergänzt – Anschrift von {lead.full_name if lead else 'Hauptgast'} übernommen."
    room = reservation.room
    if room and len(reservation.guests) > room.max_occupancy:
        return redirect_with_notice(
            url,
            f"{notice} Achtung: Zimmer {room.number} ist für {room.max_occupancy} Personen ausgelegt.",
            "warning",
        )
    return redirect_with_notice(url, notice)


@router.post("/check-in/{reservation_id}/gaeste/{rg_id}/entfernen")
def guests_remove(reservation_id: int, rg_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    rg = _find_guest(reservation, rg_id)
    url = _step_url(reservation, "gaeste")
    if rg is None or rg.is_primary:
        return redirect_with_notice(url, "Der Hauptgast kann nicht entfernt werden.", "danger")
    name = rg.guest.full_name
    reservation.guests.remove(rg)
    engine.drop_assessment(session, reservation)
    _audit_step(session, reservation, "guest.removed", f"Mitreisende Person entfernt: {name}")
    session.commit()
    return redirect_with_notice(url, f"{name} von der Reservierung entfernt.")


# ---------------------------------------------------------------------------
# Step 2 — Meldeschein
# ---------------------------------------------------------------------------


def _meldeschein_response(
    request: Request, reservation: Reservation, notice: dict[str, str] | None = None
) -> Response:
    if _is_htmx(request):
        state = engine.readiness(reservation)
        return templates.TemplateResponse(
            request,
            "checkin/_meldeschein_panel.html",
            {
                "r": reservation,
                "blockers": state["meldeschein"],
                "data_blockers": state["gaeste"],
                "next_url": _step_url(reservation, "kurtaxe"),
                "panel_notice": notice,
            },
        )
    url = _step_url(reservation, "meldeschein")
    if notice:
        return redirect_with_notice(url, notice["text"], notice["kind"])
    return RedirectResponse(url, status_code=303)


@router.get("/check-in/{reservation_id}/meldeschein", response_class=HTMLResponse)
def meldeschein_step(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    state = engine.readiness(reservation)
    return _render(
        request,
        "checkin/meldeschein.html",
        reservation,
        "meldeschein",
        data_blockers=state["gaeste"],
    )


@router.post("/check-in/{reservation_id}/meldeschein/{rg_id}/erzeugen")
def meldeschein_generate(
    request: Request, reservation_id: int, rg_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    rg = _find_guest(reservation, rg_id)
    if rg is None:
        return _meldeschein_response(
            request, reservation, {"text": "Gast nicht gefunden.", "kind": "danger"}
        )
    try:
        engine.generate_meldeschein(session, rg)
    except engine.CheckinError as exc:
        session.rollback()
        return _meldeschein_response(
            request, reservation, {"text": f"{rg.guest.full_name}: {exc.message}", "kind": "danger"}
        )
    session.commit()
    return _meldeschein_response(
        request,
        reservation,
        {
            "text": f"Meldeschein für {rg.guest.full_name} erzeugt – zur Unterschrift vorlegen.",
            "kind": "info",
        },
    )


@router.post("/check-in/{reservation_id}/meldeschein/alle")
def meldeschein_generate_all(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    done, failed = [], []
    for rg in reservation.guests:
        if rg.meldeschein_status != "offen":
            continue
        try:
            engine.generate_meldeschein(session, rg)
            done.append(rg.guest.full_name)
        except engine.CheckinError as exc:
            failed.append(f"{rg.guest.full_name}: {exc.message}")
    session.commit()
    if failed:
        notice = {"text": " ".join(failed), "kind": "danger"}
    elif done:
        notice = {
            "text": f"{len(done)} Meldeschein(e) erzeugt – zur Unterschrift vorlegen.",
            "kind": "info",
        }
    else:
        notice = None
    return _meldeschein_response(request, reservation, notice)


@router.post("/check-in/{reservation_id}/meldeschein/{rg_id}/unterschreiben")
def meldeschein_sign(
    request: Request, reservation_id: int, rg_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    rg = _find_guest(reservation, rg_id)
    if rg is None:
        return _meldeschein_response(
            request, reservation, {"text": "Gast nicht gefunden.", "kind": "danger"}
        )
    try:
        engine.sign_meldeschein(session, rg)
    except engine.CheckinError as exc:
        session.rollback()
        return _meldeschein_response(request, reservation, {"text": exc.message, "kind": "danger"})
    session.commit()
    return _meldeschein_response(
        request,
        reservation,
        {"text": f"Unterschrift von {rg.guest.full_name} bestätigt.", "kind": "success"},
    )


@router.get("/meldeschein/{rg_id}.pdf")
def meldeschein_download(rg_id: int, session: Session = Depends(get_session)) -> Response:
    rg = session.get(ReservationGuest, rg_id)
    if rg is None:
        return Response("Meldeschein nicht gefunden.\n", status_code=404, media_type="text/plain")
    try:
        pdf = engine.meldeschein_pdf(session, rg)
    except engine.CheckinError as exc:
        return Response(f"{exc.message}\n", status_code=409, media_type="text/plain")
    if pdf is None:
        return Response(
            "Für diesen Gast wurde noch kein Meldeschein erzeugt.\n",
            status_code=404,
            media_type="text/plain",
        )
    session.commit()
    safe = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in rg.guest.last_name)
    filename = f"Meldeschein-{rg.reservation.code}-{safe}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Step 3 — Kurtaxe
# ---------------------------------------------------------------------------


def _exemption_overrides(
    form: FormData, reservation: Reservation
) -> dict[int, tuple[str | None, str | None]]:
    overrides = {}
    for rg in reservation.guests:
        category = str(form.get(f"ex{rg.id}_category", "")).strip() or None
        if category not in EXEMPTION_CATEGORIES:
            category = None
        evidence = str(form.get(f"ex{rg.id}_evidence", "")).strip() or None
        overrides[rg.id] = (category, evidence)
    return overrides


def _kurtaxe_context(result: engine.KurtaxeResult, reservation: Reservation) -> dict[str, Any]:
    return {
        "result": result,
        "exemption_labels": engine.EXEMPTION_LABELS,
        "exemption_short": engine.EXEMPTION_SHORT,
        "evidence_hints": engine.EVIDENCE_HINTS,
        "assessed": reservation.kurtaxe,
        "satzung": engine.satzung(),
        "band_labels": engine.BAND_LABELS,
    }


@router.get("/check-in/{reservation_id}/kurtaxe", response_class=HTMLResponse)
def kurtaxe_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    result = engine.kurtaxe_preview(reservation)
    return _render(
        request,
        "checkin/kurtaxe.html",
        reservation,
        "kurtaxe",
        **_kurtaxe_context(result, reservation),
    )


@router.post("/check-in/{reservation_id}/kurtaxe/vorschau", response_class=HTMLResponse)
async def kurtaxe_preview(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    overrides = _exemption_overrides(await request.form(), reservation)
    result = engine.kurtaxe_preview(reservation, overrides)
    context = {"r": reservation, **_kurtaxe_context(result, reservation), "preview": True}
    return templates.TemplateResponse(request, "checkin/_kurtaxe_table.html", context)


@router.post("/check-in/{reservation_id}/kurtaxe", response_class=HTMLResponse)
async def kurtaxe_save(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    overrides = _exemption_overrides(await request.form(), reservation)
    changed = False
    for rg in reservation.guests:
        category, evidence = overrides[rg.id]
        if (rg.exemption_category, rg.exemption_evidence) != (category, evidence):
            rg.exemption_category, rg.exemption_evidence = category, evidence
            changed = True
    if changed:
        engine.drop_assessment(session, reservation)
    try:
        assessment = engine.assess_kurtaxe(session, reservation)
    except engine.CheckinError as exc:
        session.commit()  # keep the entered exemptions; they are not the problem
        result = engine.kurtaxe_preview(reservation)
        return _render(
            request,
            "checkin/kurtaxe.html",
            reservation,
            "kurtaxe",
            error=exc.message,
            **_kurtaxe_context(result, reservation),
        )
    exempt = [line["name"] for line in assessment.breakdown if line["exempt"]]
    _audit_step(
        session,
        reservation,
        "kurtaxe.assessed",
        f"Kurtaxe berechnet: {fmt_money(assessment.amount)} für {assessment.nights} Nächte",
        amount=str(assessment.amount),
        exempt=exempt,
        satzung=assessment.satzung_label,
    )
    session.commit()
    return redirect_with_notice(
        _step_url(reservation, "kurkarte"),
        f"Kurtaxe bestätigt: {fmt_money(assessment.amount)}"
        + (f" · befreit: {', '.join(exempt)}" if exempt else ""),
    )


# ---------------------------------------------------------------------------
# Step 4 — Kurkarte
# ---------------------------------------------------------------------------


def _cards(reservation: Reservation) -> list[dict[str, Any]]:
    cards = []
    for rg in reservation.guests:
        view = engine.kurkarte_view(rg, today())
        cards.append(
            {
                "rg": rg,
                "view": view,
                "qr": qr_svg(view.qr_payload, label=f"QR-Code Kurkarte {view.code}")
                if view
                else None,
            }
        )
    return cards


@router.get("/check-in/{reservation_id}/kurkarte", response_class=HTMLResponse)
def kurkarte_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    state = engine.readiness(reservation)
    return _render(
        request,
        "checkin/kurkarte.html",
        reservation,
        "kurkarte",
        cards=_cards(reservation),
        tax_blockers=state["kurtaxe"],
    )


@router.post("/check-in/{reservation_id}/kurkarte")
def kurkarte_issue(reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    url = _step_url(reservation, "kurkarte")
    if engine.readiness(reservation)["kurtaxe"]:
        return redirect_with_notice(
            _step_url(reservation, "kurtaxe"),
            "Kurkarte erst nach bestätigter Kurtaxe ausstellen.",
            "warning",
        )
    issued = [
        engine.issue_kurkarte(session, rg, today()).guest_name
        for rg in reservation.guests
        if not rg.kurkarte_code
    ]
    session.commit()
    if not issued:
        return RedirectResponse(url, status_code=303)
    return redirect_with_notice(url, f"Kurkarte ausgestellt für {', '.join(issued)}.")


# ---------------------------------------------------------------------------
# Step 5 — completion
# ---------------------------------------------------------------------------


@router.get("/check-in/{reservation_id}/abschluss", response_class=HTMLResponse)
def summary_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    state = engine.readiness(reservation)
    open_items = [b for key in engine.STEP_KEYS for b in state[key]]
    return _render(
        request,
        "checkin/abschluss.html",
        reservation,
        "abschluss",
        open_items=open_items,
    )


@router.post("/check-in/{reservation_id}/abschluss")
def complete(reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    state = engine.readiness(reservation)
    open_items = [b for key in engine.STEP_KEYS for b in state[key]]
    if open_items:
        return redirect_with_notice(
            _step_url(reservation, engine.first_open_step(reservation)),
            f"Check-in noch nicht möglich: {open_items[0].message}",
            "danger",
        )
    reservation.status = CHECKED_IN
    reservation.checked_in_at = datetime.now(UTC)
    primary = reservation.primary_guest
    room = reservation.room
    _audit_step(
        session,
        reservation,
        "reservation.checked_in",
        f"Check-in abgeschlossen: {primary.full_name if primary else reservation.code} · Zimmer {room.number}",
        room=room.number,
        guests=[rg.guest.full_name for rg in reservation.guests],
        kurtaxe=str(reservation.kurtaxe.amount) if reservation.kurtaxe else None,
    )
    session.commit()
    who = primary.full_name if primary else reservation.code
    return redirect_with_notice("/anreisen", f"{who} ist eingecheckt · Zimmer {room.number}")
