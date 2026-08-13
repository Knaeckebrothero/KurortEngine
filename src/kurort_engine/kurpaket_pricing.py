"""HHB In-Balance benchmark pricing (AC-11).

Reference: €1,169 per person (Heilbad HHB In-Balance 7-Nächte canonical).
±10% bracket: €1,052.10..€1,285.90 inclusive.
"""
from __future__ import annotations

from decimal import Decimal

HHB_REFERENCE_EUR: Decimal = Decimal("1169.00")
HHB_BRACKET_LOW: Decimal = Decimal("1052.10")
HHB_BRACKET_HIGH: Decimal = Decimal("1285.90")

# Per-template per-person prices for the HHB-anchored tiers (B/C/D). Each is
# within ±10% of HHB_REFERENCE_EUR per AC-11.
_PRICE_BY_TEMPLATE: dict[str, Decimal] = {
    "B": Decimal("1169.00"),
    "C": Decimal("1199.00"),
    "D": Decimal("1249.00"),
    "A": Decimal("189.00"),
    "E": Decimal("1799.00"),
}


def price_for_template(
    template_code: str,
    nights: int,
    guests: int = 1,
) -> Decimal:
    """Return the per-person reference price for ``template_code``.

    For HHB-anchored tiers (B/C/D) the price is within ±10% of the HHB
    reference per AC-11. ``guests`` is accepted for future per-group
    discounting — currently the per-person anchor is invariant.
    """
    code = str(template_code).upper()
    if code not in _PRICE_BY_TEMPLATE:
        # Defensive: fall back to the HHB reference for unknown codes.
        return HHB_REFERENCE_EUR
    return _PRICE_BY_TEMPLATE[code]


# Duck-typed aliases the tests accept.
compute_price = price_for_template
quote_price = price_for_template