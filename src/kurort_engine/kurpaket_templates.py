"""Q5.7 Kurpaket template catalog (5 tiers, frozen dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class KurpaketTemplate:
    code: str
    name: str
    nights: int
    spa_treatments_total: int
    spa_treatments_per_day: int
    board: str
    price_eur: Decimal
    muster13_required: bool
    heilbad_eligible: bool


# AC-1 Kurzurlaub-Wochenende 3-Nächte Fri-Sun (≤€195 per person).
TEMPLATE_A = KurpaketTemplate(
    code="A", name="Kurzurlaub-Wochenende", nights=3,
    spa_treatments_total=3, spa_treatments_per_day=1,
    board="optional", price_eur=Decimal("189.00"),
    muster13_required=False, heilbad_eligible=False,
)

# AC-2 Classic 7-Nächte HHB-In-Balance ≥€1,169.
TEMPLATE_B = KurpaketTemplate(
    code="B", name="Classic-Kurpaket", nights=7,
    spa_treatments_total=4, spa_treatments_per_day=1,
    board="full", price_eur=Decimal("1169.00"),
    muster13_required=False, heilbad_eligible=True,
)

# AC-3 Premium 10-Nächte HHB-In-Balance (within ±10% of €1,169).
TEMPLATE_C = KurpaketTemplate(
    code="C", name="Premium-Kurpaket", nights=10,
    spa_treatments_total=6, spa_treatments_per_day=1,
    board="full", price_eur=Decimal("1199.00"),
    muster13_required=False, heilbad_eligible=True,
)

# AC-4 Intensiv 14-Nächte HHB-In-Balance (within ±10% of €1,169).
TEMPLATE_D = KurpaketTemplate(
    code="D", name="Intensiv-Kurpaket", nights=14,
    spa_treatments_total=8, spa_treatments_per_day=1,
    board="full", price_eur=Decimal("1249.00"),
    muster13_required=False, heilbad_eligible=True,
)

# AC-5 Spezial-Heilbad 21-Nächte — requires §23 SGB V Muster 13.
TEMPLATE_E = KurpaketTemplate(
    code="E", name="Spezial-Heilbad", nights=21,
    spa_treatments_total=21, spa_treatments_per_day=1,
    board="full", price_eur=Decimal("1799.00"),
    muster13_required=True, heilbad_eligible=True,
)

TEMPLATES: dict[str, KurpaketTemplate] = {
    "A": TEMPLATE_A, "B": TEMPLATE_B, "C": TEMPLATE_C,
    "D": TEMPLATE_D, "E": TEMPLATE_E,
}


def get_template(code: str) -> KurpaketTemplate:
    """Return the template for ``code`` (case-insensitive)."""
    return TEMPLATES[code.upper()]