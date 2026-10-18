"""Three-step check-in: guest data, AVS printing, room handover."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import FormData

from kurort_app import audit
from kurort_app.auth import require_role, safe_next
from kurort_app.config import get_settings, today
from kurort_app.db import get_session
from kurort_app.models import (
    CHECKED_IN,
    EXEMPTION_CATEGORIES,
    MELDESCHEIN_OPEN,
    MELDESCHEIN_PRINTED,
    MELDESCHEIN_SIGNED,
    RESERVED,
    AuditEvent,
    Guest,
    Reservation,
    ReservationGuest,
)
from kurort_app.services import engine
from kurort_app.web import STATUS_LABELS, fmt_date, fmt_money, redirect_with_notice, templates
from kurort_engine.kurpaket_templates import TEMPLATES as PACKAGE_TEMPLATES

router = APIRouter(dependencies=[Depends(require_role("rezeption", "leitung"))])

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
        "package": PACKAGE_TEMPLATES.get((reservation.package_code or "").upper()),
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
    if not all_errors:
        _assess(session, reservation, auto=True)
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
        text = f"Daten geändert – in AVS neu drucken: {', '.join(stale_forms)}."
    return redirect_with_notice(
        _step_url(reservation, "avs"), text, "warning" if stale_forms else "success"
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
# AVS printing and signatures
# ---------------------------------------------------------------------------


def _avs_card(session: Session, rg: ReservationGuest) -> dict[str, Any]:
    values = []
    try:
        engine.meldeschein_form(rg)
    except engine.MeldescheinIncompleteError:
        return {"rg": rg, "values": values, "incomplete": True}
    g, res = rg.guest, rg.reservation
    countries = dict(COUNTRIES)
    values = [
        ("Familienname", g.last_name),
        ("Vorname", g.first_name),
        ("Geburtsdatum", fmt_date(g.birth_date)),
        ("Staatsangehörigkeit", countries.get(g.nationality, g.nationality)),
        ("Straße und Hausnummer", g.street),
        ("PLZ", g.postal_code),
        ("Ort", g.city),
        ("Land", countries.get(g.country, g.country)),
    ]
    if g.id_document_number or g.nationality != "DE":
        values.append(("Ausweisnummer", g.id_document_number or ""))
    line = next(
        line for line in engine.kurtaxe_preview(res).lines if line.reservation_guest_id == rg.id
    )
    values.extend(
        [
            ("Anreise", fmt_date(res.arrival)),
            ("Abreise", fmt_date(res.departure)),
            ("Kurtaxe-Gruppe", line.exemption_label if line.exempt else line.band_label),
        ]
    )
    event = session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.entity == "reservation_guest",
            AuditEvent.entity_id == str(rg.id),
            AuditEvent.action == "meldeschein.printed",
        )
        .order_by(AuditEvent.id.desc())
    )
    return {
        "rg": rg,
        "values": values,
        "incomplete": False,
        "copy_all": "\n".join(f"{label}: {value}" for label, value in values),
        "printed_by": event.actor if event else "–",
    }


@router.get("/check-in/{reservation_id}/avs", response_class=HTMLResponse)
def avs_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    return _render(
        request,
        "checkin/avs.html",
        reservation,
        "avs",
        cards=[_avs_card(session, rg) for rg in reservation.guests],
        avs_url=get_settings().avs_url,
    )


def _printed(session: Session, rg: ReservationGuest) -> None:
    engine.meldeschein_form(rg)
    if rg.meldeschein_status != MELDESCHEIN_OPEN:
        return
    rg.meldeschein_status = MELDESCHEIN_PRINTED
    rg.meldeschein_printed_at = datetime.now(UTC)
    rg.meldeschein_signed_at = None
    audit.record(
        session,
        action="meldeschein.printed",
        entity="reservation_guest",
        entity_id=rg.id,
        summary=f"In AVS gedruckt: {rg.guest.full_name}",
        payload={"reservation": rg.reservation.code},
    )


def _signed(session: Session, rg: ReservationGuest) -> None:
    if rg.meldeschein_status == MELDESCHEIN_SIGNED:
        return
    rg.meldeschein_status = MELDESCHEIN_SIGNED
    rg.meldeschein_signed_at = datetime.now(UTC)
    audit.record(
        session,
        action="meldeschein.signed",
        entity="reservation_guest",
        entity_id=rg.id,
        summary=f"Unterschrift erhalten: {rg.guest.full_name}",
        payload={"reservation": rg.reservation.code},
    )


@router.post("/check-in/{reservation_id}/avs/alle")
def avs_all(reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    for rg in reservation.guests:
        try:
            _printed(session, rg)
        except engine.MeldescheinIncompleteError:
            continue
    session.commit()
    return RedirectResponse(_step_url(reservation, "avs"), status_code=303)


@router.post("/check-in/{reservation_id}/avs/{rg_id}/gedruckt")
def avs_printed(
    request: Request, reservation_id: int, rg_id: int, session: Session = Depends(get_session)
):
    return _avs_update(request, reservation_id, rg_id, session, undo=False)


@router.post("/check-in/{reservation_id}/avs/{rg_id}/offen")
def avs_undo(
    request: Request, reservation_id: int, rg_id: int, session: Session = Depends(get_session)
):
    return _avs_update(request, reservation_id, rg_id, session, undo=True)


def _avs_update(request: Request, reservation_id: int, rg_id: int, session: Session, *, undo: bool):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    rg = _find_guest(reservation, rg_id)
    url = _step_url(reservation, "avs")
    if rg is None:
        return redirect_with_notice(url, "Gast nicht gefunden.", "danger")
    if undo:
        if engine.invalidate_meldeschein(rg):
            audit.record(
                session,
                action="meldeschein.print_undone",
                entity="reservation_guest",
                entity_id=rg.id,
                summary=f"AVS-Druck zurückgenommen: {rg.guest.full_name}",
            )
    else:
        try:
            _printed(session, rg)
        except engine.MeldescheinIncompleteError:
            return redirect_with_notice(
                _step_url(reservation, "gaeste"), "Daten unvollständig.", "danger"
            )
    session.commit()
    if _is_htmx(request):
        return templates.TemplateResponse(
            request, "checkin/_avs_guest.html", {"r": reservation, "card": _avs_card(session, rg)}
        )
    return RedirectResponse(url, status_code=303)


@router.post("/meldeschein/{rg_id}/unterschrieben")
async def signature_later(request: Request, rg_id: int, session: Session = Depends(get_session)):
    rg = session.get(ReservationGuest, rg_id)
    if rg is None:
        return redirect_with_notice("/", "Gast nicht gefunden.", "danger")
    form = await request.form()
    target = (
        safe_next(str(form["zurueck"]))
        if "zurueck" in form
        else f"/reservierungen/{rg.reservation_id}"
    )
    if rg.meldeschein_status == MELDESCHEIN_OPEN:
        return redirect_with_notice(target, "Erst in AVS drucken.", "danger")
    _signed(session, rg)
    session.commit()
    return redirect_with_notice(target, f"Unterschrift von {rg.guest.full_name} erfasst.")


@router.get("/check-in/{reservation_id}/meldeschein")
def old_meldeschein(reservation_id: int):
    return RedirectResponse(f"/check-in/{reservation_id}/avs", status_code=303)


@router.get("/check-in/{reservation_id}/kurkarte")
def old_kurkarte(reservation_id: int):
    return RedirectResponse(f"/check-in/{reservation_id}/abschluss", status_code=303)


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


@router.get("/check-in/{reservation_id}/kurtaxe")
def old_kurtaxe(reservation_id: int):
    return RedirectResponse(f"/check-in/{reservation_id}/abschluss#kurtaxe", status_code=303)


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
    _assess(session, reservation, auto=False)
    session.commit()
    return RedirectResponse(_step_url(reservation, "abschluss") + "#kurtaxe", status_code=303)


def _assess(session: Session, reservation: Reservation, *, auto: bool) -> None:
    if engine.kurtaxe_preview(reservation).blockers:
        return
    assessment = engine.assess_kurtaxe(session, reservation)
    _audit_step(
        session,
        reservation,
        "kurtaxe.assessed",
        f"Kurtaxe berechnet: {fmt_money(assessment.amount)}",
        auto=auto,
        amount=str(assessment.amount),
        satzung=assessment.satzung_label,
    )


def _open_items(session: Session, reservation: Reservation) -> list[engine.Blocker]:
    from kurort_app.services.today import checkin_blockers

    state = engine.readiness(reservation)
    return [b for key in engine.STEP_KEYS for b in state[key]] + checkin_blockers(
        session, reservation
    )


@router.get("/check-in/{reservation_id}/abschluss", response_class=HTMLResponse)
def summary_step(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    if reservation.kurtaxe is None:
        _assess(session, reservation, auto=True)
        session.commit()
    result = engine.kurtaxe_preview(reservation)
    return _render(
        request,
        "checkin/abschluss.html",
        reservation,
        "abschluss",
        open_items=_open_items(session, reservation),
        **_kurtaxe_context(result, reservation),
    )


@router.post("/check-in/{reservation_id}/abschluss")
async def complete(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    reservation = _open(session, reservation_id)
    if isinstance(reservation, RedirectResponse):
        return reservation
    _assess(session, reservation, auto=True)
    open_items = _open_items(session, reservation)
    if open_items:
        session.commit()
        return redirect_with_notice(
            _step_url(reservation, engine.first_open_step(reservation)),
            f"Check-in noch nicht möglich: {open_items[0].message}",
            "danger",
        )
    form = await request.form()
    signed_ids = set(form.getlist("unterschrieben"))
    for rg in reservation.guests:
        if str(rg.id) in signed_ids:
            _signed(session, rg)
    reservation.status = CHECKED_IN
    reservation.checked_in_at = datetime.now(UTC)
    primary, room = reservation.primary_guest, reservation.room
    who = primary.full_name if primary else reservation.code
    _audit_step(
        session,
        reservation,
        "reservation.checked_in",
        f"Check-in abgeschlossen: {who} · Zimmer {room.number}",
        room=room.number,
        guests=[rg.guest.full_name for rg in reservation.guests],
        kurtaxe=str(reservation.kurtaxe.amount),
    )
    session.commit()
    return redirect_with_notice("/", f"{who} ist eingecheckt · Zimmer {room.number}")
