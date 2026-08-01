"""AC-8: Daily Spa revenue report (per-resource + per-day + payment-method breakdown).

Test_oracle path recorded in spec.yaml:155 and spec_lock.md PROTECTED block.
This is the red-phase test for AC-8 that will fail with an AssertionError
against the placeholder (or absent) implementation. The
`kurort_engine.spa_wellness.report` submodule does not yet exist;
`generate_daily_spa_revenue_report` and `DailySpaRevenueReport` are not
yet importable.

AC-8 contract (spec.yaml:144-155):
    Event-driven. When `generate_daily_spa_revenue_report(bookings, *,
    date='YYYY-MM-DD')` is invoked with a list of `SpaBooking` objects and
    a `date`, the function shall return a `DailySpaRevenueReport` carrying
    `report.date == date`,
    `report.per_resource_eur == {resource_type: Decimal('EUR total'), ...}`
    (one entry per distinct `Resource.type` appearing in the bookings on
    that date),
    `report.per_day_eur == Decimal('sum of all booking amounts for the
    date')`,
    `report.per_payment_method_eur == {method: Decimal('EUR total'), ...}`
    (one entry per distinct `Payment.method`),
    `report.booking_count == N` (the number of bookings on that date), and
    `report.folio_lines == tuple[str, ...]` (the per-booking EUR-currency
    formatted folio lines for that date). Bookings on a date other than
    `date` shall be excluded. Empty input list yields zeroed result (NOT raise).

RED VERIFY
----------
This test is expected to FAIL during the red phase. The failure mode MUST be
`AssertionError` (a failing assertion on the helper gate), NOT
`ImportError` / `ModuleNotFoundError`.

The fixture `repo/tests/fixtures/spa_wellness_hotel_rheinland.yaml` is
created at the same time but is NOT consumed by the green phase (the test
fixture ships as documentation/traceability, not as runtime input).
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-8 contract constants (verbatim from spec.yaml PROTECTED block)
# ---------------------------------------------------------------------------

AC8_TEST_DATE: str = "2026-12-20"
AC8_OTHER_DATE: str = "2026-12-21"  # must be excluded by the filter

AC8_SAUNA_PRICE_EUR: Decimal = Decimal("8.00")
AC8_MASSAGE_PRICE_EUR: Decimal = Decimal("35.00")

# Expected totals computed from the 3-booking fixture:
#   Sauna cash 8.00 + Sauna kurkarte 8.00 + Massage cash 35.00
AC8_EXPECTED_PER_RESOURCE_EUR: dict[str, Decimal] = {
    "sauna": Decimal("16.00"),     # 2 × 8.00
    "massage": Decimal("35.00"),   # 1 × 35.00
}
AC8_EXPECTED_PER_DAY_EUR: Decimal = Decimal("51.00")  # 16 + 35
AC8_EXPECTED_PER_PAYMENT_METHOD_EUR: dict[str, Decimal] = {
    "cash": Decimal("43.00"),      # 8.00 + 35.00
    "kurkarte": Decimal("8.00"),   # 8.00 (one kurkarte booking)
}
AC8_EXPECTED_BOOKING_COUNT: int = 3
AC8_EXPECTED_FOLIO_LINES_COUNT: int = 3


def _load_report_or_assert():
    """Import `kurort_engine.spa_wellness.report` and return the module.

    Raises `AssertionError` (NOT `ModuleNotFoundError`) when the submodule is
    absent — AC-8 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("kurort_engine.spa_wellness")
    assert spec is not None, (
        "AC-8 contract violated: kurort_engine.spa_wellness package not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the package."
    )
    spec2 = importlib.util.find_spec("kurort_engine.spa_wellness.report")
    assert spec2 is not None, (
        "AC-8 contract violated: kurort_engine.spa_wellness.report submodule "
        "not found in sys.path. The red phase expects this AssertionError "
        "(NOT ImportError) until the green phase implements the submodule "
        "under repo/src/kurort_engine/spa_wellness/report.py."
    )
    module = importlib.import_module("kurort_engine.spa_wellness.report")
    return module


def _make_test_booking(date: str, amount_eur: Decimal, method: str,
                       resource_type: str, folio_line: str, booking_id: str):
    """Build a minimal booking-shaped object for the report tests.

    The DailySpaRevenueReport aggregator (per AC-8) needs:
      - booking.slot.date (for the date filter)
      - booking.amount_eur (for the per-day sum)
      - booking.payment.method (for the per-payment-method breakdown)
      - booking.slot.resource.type (for the per-resource breakdown)
      - booking.folio_line (for the per-booking EUR-currency formatted line)
    """
    from types import SimpleNamespace

    return SimpleNamespace(
        id=booking_id,
        slot=SimpleNamespace(date=date, resource=SimpleNamespace(type=resource_type)),
        payment=SimpleNamespace(method=method),
        amount_eur=amount_eur,
        folio_line=folio_line,
    )


def test_ac8_daily_spa_revenue_report_breakdown() -> None:
    """AC-8 master contract: daily revenue breakdown by resource, day, payment method.

    Test fixture (3 bookings on 2026-12-20 + 1 booking on 2026-12-21 to test the
    date filter):
      - b1: 2026-12-20 sauna cash   €8.00
      - b2: 2026-12-20 sauna kurkarte €8.00
      - b3: 2026-12-20 massage cash €35.00
      - b4: 2026-12-21 sauna cash   €8.00  ← MUST be excluded

    Asserts:
      - report.date == '2026-12-20'
      - report.per_resource_eur == {'sauna': 16.00, 'massage': 35.00}
      - report.per_day_eur == Decimal('51.00')
      - report.per_payment_method_eur == {'cash': 43.00, 'kurkarte': 8.00}
      - report.booking_count == 3 (excluding b4)
      - len(report.folio_lines) == 3 (excluding b4)
    """
    module = _load_report_or_assert()

    generate_daily_spa_revenue_report = getattr(
        module, "generate_daily_spa_revenue_report", None
    )
    DailySpaRevenueReport = getattr(module, "DailySpaRevenueReport", None)
    assert generate_daily_spa_revenue_report is not None, (
        "AC-8 contract violated: generate_daily_spa_revenue_report is missing "
        "from kurort_engine.spa_wellness.report. Red phase expects this "
        "AssertionError until the green phase adds the aggregator function."
    )
    assert DailySpaRevenueReport is not None, (
        "AC-8 contract violated: DailySpaRevenueReport is missing from "
        "kurort_engine.spa_wellness.report. Red phase expects this "
        "AssertionError until the green phase adds the report dataclass."
    )

    # 4 bookings total: 3 on 2026-12-20, 1 on 2026-12-21
    b1 = _make_test_booking(
        date=AC8_TEST_DATE,
        amount_eur=AC8_SAUNA_PRICE_EUR,
        method="cash",
        resource_type="sauna",
        folio_line="Spa booking — sauna — 2026-12-20 — €8.00 (cash)",
        booking_id="b1",
    )
    b2 = _make_test_booking(
        date=AC8_TEST_DATE,
        amount_eur=AC8_SAUNA_PRICE_EUR,
        method="kurkarte",
        resource_type="sauna",
        folio_line="Spa booking — sauna — 2026-12-20 — €8.00 (kurkarte)",
        booking_id="b2",
    )
    b3 = _make_test_booking(
        date=AC8_TEST_DATE,
        amount_eur=AC8_MASSAGE_PRICE_EUR,
        method="cash",
        resource_type="massage",
        folio_line="Spa booking — massage — 2026-12-20 — €35.00 (cash)",
        booking_id="b3",
    )
    b4 = _make_test_booking(
        date=AC8_OTHER_DATE,  # different date → MUST be excluded
        amount_eur=AC8_SAUNA_PRICE_EUR,
        method="cash",
        resource_type="sauna",
        folio_line="Spa booking — sauna — 2026-12-21 — €8.00 (cash)",
        booking_id="b4",
    )

    report = generate_daily_spa_revenue_report(
        bookings=[b1, b2, b3, b4], date=AC8_TEST_DATE
    )

    # --- per-day fields ---
    assert report.date == AC8_TEST_DATE, (
        f"AC-8 contract violated: report.date={report.date!r} expected "
        f"{AC8_TEST_DATE!r}"
    )
    assert report.booking_count == AC8_EXPECTED_BOOKING_COUNT, (
        f"AC-8 contract violated: report.booking_count={report.booking_count!r} "
        f"expected {AC8_EXPECTED_BOOKING_COUNT!r} (the 3 bookings on "
        f"{AC8_TEST_DATE}; the booking on {AC8_OTHER_DATE} MUST be excluded)"
    )
    assert report.per_day_eur == AC8_EXPECTED_PER_DAY_EUR, (
        f"AC-8 contract violated: report.per_day_eur={report.per_day_eur!r} "
        f"expected {AC8_EXPECTED_PER_DAY_EUR!r} (= 16.00 + 35.00)"
    )

    # --- per-resource breakdown ---
    assert report.per_resource_eur == AC8_EXPECTED_PER_RESOURCE_EUR, (
        f"AC-8 contract violated: report.per_resource_eur="
        f"{report.per_resource_eur!r} expected "
        f"{AC8_EXPECTED_PER_RESOURCE_EUR!r}"
    )

    # --- per-payment-method breakdown ---
    assert report.per_payment_method_eur == AC8_EXPECTED_PER_PAYMENT_METHOD_EUR, (
        f"AC-8 contract violated: report.per_payment_method_eur="
        f"{report.per_payment_method_eur!r} expected "
        f"{AC8_EXPECTED_PER_PAYMENT_METHOD_EUR!r}"
    )

    # --- folio_lines list (one per booking on the date, NOT per the input list) ---
    assert len(report.folio_lines) == AC8_EXPECTED_FOLIO_LINES_COUNT, (
        f"AC-8 contract violated: len(report.folio_lines)="
        f"{len(report.folio_lines)!r} expected "
        f"{AC8_EXPECTED_FOLIO_LINES_COUNT!r} (3 bookings on {AC8_TEST_DATE}; "
        f"the {AC8_OTHER_DATE} booking MUST be excluded)"
    )