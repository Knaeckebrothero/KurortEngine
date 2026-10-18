"""One desk balance, shared by reservations, departures and payment lists."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app.models import CANCELLED, NO_SHOW, PaymentMethod, Reservation

DEFAULT_METHODS = (
    ("bar", "Bar", False),
    ("ec", "EC-Karte", False),
    ("kreditkarte", "Kreditkarte", False),
    ("ueberweisung", "Überweisung", False),
    ("booking", "Booking.com (vorausbezahlt)", False),
    ("rechnung", "Auf Rechnung", True),
)
ZERO = Decimal("0.00")


def ensure_payment_methods(session: Session) -> None:
    codes = set(session.scalars(select(PaymentMethod.code)))
    for position, (code, label, deferred) in enumerate(DEFAULT_METHODS):
        if code not in codes:
            session.add(
                PaymentMethod(
                    code=code, label=label, deferred=deferred, active=True, position=position
                )
            )
    session.flush()


@dataclass(frozen=True)
class Balance:
    room: Decimal
    kurtaxe: Decimal | None
    due: Decimal
    paid: Decimal
    open: Decimal
    awaiting: Decimal
    state: str


def balance(reservation: Reservation) -> Balance:
    room = reservation.rate_total or ZERO
    tax = reservation.kurtaxe.amount if reservation.kurtaxe else None
    due = ZERO if reservation.status in (CANCELLED, NO_SHOW) else room + (tax or ZERO)
    active = [p for p in reservation.payments if p.cancelled_at is None]
    paid = sum((p.amount for p in active), ZERO)
    awaiting = sum((p.amount for p in active if p.received_on is None), ZERO)
    remaining = due - paid
    state = "offen" if remaining > 0 else "guthaben" if remaining < 0 else "bezahlt"
    return Balance(room, tax, due, paid, remaining, awaiting, state)


def money(amount: Decimal) -> str:
    from kurort_app.web import fmt_money

    return fmt_money(amount)


def state_label(b: Balance) -> str:
    from kurort_app.web import PAYMENT_STATE_LABELS

    label = PAYMENT_STATE_LABELS[b.state]
    if b.state != "bezahlt":
        label += f" {money(abs(b.open))}"
    if b.awaiting > 0:
        label += f" · Rechnung offen {money(b.awaiting)}"
    return label


def form_context(
    session: Session, reservation: Reservation, *, form=None, errors=None, next_path=None
) -> dict:
    from kurort_app.config import today

    b = balance(reservation)
    target = next_path or f"/reservierungen/{reservation.id}#zahlung"
    values = {
        "amount": str(max(b.open, ZERO)).replace(".", ","),
        "paid_on": today().isoformat(),
        "next": target,
    }
    values.update(form or {})
    methods = list(
        session.scalars(
            select(PaymentMethod)
            .where(PaymentMethod.active.is_(True))
            .order_by(PaymentMethod.position, PaymentMethod.id)
        )
    )
    return {
        "balance": b,
        "payment_label": state_label(b),
        "payment_methods": methods,
        "payment_form": values,
        "payment_errors": errors or {},
        "payment_next": values["next"],
        "overpayment": None,
    }


def open_balances(session: Session) -> list[tuple[Reservation, Balance]]:
    from sqlalchemy.orm import selectinload

    from kurort_app.models import CHECKED_IN, CHECKED_OUT, Payment, ReservationGuest

    rows = session.scalars(
        select(Reservation)
        .where(Reservation.status.in_((CHECKED_IN, CHECKED_OUT)))
        .options(
            selectinload(Reservation.payments).selectinload(Payment.method),
            selectinload(Reservation.kurtaxe),
            selectinload(Reservation.room),
            selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
        )
        .order_by(Reservation.departure, Reservation.id)
    )
    return [(r, b) for r in rows if (b := balance(r)).open > 0]


def open_transfers(session: Session):
    from sqlalchemy.orm import selectinload

    from kurort_app.models import Payment, ReservationGuest

    return list(
        session.scalars(
            select(Payment)
            .where(Payment.received_on.is_(None), Payment.cancelled_at.is_(None))
            .options(
                selectinload(Payment.method),
                selectinload(Payment.reservation)
                .selectinload(Reservation.guests)
                .selectinload(ReservationGuest.guest),
            )
            .order_by(Payment.paid_on, Payment.id)
        )
    )


def payment_flags(session, row):
    from kurort_app.services.today import Flag

    if row.kind != "abreise":
        return []
    b = balance(row.reservation)
    if b.open > 0:
        return [
            Flag(
                f"Offen {money(b.open)}", "warning", f"/reservierungen/{row.reservation.id}#zahlung"
            )
        ]
    if b.open < 0:
        return [Flag(state_label(b), "info", f"/reservierungen/{row.reservation.id}#zahlung")]
    return [Flag("Bezahlt", "success")]


def payment_warning(session, reservation):
    from kurort_app.services.today import Flag

    b = balance(reservation)
    return (
        [Flag(f"Offener Betrag {money(b.open)} – bitte vor dem Check-out kassieren", "warning")]
        if b.open > 0
        else []
    )


def payment_notice(session, day):
    from kurort_app.services.today import Flag

    count = len(open_balances(session))
    return [Flag(f"{count} offene Beträge", "warning", "/zahlungen/offen")] if count else []


from kurort_app.services import today as desk  # noqa: E402

desk.FLAG_PROVIDERS.append(payment_flags)
desk.CHECKOUT_WARNINGS.append(payment_warning)
desk.DASHBOARD_NOTICES.append(payment_notice)
