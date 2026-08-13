"""Toskana Therme ticket sale via Kur-/Gästekarte (AC-5).

The ``ToskanaThermeAdapter`` sells day-pass tickets to the Toskana Therme
(Toskanaworld Bad Orb) at a 20% Gästekarte discount when a valid Kurkarte
ID is presented. Per the spec.yaml PROTECTED block (AC-5 verbatim):

  - ``ToskanaThermeAdapter.sell_ticket(*, kurkarte_id, visit_date,
    ticket_type='day_pass')`` returns a ``ToskanaThermeTicket`` with
    ``list_price_eur == Decimal('22.50')`` and ``price_eur ==
    Decimal('18.00')`` (i.e. 22.50 x 0.80 = the G\u00e4stekarte rate).
  - ``kurkarte_id`` must be non-empty; ``None`` or empty raises
    ``ToskanaThermeKurkarteError``.

The HHV (Heilb\u00e4derverband) reference for this discount rate is recorded
in the spa/wellness resource-management design record
\u00a76.4 AC-5.

Pricing defaults live in :mod:`kurort_engine.spa_wellness.config`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from kurort_engine.spa_wellness.config import (
    GAESTEKARTE_DISCOUNT_FACTOR,
    TOSKANA_DAY_PASS_LIST_PRICE_EUR,
)

# ---------------------------------------------------------------------------
# Exception (per AC-5 contract)
# ---------------------------------------------------------------------------


class ToskanaThermeKurkarteError(ValueError):
    """Raised when the supplied kurkarte_id is None or empty."""

    def __init__(self, message: str = "kurkarte_id must be a non-empty string") -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# ID helpers + folio line template
# ---------------------------------------------------------------------------


def _ticket_id() -> str:
    """Generate a ToskanaThermeTicket ID with the 'tkt-<uuid8>' format."""
    return f"tkt-{uuid.uuid4().hex[:8]}"


def _build_folio_line(ticket_type: str, visit_date: str, price_eur: Decimal) -> str:
    """Render the verbatim AC-5 folio line for a ToskanaTherme ticket."""
    return (
        f"Toskana Therme ticket \u2014 {ticket_type} \u2014 "
        f"{visit_date} \u2014 \u20ac{price_eur:.2f} "
        f"(G\u00e4stekarte 20% discount applied)"
    )


# ---------------------------------------------------------------------------
# Ticket dataclass (AC-5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, init=False)
class ToskanaThermeTicket:
    """A Toskana Therme day-pass ticket sold via G\u00e4stekarte (AC-5).

    Fields:
      - id: auto-generated
      - kurkarte_id: from the buyer
      - visit_date: 'YYYY-MM-DD' string
      - ticket_type: 'day_pass' by default
      - list_price_eur: Decimal('22.50') (Toskanaworld 2026 day-pass)
      - guest_discount_applied: True when a valid G\u00e4stekarte was used
      - price_eur: list_price_eur x Decimal('0.80') = Decimal('18.00')
      - folio_line: the verbatim AC-5 string

    ``init=False`` suppresses the auto-generated ``__init__`` so we can
    derive the price/folio line from the supplied discount flag and
    list-price defaults in a single construction call.
    """

    kurkarte_id: str = field(default="")
    visit_date: str = field(default="")
    ticket_type: str = field(default="day_pass")
    list_price_eur: Decimal = field(default=TOSKANA_DAY_PASS_LIST_PRICE_EUR)
    guest_discount_applied: bool = field(default=True)
    price_eur: Decimal = field(default=TOSKANA_DAY_PASS_LIST_PRICE_EUR * GAESTEKARTE_DISCOUNT_FACTOR)
    folio_line: str = field(default="")
    id: str = field(default_factory=_ticket_id)

    def __init__(
        self,
        kurkarte_id: str,
        visit_date: str,
        ticket_type: str = "day_pass",
        *,
        list_price_eur: Decimal = TOSKANA_DAY_PASS_LIST_PRICE_EUR,
        guest_discount_applied: bool = True,
        price_eur: Decimal | None = None,
        folio_line: str | None = None,
        id: str | None = None,
    ) -> None:
        """Construct a ToskanaThermeTicket (AC-5).

        If ``price_eur`` or ``folio_line`` are not supplied they are
        derived from ``list_price_eur`` x ``GAESTEKARTE_DISCOUNT_FACTOR``
        (when ``guest_discount_applied=True``).
        """
        list_price = Decimal(str(list_price_eur))
        if price_eur is None:
            price_eur = (
                list_price * GAESTEKARTE_DISCOUNT_FACTOR
                if guest_discount_applied
                else list_price
            )
        price = Decimal(str(price_eur))
        if folio_line is None:
            folio_line = _build_folio_line(ticket_type, visit_date, price)

        object.__setattr__(self, "id", id if id is not None else _ticket_id())
        object.__setattr__(self, "kurkarte_id", kurkarte_id)
        object.__setattr__(self, "visit_date", visit_date)
        object.__setattr__(self, "ticket_type", ticket_type)
        object.__setattr__(self, "list_price_eur", list_price)
        object.__setattr__(self, "guest_discount_applied", bool(guest_discount_applied))
        object.__setattr__(self, "price_eur", price)
        object.__setattr__(self, "folio_line", folio_line)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ToskanaThermeAdapter:
    """The Kurort-vertical Toskana Therme ticket-sale adapter (AC-5).

    Validates ``kurkarte_id`` and returns a ``ToskanaThermeTicket`` with the
    20% G\u00e4stekarte discount applied. Currently a parameterised local
    stub \u2014 in production this would forward to the Toskanaworld
    voucher-issuance API (out of scope for AC-5).
    """

    def sell_ticket(
        self,
        *,
        kurkarte_id: str | None,
        visit_date: str,
        ticket_type: str = "day_pass",
    ) -> ToskanaThermeTicket:
        """Validate kurkarte_id and return a ToskanaThermeTicket (AC-5).

        Raises ``ToskanaThermeKurkarteError`` if ``kurkarte_id`` is None or
        the empty string.
        """
        if kurkarte_id is None or kurkarte_id == "":
            raise ToskanaThermeKurkarteError(
                "kurkarte_id must be a non-empty string"
            )

        return ToskanaThermeTicket(
            kurkarte_id=str(kurkarte_id),
            visit_date=visit_date,
            ticket_type=ticket_type,
        )


__all__ = [
    "ToskanaThermeAdapter",
    "ToskanaThermeTicket",
    "ToskanaThermeKurkarteError",
]
