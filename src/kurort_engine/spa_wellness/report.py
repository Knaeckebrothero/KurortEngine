"""DailySpaRevenueReport aggregator for kurort_engine.spa_wellness (AC-8).

Per the spec.yaml PROTECTED block (AC-8 verbatim):

  - ``generate_daily_spa_revenue_report(bookings, *, date='YYYY-MM-DD')``
    accepts a list of SpaBooking-shaped objects (duck-typed; the real
    ``SpaBooking`` and the AC-8 test fixtures both expose ``.slot``,
    ``.payment``, ``.amount_eur``, ``.folio_line``).
  - Filters bookings to those where ``booking.slot.date == date``.
  - Returns a ``DailySpaRevenueReport`` with:
    - ``per_resource_eur``: dict of resource-type \u2192 EUR sum
    - ``per_day_eur``: total EUR for the date
    - ``per_payment_method_eur``: dict of payment-method \u2192 EUR sum
    - ``booking_count``: number of bookings on the date
    - ``folio_lines``: tuple of EUR-currency formatted lines
  - Empty input \u2192 zeroed result (MUST NOT raise).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kurort_engine.spa_wellness.payment_adapter import SpaBooking


class DailySpaRevenueReport:
    """A per-day spa revenue report with breakdown by resource and payment method (AC-8).

    Fields:
      - date: the report date ('YYYY-MM-DD')
      - per_resource_eur: dict of resource_type \u2192 Decimal EUR sum
      - per_day_eur: Decimal total EUR (sum over the date)
      - per_payment_method_eur: dict of payment method \u2192 Decimal EUR sum
      - booking_count: int (number of bookings on the date)
      - folio_lines: tuple of EUR-currency formatted strings (one per booking)
    """

    __slots__ = (
        "date",
        "per_resource_eur",
        "per_day_eur",
        "per_payment_method_eur",
        "booking_count",
        "folio_lines",
    )

    def __init__(
        self,
        date: str,
        per_resource_eur: dict[str, Decimal],
        per_day_eur: Decimal,
        per_payment_method_eur: dict[str, Decimal],
        booking_count: int,
        folio_lines: tuple[str, ...],
    ) -> None:
        self.date = date
        self.per_resource_eur = dict(per_resource_eur)
        self.per_day_eur = Decimal(str(per_day_eur))
        self.per_payment_method_eur = dict(per_payment_method_eur)
        self.booking_count = int(booking_count)
        self.folio_lines = tuple(folio_lines)

    def __repr__(self) -> str:
        return (
            f"DailySpaRevenueReport(date={self.date!r}, "
            f"per_day_eur={self.per_day_eur!r}, "
            f"booking_count={self.booking_count!r}, "
            f"per_resource_eur={self.per_resource_eur!r}, "
            f"per_payment_method_eur={self.per_payment_method_eur!r})"
        )


def generate_daily_spa_revenue_report(
    bookings: Iterable[SpaBooking],
    *,
    date: str,
) -> DailySpaRevenueReport:
    """Aggregate a daily spa revenue report (AC-8).

    Steps:
      (1) Filter bookings to those on `date` (booking.slot.date == date).
      (2) For each kept booking, accumulate:
            - per_resource_eur[resource_type] += amount
            - per_payment_method_eur[method] += amount
            - per_day_eur += amount
            - folio_lines.append(folio_line)
      (3) Return DailySpaRevenueReport with the rolled-up fields.

    Empty `bookings` (or no bookings on the date) \u2192 zeroed result, no raise.
    """
    per_resource: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    per_method: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    per_day_total: Decimal = Decimal("0.00")
    folio_lines_list: list[str] = []
    booking_count = 0

    for booking in bookings:
        slot_date = booking.slot.date
        if slot_date != date:
            continue
        resource_type = booking.slot.resource.type
        method = booking.payment.method
        amount = Decimal(str(booking.amount_eur))
        per_resource[resource_type] = per_resource[resource_type] + amount
        per_method[method] = per_method[method] + amount
        per_day_total = per_day_total + amount
        folio_lines_list.append(booking.folio_line)
        booking_count += 1

    return DailySpaRevenueReport(
        date=date,
        per_resource_eur=dict(per_resource),
        per_day_eur=per_day_total,
        per_payment_method_eur=dict(per_method),
        booking_count=booking_count,
        folio_lines=tuple(folio_lines_list),
    )




__all__ = [
    "DailySpaRevenueReport",
    "generate_daily_spa_revenue_report",
]
