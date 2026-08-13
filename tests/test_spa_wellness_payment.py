"""AC-6 + AC-7: Spa payment integration + Guest folio line integration with EUR currency.

Test_oracle paths recorded in spec.yaml:127,142 and spec_lock.md PROTECTED block.
This is the red-phase test for AC-6 + AC-7 that will fail with an AssertionError
against the placeholder (or absent) implementation. The
`kurort_engine.spa_wellness.payment_adapter` submodule does not yet exist;
`Payment`, `PaymentMethodError`, `PaymentMethodKurkarteError`, and
`SpaBooking` are not yet importable.

AC-6 contract (spec.yaml:115-127):
    Ubiquitous. The `payment_adapter` module shall expose a
    `Payment(booking, method, *, kurkarte_id=None)` constructor that accepts
    `method in frozenset({'cash', 'sepa', 'kurkarte'})` and shall return a
    `Payment` object carrying
    `payment.method == method`,
    `payment.booking_id == booking.id`,
    `payment.kurkarte_id == kurkarte_id`,
    `payment.amount_eur == booking.folio_price_eur`,
    `payment.eur_currency_format == '€' + str(amount_eur)` formatted to 2
    decimal places, and `payment.processed_at` set to current UTC datetime.
    If `method == 'kurkarte'` and `kurkarte_id is None`, raise
    `PaymentMethodKurkarteError`. If `method` not in the allowed set, raise
    `PaymentMethodError`.

AC-7 contract (spec.yaml:129-142):
    Event-driven. When `SpaBooking.book(guest_id, slot, payment)` is invoked
    with a `guest_id='g1'`, a `Slot` object, and a `Payment` object, the
    returned `SpaBooking` shall carry
    `booking.guest_id == 'g1'`,
    `booking.slot_id == slot.id`,
    `booking.payment_id == payment.id`,
    `booking.folio_line == 'kurort_engine.spa_wellness — Spa booking — slot
    {slot.id} — guest g1 — €{amount_eur:.2f}'`,
    `booking.folio_amount_eur == payment.amount_eur`, and
    `booking.folio_currency == 'EUR'`. The booking atomically increments
    `slot.bookings_count` by 1.

RED VERIFY
----------
These tests are expected to FAIL during the red phase. The failure mode MUST be
`AssertionError` (a failing assertion on the helper gate), NOT
`ImportError` / `ModuleNotFoundError`.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-6 + AC-7 contract constants (verbatim from spec.yaml PROTECTED block)
# ---------------------------------------------------------------------------

AC6_TEST_BOOKING_ID: str = "bk-test-001"
AC6_TEST_GUEST_ID: str = "g1"
AC6_TEST_KURKARTE_ID: str = "k1"
AC6_SAUNA_PRICE_EUR: Decimal = Decimal("8.00")
AC6_MASSAGE_PRICE_EUR: Decimal = Decimal("35.00")

AC7_EXPECTED_FOLIO_LINE_PREFIX: str = "kurort_engine.spa_wellness — Spa booking — slot "
AC7_EXPECTED_FOLIO_LINE_SUFFIX: str = " — guest g1 — €8.00"
AC7_EXPECTED_FOLIO_CURRENCY: str = "EUR"


def _load_payment_or_assert():
    """Import `kurort_engine.spa_wellness.payment_adapter` and return the module.

    Raises `AssertionError` (NOT `ModuleNotFoundError`) when the submodule is
    absent — AC-6 + AC-7 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("kurort_engine.spa_wellness")
    assert spec is not None, (
        "AC-6 + AC-7 contract violated: kurort_engine.spa_wellness package not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the package."
    )
    spec2 = importlib.util.find_spec("kurort_engine.spa_wellness.payment_adapter")
    assert spec2 is not None, (
        "AC-6 + AC-7 contract violated: "
        "kurort_engine.spa_wellness.payment_adapter submodule not found. "
        "Red phase expects this AssertionError (NOT ImportError) until the "
        "green phase implements the submodule under "
        "repo/src/kurort_engine/spa_wellness/payment_adapter.py."
    )
    module = importlib.import_module("kurort_engine.spa_wellness.payment_adapter")
    return module


def _make_test_booking(module, booking_id: str, price_eur: Decimal):
    """Build a minimal booking-shaped object for the payment tests.

    The Payment constructor (per AC-6) needs `booking.id` and
    `booking.folio_price_eur`. We use a tiny helper dataclass via
    `types.SimpleNamespace` so the test stays focused on the AC-6 contract.
    """
    from types import SimpleNamespace

    return SimpleNamespace(id=booking_id, folio_price_eur=price_eur)


def test_ac6_payment_integration_cash_sepa_kurkarte() -> None:
    """AC-6 master contract: Payment accepts cash / sepa / kurkarte methods.

    Verifies:
      1. Payment(cash) -> payment.method == 'cash', amount_eur == booking.price,
         eur_currency_format == '€8.00'
      2. Payment(sepa) -> payment.method == 'sepa', amount_eur == booking.price
      3. Payment(kurkarte, kurkarte_id='k1') -> payment.method == 'kurkarte',
         payment.kurkarte_id == 'k1'
      4. Payment(kurkarte, kurkarte_id=None) RAISES PaymentMethodKurkarteError
    """
    import pytest

    module = _load_payment_or_assert()

    Payment = getattr(module, "Payment", None)
    PaymentMethodKurkarteError = getattr(module, "PaymentMethodKurkarteError", None)
    PaymentMethodError = getattr(module, "PaymentMethodError", None)
    assert Payment is not None, (
        "AC-6 contract violated: Payment is missing from "
        "kurort_engine.spa_wellness.payment_adapter. Red phase expects this "
        "AssertionError until the green phase adds the Payment class."
    )
    assert PaymentMethodKurkarteError is not None, (
        "AC-6 contract violated: PaymentMethodKurkarteError is missing. "
        "Red phase expects this AssertionError until the green phase adds the "
        "kurkarte validation exception."
    )
    assert PaymentMethodError is not None, (
        "AC-6 contract violated: PaymentMethodError is missing. Red phase "
        "expects this AssertionError until the green phase adds the method "
        "validation exception."
    )

    # --- Test 1: cash payment for an €8.00 booking ---
    booking_cash = _make_test_booking(module, AC6_TEST_BOOKING_ID, AC6_SAUNA_PRICE_EUR)
    payment_cash = Payment(booking_cash, method="cash")

    assert payment_cash.method == "cash", (
        f"AC-6 contract violated: payment_cash.method={payment_cash.method!r} "
        f"expected 'cash'"
    )
    assert payment_cash.booking_id == AC6_TEST_BOOKING_ID, (
        f"AC-6 contract violated: payment_cash.booking_id="
        f"{payment_cash.booking_id!r} expected {AC6_TEST_BOOKING_ID!r}"
    )
    assert payment_cash.amount_eur == AC6_SAUNA_PRICE_EUR, (
        f"AC-6 contract violated: payment_cash.amount_eur="
        f"{payment_cash.amount_eur!r} expected {AC6_SAUNA_PRICE_EUR!r} "
        f"(booking.folio_price_eur verbatim, no rounding)"
    )
    assert payment_cash.eur_currency_format == "€8.00", (
        f"AC-6 contract violated: payment_cash.eur_currency_format="
        f"{payment_cash.eur_currency_format!r} expected '€8.00' (2 dp)"
    )

    # --- Test 2: sepa payment for an €35.00 booking ---
    booking_sepa = _make_test_booking(module, "bk-test-002", AC6_MASSAGE_PRICE_EUR)
    payment_sepa = Payment(booking_sepa, method="sepa")
    assert payment_sepa.method == "sepa", (
        f"AC-6 contract violated: payment_sepa.method={payment_sepa.method!r} "
        f"expected 'sepa'"
    )
    assert payment_sepa.amount_eur == AC6_MASSAGE_PRICE_EUR, (
        f"AC-6 contract violated: payment_sepa.amount_eur="
        f"{payment_sepa.amount_eur!r} expected {AC6_MASSAGE_PRICE_EUR!r}"
    )
    assert payment_sepa.eur_currency_format == "€35.00", (
        f"AC-6 contract violated: payment_sepa.eur_currency_format="
        f"{payment_sepa.eur_currency_format!r} expected '€35.00' (2 dp)"
    )

    # --- Test 3: kurkarte payment with valid kurkarte_id ---
    booking_kk = _make_test_booking(module, "bk-test-003", AC6_SAUNA_PRICE_EUR)
    payment_kk = Payment(booking_kk, method="kurkarte", kurkarte_id=AC6_TEST_KURKARTE_ID)
    assert payment_kk.method == "kurkarte", (
        f"AC-6 contract violated: payment_kk.method={payment_kk.method!r} "
        f"expected 'kurkarte'"
    )
    assert payment_kk.kurkarte_id == AC6_TEST_KURKARTE_ID, (
        f"AC-6 contract violated: payment_kk.kurkarte_id="
        f"{payment_kk.kurkarte_id!r} expected {AC6_TEST_KURKARTE_ID!r}"
    )

    # --- Test 4: kurkarte payment without kurkarte_id RAISES ---
    booking_bad = _make_test_booking(module, "bk-test-004", AC6_SAUNA_PRICE_EUR)
    with pytest.raises(PaymentMethodKurkarteError) as excinfo:
        Payment(booking_bad, method="kurkarte", kurkarte_id=None)
    assert "kurkarte" in str(excinfo.value).lower(), (
        f"AC-6 contract violated: PaymentMethodKurkarteError message="
        f"{str(excinfo.value)!r} expected to mention 'kurkarte'"
    )


def test_ac7_guest_folio_line_integration_with_eur_currency() -> None:
    """AC-7 master contract: SpaBooking.book emits EUR-currency guest folio line.

    Verifies:
      1. SpaBooking.book(guest_id='g1', slot=slot, payment=payment) returns
         a SpaBooking carrying guest_id, slot_id, payment_id, folio_line,
         folio_amount_eur, folio_currency
      2. folio_line starts with 'kurort_engine.spa_wellness — Spa booking — slot '
         and ends with ' — guest g1 — €8.00'
      3. folio_amount_eur == payment.amount_eur
      4. folio_currency == 'EUR'
      5. slot.bookings_count is incremented by 1
    """
    module = _load_payment_or_assert()

    Payment = getattr(module, "Payment", None)
    SpaBooking = getattr(module, "SpaBooking", None)
    assert Payment is not None and SpaBooking is not None, (
        "AC-7 contract violated: Payment or SpaBooking is missing. Red phase "
        "expects this AssertionError until the green phase adds them."
    )

    # Build minimal slot-shaped object for the booking call.
    from types import SimpleNamespace

    slot = SimpleNamespace(
        id="sa-2026-12-20-T16:00",
        bookings_count=0,
        resource=SimpleNamespace(type="sauna"),
    )
    booking_for_payment = SimpleNamespace(
        id=AC6_TEST_BOOKING_ID, folio_price_eur=AC6_SAUNA_PRICE_EUR
    )
    payment = Payment(booking_for_payment, method="cash")

    spa_booking = SpaBooking.book(guest_id=AC6_TEST_GUEST_ID, slot=slot, payment=payment)

    assert spa_booking.guest_id == AC6_TEST_GUEST_ID, (
        f"AC-7 contract violated: spa_booking.guest_id={spa_booking.guest_id!r} "
        f"expected {AC6_TEST_GUEST_ID!r}"
    )
    assert spa_booking.slot_id == slot.id, (
        f"AC-7 contract violated: spa_booking.slot_id={spa_booking.slot_id!r} "
        f"expected {slot.id!r}"
    )
    assert spa_booking.payment_id == payment.id, (
        f"AC-7 contract violated: spa_booking.payment_id={spa_booking.payment_id!r} "
        f"expected {payment.id!r}"
    )
    assert spa_booking.folio_line.startswith(AC7_EXPECTED_FOLIO_LINE_PREFIX), (
        f"AC-7 contract violated: spa_booking.folio_line="
        f"{spa_booking.folio_line!r} does not start with "
        f"{AC7_EXPECTED_FOLIO_LINE_PREFIX!r}"
    )
    assert spa_booking.folio_line.endswith(AC7_EXPECTED_FOLIO_LINE_SUFFIX), (
        f"AC-7 contract violated: spa_booking.folio_line="
        f"{spa_booking.folio_line!r} does not end with "
        f"{AC7_EXPECTED_FOLIO_LINE_SUFFIX!r}"
    )
    assert spa_booking.folio_amount_eur == AC6_SAUNA_PRICE_EUR, (
        f"AC-7 contract violated: spa_booking.folio_amount_eur="
        f"{spa_booking.folio_amount_eur!r} expected {AC6_SAUNA_PRICE_EUR!r}"
    )
    assert spa_booking.folio_currency == AC7_EXPECTED_FOLIO_CURRENCY, (
        f"AC-7 contract violated: spa_booking.folio_currency="
        f"{spa_booking.folio_currency!r} expected {AC7_EXPECTED_FOLIO_CURRENCY!r}"
    )
    assert slot.bookings_count == 1, (
        f"AC-7 contract violated: slot.bookings_count={slot.bookings_count!r} "
        f"expected 1 (atomically incremented from 0 by SpaBooking.book)"
    )