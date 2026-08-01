"""AC-2: Per-reservation automatic Kurtaxe posting (age-band + Schwerbehindert matching).

Test_oracle path recorded in spec.yaml:72. This is the red-phase test that
will fail with an AssertionError against the placeholder implementation
(``calculate_kurtaxe_for_reservation`` currently returns ``Decimal('0.00')``).

The placeholder contract — Guest, Reservation, calculate_kurtaxe_for_reservation
— lives in ``kurort_engine.calculator``. The fixture factory (cached Satzung +
age-anchored Guest) lives in ``tests._factories``.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from kurort_engine import Guest, Reservation, calculate_kurtaxe_for_reservation

from tests._factories import hessen_satzung, make_guest  # noqa: F401  (fixtures re-exported)


def test_ac2_per_reservation_automatic_kurtaxe_posting_by_age_band(
    hessen_satzung,
) -> None:
    # ---- Day-count rule: 2024-06-10 -> 2024-06-13 = 3 nights = 3 days ------
    arrival = date(2024, 6, 10)
    departure = date(2024, 6, 13)
    day_count = (departure - arrival).days
    assert day_count == 3

    # ---- Multi-guest reservation: adult + child + Schwerbehinderter (GdB 80)
    # Per Bad Orb Satzung 01.07.2020:
    #   adult (age 35, no disability)                  -> band `adult`              (€2.50/day)
    #   child (age 5,  no disability)                  -> band `child`              (€0.00/day)
    #   Schwerbehinderter (age 50, disability_pct=80)  -> band `adult_disabled_70`  (€1.25/day)
    reservation = Reservation(
        reservation_id="R-2024-001",
        arrival=arrival,
        departure=departure,
        guests=(
            make_guest(age_years=35, name="Anna Vollzahler"),
            make_guest(age_years=5, name="Kim Kind"),
            make_guest(
                age_years=50,
                disability_pct=80,
                name="Erika Schwerbehindert",
            ),
        ),
    )

    total = calculate_kurtaxe_for_reservation(reservation, hessen_satzung)

    # Return type must be Decimal (no float drift on currency totals).
    assert isinstance(total, Decimal), (
        f"calculate_kurtaxe_for_reservation must return Decimal, got {type(total).__name__}"
    )

    # Σ per_guest_rate × day_count = 2.50*3 + 0.00*3 + 1.25*3 = 11.25
    expected = Decimal("2.50") * 3 + Decimal("0.00") * 3 + Decimal("1.25") * 3
    assert total == expected == Decimal("11.25"), (
        f"expected Decimal('11.25') for 3 guests × 3 nights, got {total!r}"
    )


def test_ac2_single_adult_one_night_returns_decimal_two_fifty(hessen_satzung) -> None:
    """A 1-guest 1-night reservation (adult age 30) must return Decimal('2.50').

    Covers the minimum viable input shape and proves the algorithm works for
    trivial day counts (no off-by-one in the (departure - arrival).days rule).
    """
    reservation = Reservation(
        reservation_id="R-2024-002",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 11),
        guests=(make_guest(age_years=30, name="Solo Adult"),),
    )

    total = calculate_kurtaxe_for_reservation(reservation, hessen_satzung)

    assert isinstance(total, Decimal)
    assert total == Decimal("2.50"), (
        f"single adult / single night must yield Decimal('2.50'), got {total!r}"
    )


def test_ac2_schwerbehinderter_gdb_100_routes_to_disabled_70_band(hessen_satzung) -> None:
    """A Schwerbehinderter with disability_pct=100 still routes to ``adult_disabled_70``.

    AC-2 governs tariff-band matching only. The ``schwerbehindert_100``
    exemption (zero-EUR posting + audit entry) is a SEPARATE concern handled
    by AC-3. Here we assert that the band matcher does NOT silently fall
    through to a zero-rate band when GdB reaches 100; the matching band is
    ``adult_disabled_70`` (€1.25/day) and AC-3's exemption logic will zero
    it out later in the pipeline.

    Sanity check: a single Schwerbehinderter (GdB 100, age 50) for 3 nights
    must yield 1.25 × 3 = 3.75 — NOT 0.00 (which would imply the band
    matcher dropped the guest or hit a no-bound disability_pct_max=0 sentinel).
    """
    reservation = Reservation(
        reservation_id="R-2024-003",
        arrival=date(2024, 6, 10),
        departure=date(2024, 6, 13),
        guests=(
            make_guest(
                age_years=50,
                disability_pct=100,
                name="Max Schwerbehindert 100",
            ),
        ),
    )

    total = calculate_kurtaxe_for_reservation(reservation, hessen_satzung)

    assert isinstance(total, Decimal)
    assert total == Decimal("1.25") * 3 == Decimal("3.75"), (
        f"Schwerbehinderter GdB 100 must still route to adult_disabled_70 "
        f"(1.25/day × 3 = 3.75); got {total!r} — if 0.00, the band matcher "
        f"is falling through past the disabled band (AC-2 bug, AC-3 fix)."
    )