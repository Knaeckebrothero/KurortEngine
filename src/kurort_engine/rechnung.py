"""Badekur Rechnung layout for Krankenkasse §23 SGB V submission (AC-5).

Renders a printable, Krankenkasse-submittable Rechnung for a single
reservation. The layout separates "Zuschussfähige Posten" into the
three sub-totals Krankenkassen reimburse under §23 SGB V:

  - Kurtaxe       (per-day Kurtaxe — from the Satzung rate bands)
  - Übernachtung  (per-night accommodation — from the reservation's
                   "übernachtung" folio entries)
  - Verpflegung   (per-night board — from the reservation's
                   "verpflegung" folio entries)

The footer cites the legal §23 SGB V reimbursement paragraph verbatim.
A Krankenkasse reviewer must be able to grep the printed Rechnung for
``Badekur/Ambulante Vorsorge §23 SGB V`` to authorise payment; the
string is bit-for-bit pinned by the spec and must not drift.

Spec contract (spec.yaml:98-105):
    build_badekur_rechnung(reservation, satzung, folios) -> str

Where ``folios`` is a ``dict[str, list[Decimal]]`` keyed by category
name (case-sensitive lowercase umlaut keys: ``übernachtung``,
``verpflegung``). The exact shape is not pinned by the spec; this
implementation uses a flat per-category list. Categories not present
in the folios dict contribute ``Decimal("0.00")``.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from kurort_engine.calculator import (
    Reservation,
    calculate_kurtaxe_for_reservation,
)
from kurort_engine.rates import Satzung

# Verbatim §23 SGB V citation from spec.yaml:104. The Krankenkasse
# reviewer greps for this exact string on the printed Rechnung. Any
# drift (missing slash, lower-case "sgb", ASCII "Section" instead of
# "§") invalidates the Rechnung for reimbursement.
AC5_FOOTER_TEXT: str = "Badekur/Ambulante Vorsorge §23 SGB V"


# Folios category keys (lowercase, umlaut as in spec/_factories).
_FOLIO_UEBERNACHTUNG: str = "übernachtung"
_FOLIO_VERPFLEGUNG: str = "verpflegung"


def _sum_folio(folios: Mapping[str, list[Decimal]], category: str) -> Decimal:
    """Return the per-category sub-total across ``folios[category]``.

    Missing categories contribute ``Decimal("0.00")`` so the rendered
    Rechnung never silently omits a Zuschussfähige Posten.
    """
    entries = folios.get(category) or []
    total = Decimal("0.00")
    for entry in entries:
        total += Decimal(entry)
    return total.quantize(Decimal("0.01"))


def _format_eur(amount: Decimal) -> str:
    """Render a EUR amount using the German comma convention.

    Output form: ``"5,00 EUR"``. The thousands separator is omitted to
    keep the Zuschussfähige Posten block readable on a single printed
    column; if amounts grow into the thousands, swap to
    ``"{:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")``
    here only — every other consumer of the Rechnung treats the comma
    as the decimal separator.
    """
    quantized = Decimal(amount).quantize(Decimal("0.01"))
    return f"{quantized:.2f}".replace(".", ",") + " EUR"


def build_badekur_rechnung(
    reservation: Reservation,
    satzung: Satzung,
    folios: Mapping[str, list[Decimal]],
) -> str:
    """Render the Badekur Rechnung for ``reservation`` under ``satzung``.

    AC-5 contract:
      - Signature: ``(reservation, satzung, folios)`` — exactly three
        positional parameters, no ``exemptions=``, no ``out_path=``.
      - Returns a non-empty ``str`` containing the three Zuschussfähige
        Posten labels (``Kurtaxe``, ``Übernachtung``, ``Verpflegung``)
        and the verbatim footer ``AC5_FOOTER_TEXT``.

    The Kurtaxe sub-total is sourced from
    :func:`calculate_kurtaxe_for_reservation` (the engine's canonical
    Kurtaxe computation — AC-1/AC-2); the Übernachtung and Verpflegung
    sub-totals are sourced from the per-night ``folios`` dict. The
    function emits no audit entries — the AC-7 spec at line 124 names
    only ``rates/exemptions/reporting`` actors, and AC-5 is a rendering
    pass that does not alter the auditable Kurtaxe stream.
    """
    kurtaxe_total = calculate_kurtaxe_for_reservation(reservation, satzung)
    uebernachtung_total = _sum_folio(folios, _FOLIO_UEBERNACHTUNG)
    verpflegung_total = _sum_folio(folios, _FOLIO_VERPFLEGUNG)

    guest_name = ", ".join(guest.name for guest in reservation.guests) or "(kein Gast)"
    stay_range = (
        f"{reservation.arrival.isoformat()} - {reservation.departure.isoformat()}"
    )

    lines: tuple[str, ...] = (
        "Rechnung",
        f"  Reservierung: {reservation.reservation_id}",
        f"  Gast:         {guest_name}",
        f"  Aufenthalt:   {stay_range}",
        "",
        "Zuschussfähige Posten:",
        f"  Kurtaxe:      {_format_eur(kurtaxe_total)}",
        f"  Übernachtung: {_format_eur(uebernachtung_total)}",
        f"  Verpflegung:  {_format_eur(verpflegung_total)}",
        "",
        AC5_FOOTER_TEXT,
    )
    return "\n".join(lines) + "\n"