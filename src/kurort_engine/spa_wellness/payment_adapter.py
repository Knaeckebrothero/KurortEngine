"""Payment + SpaBooking entities for kurort_engine.spa_wellness (AC-6 + AC-7).

A ``Payment`` represents a single payment instrument applied to a booking. The
``SpaBooking`` represents the persisted guest-folio entry for a Spa slot
reservation. Per the spec.yaml PROTECTED block (AC-6 + AC-7 verbatim):

  - ``Payment(booking, method, *, kurkarte_id=None)`` returns a frozen
    Payment dataclass with ``method in {'cash','sepa','kurkarte'}`` validated,
    ``amount_eur`` pulled from ``booking.folio_price_eur``,
    ``eur_currency_format`` rendered as ``f'€{amount_eur:.2f}'``, and
    ``processed_at`` set to UTC now.

  - ``SpaBooking.book(guest_id, slot, payment)`` classmethod atomically
    increments ``slot.bookings_count`` and returns a frozen ``SpaBooking``
    dataclass with ``folio_line`` rendered as
    ``'kurort_engine.spa_wellness — Spa booking — slot {slot.id} — guest
    {guest_id} — €{amount_eur:.2f}'``.

Both classes are implemented as ``@dataclass(frozen=True)`` with
``init=False`` so we can supply custom ``__init__`` signatures that match
the AC-6/AC-7 contracts verbatim (the auto-generated ``__init__`` would
otherwise expose every dataclass field as a kwarg and break the
``Payment(booking, method)`` public API).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from kurort_engine.spa_wellness.config import ALLOWED_PAYMENT_METHODS

# ---------------------------------------------------------------------------
# Exceptions (per AC-6 contract)
# ---------------------------------------------------------------------------


class PaymentMethodError(ValueError):
    """Raised when the supplied payment method is not in the allowed set."""

    def __init__(self, message: str = "method must be one of cash|sepa|kurkarte") -> None:
        super().__init__(message)
        self.message = message


class PaymentMethodKurkarteError(PaymentMethodError):
    """Raised when method='kurkarte' but no kurkarte_id was supplied."""

    def __init__(self, message: str = "kurkarte method requires kurkarte_id") -> None:
        super().__init__(message)


class SlotBookingError(RuntimeError):
    """Raised when a slot has reached its booking capacity."""

    def __init__(self, message: str = "slot at capacity") -> None:
        super().__init__(message)



# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------


def _payment_id() -> str:
    """Generate a payment ID with the 'pay-<uuid8>' format."""
    return f"pay-{uuid.uuid4().hex[:8]}"


def _spa_booking_id() -> str:
    """Generate a SpaBooking ID with the 'spbk-<uuid8>' format."""
    return f"spbk-{uuid.uuid4().hex[:8]}"


# Folio line template per AC-7 contract -- em-dash separators, Euro symbol.
_FOLIO_LINE_TEMPLATE = (
    "kurort_engine.spa_wellness \u2014 Spa booking \u2014 slot {slot_id} "
    "\u2014 guest {guest_id} \u2014 \u20ac{amount:.2f}"
)


# ---------------------------------------------------------------------------
# Payment (AC-6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, init=False)
class Payment:
    """A single payment applied to a Spa booking (AC-6).

    Public construction goes through ``Payment(booking, method, *, kurkarte_id)``
    which validates the method, derives ``amount_eur`` from
    ``booking.folio_price_eur``, and stamps ``processed_at`` at UTC now.
    The dataclass is frozen (immutable after construction) so it can be
    safely cached and shared across the booking pipeline.

    ``init=False`` suppresses the auto-generated ``__init__`` so we can
    expose the AC-6 verbatim signature ``Payment(booking, method, *,
    kurkarte_id=None)`` without leaking every dataclass field as a kwarg.
    """

    # dataclass fields (init=False so they aren't in __init__ signature).
    booking_id: str = field(default="")
    method: str = field(default="")
    amount_eur: Decimal = field(default=Decimal("0.00"))
    eur_currency_format: str = field(default="")
    kurkarte_id: str | None = field(default=None)
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=_payment_id)

    def __init__(
        self,
        booking: Any,
        method: str,
        *,
        kurkarte_id: str | None = None,
        **_kwargs: Any,
    ) -> None:
        """AC-6 public constructor: Payment(booking, method, *, kurkarte_id)."""
        if method not in ALLOWED_PAYMENT_METHODS:
            raise PaymentMethodError(
                f"method must be one of cash|sepa|kurkarte (got {method!r})"
            )
        if method == "kurkarte" and kurkarte_id is None:
            raise PaymentMethodKurkarteError(
                "kurkarte method requires kurkarte_id"
            )

        amount = Decimal(str(booking.folio_price_eur))
        # Frozen dataclass: bypass the freeze during construction with object.__setattr__.
        object.__setattr__(self, "id", _payment_id())
        object.__setattr__(self, "booking_id", booking.id)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "amount_eur", amount)
        object.__setattr__(self, "eur_currency_format", f"\u20ac{amount:.2f}")
        object.__setattr__(self, "kurkarte_id", kurkarte_id)
        object.__setattr__(self, "processed_at", datetime.now(UTC))


# ---------------------------------------------------------------------------
# SpaBooking (AC-7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, init=False)
class SpaBooking:
    """A persisted Spa slot booking (AC-7).

    Constructed via ``SpaBooking.book(guest_id, slot, payment)`` classmethod,
    which atomically increments ``slot.bookings_count`` and emits the
    EUR-currency guest-folio line. The dataclass is frozen.

    ``init=False`` suppresses the auto-generated ``__init__`` so the only
    public construction path is ``SpaBooking.book(...)``.
    """

    # dataclass fields (init=False so they aren't in __init__ signature).
    guest_id: str = field(default="")
    slot_id: str = field(default="")
    payment_id: str = field(default="")
    slot: Any = field(default=None)
    payment: Payment = field(default=None)  # type: ignore[assignment]
    folio_line: str = field(default="")
    folio_amount_eur: Decimal = field(default=Decimal("0.00"))
    folio_currency: str = field(default="EUR")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: str = field(default_factory=_spa_booking_id)

    # Convenience alias for the AC-8 report aggregator, which reads
    # `booking.amount_eur` (per the duck-typed AC-8 fixture). The canonical
    # AC-7 contract field is `folio_amount_eur`.
    @property
    def amount_eur(self) -> Decimal:
        return self.folio_amount_eur

    @classmethod
    def book(
        cls,
        guest_id: str,
        slot: Any,
        payment: Payment,
    ) -> SpaBooking:
        """Atomically increment slot.bookings_count and return a SpaBooking."""
        current = getattr(slot, "bookings_count", 0)
        capacity = getattr(slot, "capacity", 1)
        if current >= capacity:
            raise SlotBookingError("slot at capacity")

        try:
            object.__setattr__(slot, "bookings_count", current + 1)
        except (AttributeError, TypeError):
            slot.bookings_count = current + 1

        amount = payment.amount_eur
        folio_line = _FOLIO_LINE_TEMPLATE.format(
            slot_id=slot.id,
            guest_id=guest_id,
            amount=amount,
        )

        # Build the SpaBooking directly via object.__new__ + setattr, since
        # the dataclass __init__ is suppressed (init=False).
        booking = object.__new__(cls)
        object.__setattr__(booking, "id", _spa_booking_id())
        object.__setattr__(booking, "guest_id", guest_id)
        object.__setattr__(booking, "slot_id", slot.id)
        object.__setattr__(booking, "payment_id", payment.id)
        object.__setattr__(booking, "slot", slot)
        object.__setattr__(booking, "payment", payment)
        object.__setattr__(booking, "folio_line", folio_line)
        object.__setattr__(booking, "folio_amount_eur", amount)
        object.__setattr__(booking, "folio_currency", "EUR")
        object.__setattr__(booking, "created_at", datetime.now(UTC))
        return booking


__all__ = [
    "Payment",
    "PaymentMethodError",
    "PaymentMethodKurkarteError",
    "SlotBookingError",
    "SpaBooking",
]
