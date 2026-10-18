"""Payment entry, corrections, incoming transfers and payment-method settings."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kurort_app import audit
from kurort_app.auth import require_role
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import CANCELLED, Payment, PaymentMethod, Reservation, ReservationGuest
from kurort_app.services import payments
from kurort_app.web import NAV, NavItem, redirect_with_notice, templates

router = APIRouter(dependencies=[Depends(require_role("rezeption", "leitung"))])
manager = [Depends(require_role("leitung"))]
NAV.append(
    NavItem(
        "/verwaltung/zahlungsarten",
        "Zahlungsarten",
        '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h3"/>',
        "Verwaltung",
        roles=("leitung",),
    )
)


def _reservation(session: Session, reservation_id: int, *, lock: bool = False) -> Reservation:
    stmt = (
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.payments).selectinload(Payment.method),
            selectinload(Reservation.kurtaxe),
            selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
            selectinload(Reservation.room),
        )
    )
    if lock:
        stmt = stmt.with_for_update()
    r = session.scalar(stmt)
    if r is None:
        raise HTTPException(404, "Reservierung nicht gefunden")
    return r


def _local_next(raw: str, fallback: str) -> str:
    decoded = unquote(raw)
    if (
        not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or any(ord(c) < 32 or ord(c) == 127 for c in decoded)
    ):
        return fallback
    parts = urlsplit(decoded)
    return raw if not parts.scheme and not parts.netloc else fallback


def _redirect(target: str, message: str):
    base, sep, anchor = target.partition("#")
    response = redirect_with_notice(base, message)
    if sep:
        response.headers["location"] += f"#{anchor}"
    return response


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


def _amount(raw: str) -> tuple[Decimal | None, str | None]:
    raw = raw.strip()
    if not raw:
        return None, "Betrag fehlt"
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?|[+-]?\d+\.\d+", raw):
        return None, "Betrag ungültig"
    normalized = raw.replace(".", "").replace(",", ".") if "," in raw else raw
    amount = Decimal(normalized)
    if amount.as_tuple().exponent < -2:
        return None, "Höchstens zwei Nachkommastellen"
    if amount <= 0:
        return None, "Betrag muss größer als 0 sein"
    if amount > Decimal("100000"):
        return None, "Höchstens 100.000,00 €"
    return amount.quantize(Decimal("0.01")), None


def _entry_page(request, session, r, form, errors, overpayment=None):
    context = payments.form_context(session, r, form=form, errors=errors)
    context.update(r=r, overpayment=overpayment)
    return templates.TemplateResponse(request, "payments/entry.html", context)


def _event(session, payment, action, summary, **extra):
    audit.record(
        session,
        action=action,
        entity="reservation",
        entity_id=payment.reservation_id,
        summary=summary,
        payload={
            "payment_id": payment.id,
            "amount": str(payment.amount),
            "method": payment.method.code,
            **extra,
        },
    )


@router.post("/reservierungen/{reservation_id}/zahlungen")
async def record_payment(
    request: Request, reservation_id: int, session: Session = Depends(get_session)
):
    form = {k: str(v) for k, v in (await request.form()).items()}
    r = _reservation(session, reservation_id, lock=True)
    form["next"] = _local_next(form.get("next", ""), f"/reservierungen/{r.id}#zahlung")
    errors = {}
    amount, error = _amount(form.get("amount", ""))
    if error:
        errors["amount"] = error
    method = session.scalar(
        select(PaymentMethod)
        .where(PaymentMethod.id == _int(form.get("method_id", "")))
        .with_for_update()
    )
    if method is None or not method.active:
        errors["method_id"] = "Zahlungsart wählen"
    paid_on = _date(form.get("paid_on", today().isoformat()))
    if paid_on is None:
        errors["paid_on"] = "Datum ungültig"
    elif paid_on > today():
        errors["paid_on"] = "Datum liegt in der Zukunft"
    for field, limit in (("payer", 120), ("note", 200)):
        if len(form.get(field, "").strip()) > limit:
            errors[field] = f"Höchstens {limit} Zeichen"
    if r.status == CANCELLED:
        errors["status"] = "Für stornierte Aufenthalte keine Zahlung erfassen."
    if errors:
        return _entry_page(request, session, r, form, errors)
    credit = amount - payments.balance(r).open
    if credit > 0 and form.get("confirm_overpayment") != "1":
        return _entry_page(request, session, r, form, {}, credit)
    payment = Payment(
        reservation=r,
        method=method,
        amount=amount,
        paid_on=paid_on,
        received_on=None if method.deferred else paid_on,
        payer=form.get("payer", "").strip() or None,
        note=form.get("note", "").strip() or None,
        recorded_by=audit.current_actor.get() or audit.DEFAULT_ACTOR,
    )
    session.add(payment)
    session.flush()
    _event(
        session,
        payment,
        "payment_recorded",
        f"Zahlung erfasst · {method.label} · {payments.money(amount)}",
    )
    session.commit()
    return _redirect(form["next"], "Zahlung erfasst.")


@router.post("/reservierungen/{reservation_id}/zahlungen/{payment_id}/stornieren")
async def cancel_payment(
    request: Request, reservation_id: int, payment_id: int, session: Session = Depends(get_session)
):
    r = _reservation(session, reservation_id, lock=True)
    payment = next((p for p in r.payments if p.id == payment_id), None)
    if payment is None:
        raise HTTPException(404, "Zahlung nicht gefunden")
    if payment.cancelled_at is not None:
        raise HTTPException(409, "Zahlung bereits storniert")
    reason = str((await request.form()).get("reason", "")).strip()
    if not reason or len(reason) > 200:
        return _entry_page(
            request,
            session,
            r,
            {},
            {f"reason_{payment.id}": "Grund fehlt" if not reason else "Höchstens 200 Zeichen"},
        )
    payment.cancelled_at = datetime.now(UTC)
    payment.cancelled_by = audit.current_actor.get() or audit.DEFAULT_ACTOR
    payment.cancel_reason = reason
    _event(session, payment, "payment_cancelled", f"Zahlung storniert · {reason}", reason=reason)
    session.commit()
    return _redirect(f"/reservierungen/{r.id}#zahlung", "Zahlung storniert.")


@router.get("/zahlungen/offen")
def open_payments(request: Request, ansicht: str = "", session: Session = Depends(get_session)):
    return _open_page(request, session, ansicht)


def _open_page(request, session, view, errors=None, values=None):
    return templates.TemplateResponse(
        request,
        "payments/open.html",
        {
            "view": "rechnung" if view == "rechnung" else "offen",
            "balances": payments.open_balances(session),
            "transfers": payments.open_transfers(session),
            "receipt_errors": errors or {},
            "receipt_values": values or {},
        },
    )


@router.post("/zahlungen/{payment_id}/eingang")
async def receive_payment(
    request: Request, payment_id: int, session: Session = Depends(get_session)
):
    payment = session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(404, "Zahlung nicht gefunden")
    _reservation(session, payment.reservation_id, lock=True)
    session.refresh(payment)
    if payment.cancelled_at is not None or payment.received_on is not None:
        raise HTTPException(409, "Kein offener Zahlungseingang")
    raw = str((await request.form()).get("received_on", ""))
    day = _date(raw)
    error = None
    if day is None:
        error = "Datum ungültig"
    elif day > today():
        error = "Datum liegt in der Zukunft"
    elif day < payment.paid_on:
        error = "Datum liegt vor der Zahlung"
    if error:
        return _open_page(request, session, "rechnung", {payment.id: error}, {payment.id: raw})
    payment.received_on = day
    _event(
        session,
        payment,
        "payment_received",
        f"Zahlungseingang erfasst · {payments.money(payment.amount)}",
    )
    session.commit()
    return _redirect("/zahlungen/offen?ansicht=rechnung", "Zahlungseingang erfasst.")


def _methods(session):
    return list(
        session.scalars(select(PaymentMethod).order_by(PaymentMethod.position, PaymentMethod.id))
    )


def _methods_page(request, session, errors=None, form=None):
    return templates.TemplateResponse(
        request,
        "payments/methods.html",
        {"methods": _methods(session), "method_errors": errors or {}, "method_form": form or {}},
    )


@router.get("/verwaltung/zahlungsarten", dependencies=manager)
def methods_page(request: Request, session: Session = Depends(get_session)):
    return _methods_page(request, session)


@router.post("/verwaltung/zahlungsarten", dependencies=manager)
async def create_method(request: Request, session: Session = Depends(get_session)):
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    code, label = form.get("code", ""), form.get("label", "")
    errors = {}
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", code):
        errors["code"] = "Kürzel: 1–32 Kleinbuchstaben, Ziffern, - oder _."
    elif session.scalar(select(PaymentMethod.id).where(PaymentMethod.code == code)):
        errors["code"] = "Kürzel schon vergeben"
    if not label or len(label) > 60:
        errors["label"] = "Bezeichnung fehlt" if not label else "Höchstens 60 Zeichen"
    if errors:
        return _methods_page(request, session, errors, form)
    rows = _methods(session)
    method = PaymentMethod(
        code=code,
        label=label,
        deferred=form.get("deferred") == "1",
        active=form.get("active") == "1",
        position=max((m.position for m in rows), default=-1) + 1,
    )
    session.add(method)
    session.flush()
    audit.record(
        session,
        action="payment_method_created",
        entity="payment_method",
        entity_id=method.id,
        summary=f"Zahlungsart angelegt · {method.label}",
        payload={"code": code},
    )
    session.commit()
    return _redirect("/verwaltung/zahlungsarten", "Zahlungsart angelegt.")


@router.post("/verwaltung/zahlungsarten/{method_id}", dependencies=manager)
async def update_method(request: Request, method_id: int, session: Session = Depends(get_session)):
    rows = list(
        session.scalars(
            select(PaymentMethod)
            .order_by(PaymentMethod.position, PaymentMethod.id)
            .with_for_update()
        )
    )
    method = next((m for m in rows if m.id == method_id), None)
    if method is None:
        raise HTTPException(404, "Zahlungsart nicht gefunden")
    form = {k: str(v).strip() for k, v in (await request.form()).items()}
    if "move" in form:
        idx = rows.index(method)
        other = idx + (-1 if form["move"] == "up" else 1)
        if 0 <= other < len(rows):
            rows[idx], rows[other] = rows[other], rows[idx]
        for position, row in enumerate(rows):
            row.position = position
    else:
        label = form.get("label", "")
        if not label or len(label) > 60:
            return _methods_page(
                request,
                session,
                {"label": "Bezeichnung fehlt" if not label else "Höchstens 60 Zeichen"},
                form,
            )
        method.label = label
        method.deferred = form.get("deferred") == "1"
        method.active = form.get("active") == "1"
    audit.record(
        session,
        action="payment_method_updated",
        entity="payment_method",
        entity_id=method.id,
        summary=f"Zahlungsart geändert · {method.label}",
        payload={
            "code": method.code,
            "label": method.label,
            "active": method.active,
            "deferred": method.deferred,
            "position": method.position,
        },
    )
    session.commit()
    return _redirect("/verwaltung/zahlungsarten", "Zahlungsart gespeichert.")
