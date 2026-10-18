"""Guest e-mails, outbox and hotel-editable mail/safe settings."""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app import audit
from kurort_app.auth import current_actor, require_role
from kurort_app.db import get_session
from kurort_app.models import (
    EmailMessageRow,
    EmailTemplate,
    LateArrival,
    Reservation,
    SafeCompartment,
)
from kurort_app.services import mail, mail_templates
from kurort_app.web import NAV, NavItem, redirect_with_notice, templates

router = APIRouter(dependencies=[Depends(require_role("rezeption", "leitung"))])
NAV.append(
    NavItem(
        "/verwaltung/e-mail",
        "E-Mail & Safe",
        '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 5 9 7 9-7"/>',
        "Verwaltung",
        roles=("leitung",),
    )
)
MANAGER = Depends(require_role("leitung"))


def _get(session, model, key):
    obj = session.get(model, key)
    if obj is None:
        raise HTTPException(404, "Eintrag nicht gefunden.")
    return obj


def _template(session, key):
    row = session.scalar(select(EmailTemplate).where(EmailTemplate.key == key))
    if row is None:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    return row


def _compose(request, session, r, form=None, error=None):
    choices = list(
        session.scalars(
            select(EmailTemplate)
            .where(EmailTemplate.active, EmailTemplate.key != "spaetanreise")
            .order_by(EmailTemplate.id)
        )
    )
    key = request.query_params.get("vorlage", "buchungsbestaetigung")
    chosen = next((t for t in choices if t.key == key), choices[0] if choices else None)
    form = (
        form
        if form is not None
        else {
            "template_key": chosen.key if chosen else "",
            "to_address": r.primary_guest.email if r.primary_guest else "",
            "subject": chosen.subject if chosen else "",
            "body": chosen.body if chosen else "",
        }
    )
    partial = bool(request.headers.get("HX-Request"))
    return templates.TemplateResponse(
        request,
        "mail/_compose.html" if partial else "mail/compose.html",
        {"r": r, "choices": choices, "form": form, "error": error},
        status_code=422 if error else 200,
    )


@router.get("/reservierungen/{reservation_id}/e-mail")
def compose(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    return _compose(request, session, _get(session, Reservation, reservation_id))


@router.post("/reservierungen/{reservation_id}/e-mail/vorschau")
async def preview(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    r = _get(session, Reservation, reservation_id)
    form = dict(await request.form())
    try:
        subject, body = mail_templates.render(
            str(form.get("subject", "")), str(form.get("body", "")), mail_templates.context_for(r)
        )
        return templates.TemplateResponse(
            request, "mail/_preview.html", {"subject": subject, "body": body}
        )
    except ValueError as exc:
        return templates.TemplateResponse(request, "mail/_preview.html", {"error": str(exc)})


@router.post("/reservierungen/{reservation_id}/e-mail")
async def send_message(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    r = _get(session, Reservation, reservation_id)
    form = {k: str(v) for k, v in (await request.form()).items()}
    try:
        key = form.get("template_key", "")
        if key:
            selected = _template(session, key)
            if not selected.active or key == "spaetanreise":
                raise ValueError("Diese Vorlage gehört zur Spätanreise oder ist nicht aktiv.")
        address = mail.validate_recipient(form.get("to_address", ""))
        subject, body = mail_templates.render(
            form.get("subject", ""), form.get("body", ""), mail_templates.context_for(r)
        )
    except ValueError as exc:
        return _compose(request, session, r, form, str(exc))
    row = EmailMessageRow(
        reservation_id=r.id,
        template_key=key or None,
        to_address=address,
        subject=subject,
        body=body,
        created_by=current_actor.get() or "rezeption",
    )
    mail.send(session, row, settings=request.app.state.settings)
    text = (
        "E-Mail gesendet"
        if row.status == "sent"
        else (
            "protokolliert – nicht versendet (kein Mailserver eingerichtet)"
            if row.status == "logged"
            else "E-Mail fehlgeschlagen – im Postausgang erneut senden"
        )
    )
    return redirect_with_notice(
        f"/reservierungen/{r.id}", text, "danger" if row.status == "failed" else "success"
    )


@router.get("/e-mails")
def outbox(
    request: Request,
    status: str = "",
    reservation_id: int | None = None,
    session: Session = Depends(get_session),
):
    query = select(EmailMessageRow).order_by(
        EmailMessageRow.created_at.desc(), EmailMessageRow.id.desc()
    )
    if status:
        query = query.where(EmailMessageRow.status == status)
    if reservation_id is not None:
        query = query.where(EmailMessageRow.reservation_id == reservation_id)
    return templates.TemplateResponse(
        request,
        "mail/outbox.html",
        {
            "messages": session.scalars(query).all(),
            "status": status,
            "reservation_id": reservation_id,
        },
    )


@router.get("/e-mails/{message_id}")
def message_detail(request: Request, message_id: int, session: Session = Depends(get_session)):
    row = _get(session, EmailMessageRow, message_id)
    # Safe codes are revealed only on the audited preparation page.
    return templates.TemplateResponse(
        request,
        "mail/message.html",
        {"message": row, "sensitive": row.template_key == "spaetanreise"},
    )


@router.post("/e-mails/{message_id}/erneut")
def retry(request: Request, message_id: int, session: Session = Depends(get_session)):
    row = session.scalar(
        select(EmailMessageRow).where(EmailMessageRow.id == message_id).with_for_update()
    )
    if row is None:
        raise HTTPException(404)
    if row.status != "failed":
        return redirect_with_notice(
            f"/e-mails/{row.id}",
            "Nur fehlgeschlagene Nachrichten können erneut gesendet werden.",
            "warning",
        )
    if row.template_key == "spaetanreise":
        late = session.scalar(select(LateArrival).where(LateArrival.email_message_id == row.id))
        if not late or late.status != "vorbereitet":
            return redirect_with_notice(
                f"/e-mails/{row.id}", "Dieser Safe-Code ist nicht mehr gültig.", "warning"
            )
    mail.send(session, row, settings=request.app.state.settings)
    return redirect_with_notice(
        f"/e-mails/{row.id}",
        "Erneuter Versand: " + row.status,
        "danger" if row.status == "failed" else "success",
    )


@router.get("/verwaltung/e-mail", dependencies=[MANAGER])
def settings_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        request,
        "mail/settings.html",
        {
            "rows": session.scalars(select(EmailTemplate).order_by(EmailTemplate.id)).all(),
            "compartments": session.scalars(
                select(SafeCompartment).order_by(SafeCompartment.position, SafeCompartment.id)
            ).all(),
        },
    )


def _editor(request, row=None, form=None, error=None):
    form = (
        form
        if form is not None
        else {
            "key": row.key,
            "name": row.name,
            "subject": row.subject,
            "body": row.body,
            "active": row.active,
        }
        if row
        else {}
    )
    return templates.TemplateResponse(
        request,
        "mail/editor.html",
        {
            "row": row,
            "form": form,
            "error": error,
            "placeholders": mail_templates.placeholder_names(allow_safe=bool(row and row.system)),
        },
        status_code=422 if error else 200,
    )


@router.get("/verwaltung/e-mail/vorlagen/neu", dependencies=[MANAGER])
def new_template(request: Request):
    return _editor(request)


@router.get("/verwaltung/e-mail/vorlagen/{key}", dependencies=[MANAGER])
def edit_template(request: Request, key: str, session: Session = Depends(get_session)):
    return _editor(request, _template(session, key))


@router.post("/verwaltung/e-mail/vorlagen/{key}/vorschau", dependencies=[MANAGER])
async def editor_preview(request: Request, key: str, session: Session = Depends(get_session)):
    row = _template(session, key) if key != "neu" else None
    form = await request.form()
    try:
        subject, body = mail_templates.validate_template(
            str(form.get("subject", "")),
            str(form.get("body", "")),
            allow_safe=bool(row and row.system),
        )
        return templates.TemplateResponse(
            request, "mail/_preview.html", {"subject": subject, "body": body}
        )
    except ValueError as exc:
        return templates.TemplateResponse(request, "mail/_preview.html", {"error": str(exc)})


async def _save_template(request, session, row=None):
    form = {k: str(v) for k, v in (await request.form()).items()}
    try:
        key, name = form.get("key", row.key if row else "").strip(), form.get("name", "").strip()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", key) or not 1 <= len(name) <= 80:
            raise ValueError(
                "Bitte einen Schlüssel (a–z, Ziffern, - oder _) und einen Namen mit höchstens 80 Zeichen angeben."
            )
        active = form.get("active") == "on"
        if row and row.system and (key != row.key or name != row.name or not active):
            raise ValueError("Systemvorlagen können nicht umbenannt oder deaktiviert werden.")
        if row and key != row.key:
            raise ValueError("Der Vorlagenschlüssel bleibt unverändert.")
        if not row and session.scalar(select(EmailTemplate.id).where(EmailTemplate.key == key)):
            raise ValueError("Diesen Vorlagenschlüssel gibt es bereits.")
        mail_templates.validate_template(
            form.get("subject", ""), form.get("body", ""), allow_safe=bool(row and row.system)
        )
    except ValueError as exc:
        return _editor(request, row, form, str(exc))
    created = row is None
    row = row or EmailTemplate(key=key, system=False)
    row.name, row.subject, row.body, row.active = name, form["subject"], form["body"], active
    row.updated_at, row.updated_by = datetime.now(UTC), current_actor.get() or "rezeption"
    session.add(row)
    session.flush()
    audit.record(
        session,
        action="email_template_created" if created else "email_template_updated",
        entity="email_template",
        entity_id=row.id,
        summary="E-Mail-Vorlage gespeichert",
        payload={"key": row.key},
    )
    session.commit()
    return redirect_with_notice("/verwaltung/e-mail", "Vorlage gespeichert")


@router.post("/verwaltung/e-mail/vorlagen", dependencies=[MANAGER])
async def create_template(request: Request, session: Session = Depends(get_session)):
    return await _save_template(request, session)


@router.post("/verwaltung/e-mail/vorlagen/{key}", dependencies=[MANAGER])
async def save_template(request: Request, key: str, session: Session = Depends(get_session)):
    return await _save_template(request, session, _template(session, key))


async def _save_compartment(request, session, row=None):
    form = {k: str(v) for k, v in (await request.form()).items()}
    label, pin = form.get("label", "").strip(), form.get("fixed_pin", "").strip()
    error = None
    if not 1 <= len(label) <= 40 or (pin and not re.fullmatch(r"[0-9]{1,8}", pin)):
        error = "Fachname (höchstens 40 Zeichen) und Code (1–8 Ziffern) prüfen."
    existing = session.scalar(select(SafeCompartment.id).where(SafeCompartment.label == label))
    if existing and (not row or existing != row.id):
        error = "Diesen Fachnamen gibt es bereits."
    if row and session.scalar(
        select(LateArrival.id).where(
            LateArrival.compartment_id == row.id, LateArrival.status == "vorbereitet"
        )
    ):
        error = "Das Fach ist belegt. Bitte erst die Spätanreise abschließen oder abbrechen."
    try:
        position = int(form.get("position", "0"))
    except ValueError:
        error, position = "Bitte eine ganze Zahl für die Reihenfolge angeben.", 0
    if error:
        return redirect_with_notice("/verwaltung/e-mail", error, "danger")
    created = row is None
    row = row or SafeCompartment()
    row.label, row.position, row.active = label, position, form.get("active") == "on"
    if pin or form.get("clear_pin") == "on":
        row.fixed_pin = pin or None
    session.add(row)
    session.flush()
    audit.record(
        session,
        action="safe_compartment_created" if created else "safe_compartment_updated",
        entity="safe_compartment",
        entity_id=row.id,
        summary="Safe-Fach gespeichert",
        payload={"label": row.label, "fixed": bool(row.fixed_pin)},
    )
    session.commit()
    return redirect_with_notice("/verwaltung/e-mail", "Safe-Fach gespeichert")


@router.post("/verwaltung/safe-faecher", dependencies=[MANAGER])
async def create_compartment(request: Request, session: Session = Depends(get_session)):
    return await _save_compartment(request, session)


@router.post("/verwaltung/safe-faecher/{compartment_id}", dependencies=[MANAGER])
async def update_compartment(
    request: Request, compartment_id: int, session: Session = Depends(get_session)
):
    row = session.scalar(
        select(SafeCompartment).where(SafeCompartment.id == compartment_id).with_for_update()
    )
    if row is None:
        raise HTTPException(404)
    return await _save_compartment(request, session, row)
