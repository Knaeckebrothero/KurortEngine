"""Guest e-mails, outbox and hotel-editable mail/safe settings."""

import re
import unicodedata
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
        "/e-mails",
        "Postausgang",
        '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
        "Heute",
    )
)
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


def _preview(subject, body, context):
    try:
        subject, body = mail_templates.render(subject, body, context)
        return {"subject": subject, "body": body}
    except ValueError as exc:
        return {"error": str(exc)}


def _filled(template, context):
    """The template filled with this stay, so staff read and edit the real e-mail.

    Sending fills placeholders once more, which leaves filled text unchanged. A value
    with braces could then read as a placeholder, so such stays keep the raw template.
    """
    if template is None:
        return "", ""
    if any("{" in v or "}" in v for values in context.values() for v in values.values()):
        return template.subject, template.body
    preview = _preview(template.subject, template.body, context)
    if "error" in preview:
        return template.subject, template.body
    return preview["subject"], preview["body"]


def _compose(request, session, r, form=None, error=None):
    choices = list(
        session.scalars(
            select(EmailTemplate)
            .where(EmailTemplate.active, EmailTemplate.key != "spaetanreise")
            .order_by(EmailTemplate.id)
        )
    )
    key = (form or {}).get("template_key") or request.query_params.get(
        "vorlage", "buchungsbestaetigung"
    )
    chosen = next((t for t in choices if t.key == key), choices[0] if choices else None)
    context = mail_templates.context_for(r)
    subject, body = _filled(chosen, context)
    form = (
        form
        if form is not None
        else {
            "template_key": chosen.key if chosen else "",
            "to_address": r.primary_guest.email if r.primary_guest else "",
            "subject": subject,
            "body": body,
        }
    )
    partial = bool(request.headers.get("HX-Request"))
    return templates.TemplateResponse(
        request,
        "mail/_compose.html" if partial else "mail/compose.html",
        {
            "r": r,
            "choices": choices,
            "form": form,
            "error": error,
            # What the chosen template looked like before typing; a switch keeps edits.
            "pristine": {"subject": subject, "body": body},
            "preview": _preview(form.get("subject", ""), form.get("body", ""), context),
            "placeholders": [
                (f"{group}.{field}", value)
                for group, values in context.items()
                for field, value in values.items()
            ],
        },
        status_code=422 if error else 200,
    )


@router.get("/reservierungen/{reservation_id}/e-mail")
def compose(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    return _compose(request, session, _get(session, Reservation, reservation_id))


@router.post("/reservierungen/{reservation_id}/e-mail/vorschau")
async def preview(request: Request, reservation_id: int, session: Session = Depends(get_session)):
    r = _get(session, Reservation, reservation_id)
    form = dict(await request.form())
    return templates.TemplateResponse(
        request,
        "mail/_preview.html",
        _preview(
            str(form.get("subject", "")), str(form.get("body", "")), mail_templates.context_for(r)
        ),
    )


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
    guest = r.primary_guest
    who = guest.full_name if guest and guest.email == address else address
    text, kind = {
        "sent": (f"E-Mail an {who} gesendet.", "success"),
        "logged": (
            f"E-Mail an {who} gespeichert – Testbetrieb, es wird nichts verschickt.",
            "info",
        ),
    }.get(row.status, ("E-Mail fehlgeschlagen – im Postausgang erneut senden.", "danger"))
    return redirect_with_notice(f"/reservierungen/{r.id}", text, kind)


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
            "template_names": _template_names(session),
        },
    )


def _template_names(session):
    return {
        key: name for key, name in session.execute(select(EmailTemplate.key, EmailTemplate.name))
    }


@router.get("/e-mails/{message_id}")
def message_detail(request: Request, message_id: int, session: Session = Depends(get_session)):
    row = _get(session, EmailMessageRow, message_id)
    # Safe codes are revealed only on the audited preparation page.
    return templates.TemplateResponse(
        request,
        "mail/message.html",
        {
            "message": row,
            "sensitive": row.template_key == "spaetanreise",
            "template_name": _template_names(session).get(row.template_key),
        },
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
    text, kind = {
        "sent": ("E-Mail gesendet.", "success"),
        "logged": ("E-Mail gespeichert – Testbetrieb, es wird nichts verschickt.", "info"),
    }.get(row.status, ("Erneuter Versand fehlgeschlagen.", "danger"))
    return redirect_with_notice(f"/e-mails/{row.id}", text, kind)


def _settings(request, session, safe_errors=None, safe_form=None, safe_target=None):
    """safe_target is the compartment id (or "neu") whose form shows ``safe_errors``."""
    settings = request.app.state.settings
    return templates.TemplateResponse(
        request,
        "mail/settings.html",
        {
            "rows": session.scalars(select(EmailTemplate).order_by(EmailTemplate.id)).all(),
            "compartments": session.scalars(
                select(SafeCompartment).order_by(SafeCompartment.position, SafeCompartment.id)
            ).all(),
            "smtp": settings.mail_transport == "smtp",
            "sender": settings.smtp_from,
            "safe_errors": safe_errors or {},
            "safe_form": safe_form or {},
            "safe_target": safe_target,
        },
        status_code=422 if safe_errors else 200,
    )


@router.get("/verwaltung/e-mail", dependencies=[MANAGER])
def settings_page(request: Request, session: Session = Depends(get_session)):
    return _settings(request, session)


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


def _template_key(session, name):
    """Internal key from the name: "Rückfrage Ärztin" -> "rueckfrage_aerztin"."""
    text = name.lower()
    for umlaut, plain in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, plain)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:32].strip("_")
    if not base[:1].isalpha():
        base = f"vorlage_{base}".strip("_")[:32]
    key, number = base, 2
    while key == "neu" or session.scalar(select(EmailTemplate.id).where(EmailTemplate.key == key)):
        key, number = f"{base}_{number}", number + 1
    return key


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
        name = form.get("name", "").strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("Bitte einen Namen mit höchstens 80 Zeichen angeben.")
        active = form.get("active") == "on"
        if row and row.system and (name != row.name or not active):
            raise ValueError("Systemvorlagen können nicht umbenannt oder deaktiviert werden.")
        if row and form.get("key", row.key) != row.key:
            raise ValueError("Der Vorlagenschlüssel bleibt unverändert.")
        mail_templates.validate_template(
            form.get("subject", ""), form.get("body", ""), allow_safe=bool(row and row.system)
        )
    except ValueError as exc:
        return _editor(request, row, form, str(exc))
    created = row is None
    row = row or EmailTemplate(key=_template_key(session, name), system=False)
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
    errors = {}
    existing = session.scalar(select(SafeCompartment.id).where(SafeCompartment.label == label))
    if not label:
        errors["label"] = "Bitte einen Fachnamen angeben."
    elif len(label) > 40:
        errors["label"] = "Höchstens 40 Zeichen."
    elif existing and (not row or existing != row.id):
        errors["label"] = "Diesen Fachnamen gibt es bereits."
    if pin and not re.fullmatch(r"[0-9]{1,8}", pin):
        errors["fixed_pin"] = "Der Code besteht aus 1 bis 8 Ziffern."
    if row is None and not form.get("position", "").strip():
        # A new compartment goes to the end of the list.
        position = max(session.scalars(select(SafeCompartment.position)).all(), default=-1) + 1
    else:
        try:
            position = int(form.get("position", "0"))
        except ValueError:
            errors["position"], position = "Bitte eine ganze Zahl angeben.", 0
    if row and session.scalar(
        select(LateArrival.id).where(
            LateArrival.compartment_id == row.id, LateArrival.status == "vorbereitet"
        )
    ):
        errors["form"] = (
            "Das Fach ist belegt. Bitte erst die Spätanreise abschließen oder abbrechen."
        )
    if errors:
        # The PIN is never sent back to the browser; it has to be typed again.
        form.pop("fixed_pin", None)
        return _settings(request, session, errors, form, row.id if row else "neu")
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
