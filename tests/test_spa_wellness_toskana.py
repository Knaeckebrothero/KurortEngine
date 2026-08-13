"""AC-5: Toskana Therme ticket sale via Kur-/Gästekarte (20% discount).

Test_oracle path recorded in spec.yaml:112 and spec_lock.md PROTECTED block.
This is the red-phase test for AC-5 that will fail with an AssertionError
against the placeholder (or absent) implementation. The
`kurort_engine.spa_wellness.toskana_therme` submodule does not yet exist;
`ToskanaThermeAdapter`, `ToskanaThermeTicket`, and `ToskanaThermeKurkarteError`
do not yet exist.

AC-5 contract (spec.yaml:102-112):
    Event-driven. When `ToskanaThermeAdapter.sell_ticket(*, kurkarte_id,
    visit_date, ticket_type='day_pass')` is invoked with a valid
    `kurkarte_id='k123'` and `visit_date='2026-12-20'`, the adapter shall
    return a `ToskanaThermeTicket` carrying
    `ticket.kurkarte_id == 'k123'`,
    `ticket.visit_date == '2026-12-20'`,
    `ticket.ticket_type == 'day_pass'`,
    `ticket.list_price_eur == Decimal('22.50')` (Toskanaworld 2026 day-pass),
    `ticket.guest_discount_applied == True` (20% per HHV [413]),
    `ticket.price_eur == Decimal('18.00')` (= 22.50 × 0.80), and
    `ticket.folio_line == 'Toskana Therme ticket — day_pass — 2026-12-20 —
    €18.00 (Gästekarte 20% discount applied)'`. If `kurkarte_id` is empty or
    `None`, the adapter shall raise `ToskanaThermeKurkarteError`.

RED VERIFY
----------
This test is expected to FAIL during the red phase. The failure mode MUST be
`AssertionError` (a failing assertion on the helper gate), NOT
`ImportError` / `ModuleNotFoundError`.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-5 contract constants (verbatim from spec.yaml PROTECTED block)
# ---------------------------------------------------------------------------

AC5_TEST_KURKARTE_ID: str = "k123"
AC5_TEST_VISIT_DATE: str = "2026-12-20"
AC5_DAY_PASS_LIST_PRICE_EUR: Decimal = Decimal("22.50")
AC5_GASTEKARTE_DISCOUNT_FACTOR: Decimal = Decimal("0.80")  # = 1 - 0.20 (20% off)
AC5_DAY_PASS_DISCOUNTED_EUR: Decimal = Decimal("18.00")  # = 22.50 * 0.80
AC5_EXPECTED_FOLIO_LINE: str = (
    "Toskana Therme ticket — day_pass — 2026-12-20 "
    "— €18.00 (Gästekarte 20% discount applied)"
)


def _load_toskana_or_assert():
    """Import `kurort_engine.spa_wellness.toskana_therme` and return the module.

    Raises `AssertionError` (NOT `ModuleNotFoundError`) when the submodule is
    absent — AC-5 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("kurort_engine.spa_wellness")
    assert spec is not None, (
        "AC-5 contract violated: kurort_engine.spa_wellness package not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the package."
    )
    spec2 = importlib.util.find_spec("kurort_engine.spa_wellness.toskana_therme")
    assert spec2 is not None, (
        "AC-5 contract violated: kurort_engine.spa_wellness.toskana_therme "
        "submodule not found in sys.path. The red phase expects this "
        "AssertionError (NOT ImportError) until the green phase implements "
        "the submodule under repo/src/kurort_engine/spa_wellness/toskana_therme.py."
    )
    module = importlib.import_module("kurort_engine.spa_wellness.toskana_therme")
    return module


def test_ac5_toskana_therme_ticket_sale_via_gaestekarte() -> None:
    """AC-5 master contract: ToskanaThermeAdapter sells day_pass with 20% discount.

    Verifies the full ticket-sale contract:
      1. The adapter sells a day_pass for kurkarte_id='k123' on visit_date='2026-12-20'
      2. Returns ToskanaThermeTicket with 7 fields per AC-5 spec
      3. folio_line is the verbatim string from the spec
      4. Calling sell_ticket with kurkarte_id=None raises ToskanaThermeKurkarteError
    """
    module = _load_toskana_or_assert()

    ToskanaThermeAdapter = getattr(module, "ToskanaThermeAdapter", None)
    ToskanaThermeKurkarteError = getattr(module, "ToskanaThermeKurkarteError", None)
    assert ToskanaThermeAdapter is not None, (
        "AC-5 contract violated: ToskanaThermeAdapter is missing from "
        "kurort_engine.spa_wellness.toskana_therme. Red phase expects this "
        "AssertionError until the green phase adds the adapter class."
    )
    assert ToskanaThermeKurkarteError is not None, (
        "AC-5 contract violated: ToskanaThermeKurkarteError is missing from "
        "kurort_engine.spa_wellness.toskana_therme. Red phase expects this "
        "AssertionError until the green phase adds the validation exception."
    )

    adapter = ToskanaThermeAdapter()
    ticket = adapter.sell_ticket(
        kurkarte_id=AC5_TEST_KURKARTE_ID,
        visit_date=AC5_TEST_VISIT_DATE,
    )

    # 7 fields per AC-5 contract
    assert ticket.kurkarte_id == AC5_TEST_KURKARTE_ID, (
        f"AC-5 contract violated: ticket.kurkarte_id={ticket.kurkarte_id!r} "
        f"expected {AC5_TEST_KURKARTE_ID!r}"
    )
    assert ticket.visit_date == AC5_TEST_VISIT_DATE, (
        f"AC-5 contract violated: ticket.visit_date={ticket.visit_date!r} "
        f"expected {AC5_TEST_VISIT_DATE!r}"
    )
    assert ticket.ticket_type == "day_pass", (
        f"AC-5 contract violated: ticket.ticket_type={ticket.ticket_type!r} "
        f"expected 'day_pass'"
    )
    assert ticket.list_price_eur == AC5_DAY_PASS_LIST_PRICE_EUR, (
        f"AC-5 contract violated: ticket.list_price_eur="
        f"{ticket.list_price_eur!r} expected {AC5_DAY_PASS_LIST_PRICE_EUR!r} "
        f"(Toskanaworld 2026 day-pass price)"
    )
    assert ticket.guest_discount_applied is True, (
        "AC-5 contract violated: ticket.guest_discount_applied is not True. "
        "A valid Kur-/Gästekarte must trigger the 20% HHV discount."
    )
    assert ticket.price_eur == AC5_DAY_PASS_DISCOUNTED_EUR, (
        f"AC-5 contract violated: ticket.price_eur={ticket.price_eur!r} "
        f"expected {AC5_DAY_PASS_DISCOUNTED_EUR!r} (= 22.50 × 0.80)"
    )
    assert ticket.folio_line == AC5_EXPECTED_FOLIO_LINE, (
        f"AC-5 contract violated: ticket.folio_line={ticket.folio_line!r} "
        f"expected the verbatim string from spec.yaml:\n{AC5_EXPECTED_FOLIO_LINE!r}"
    )

    # Validation gate per AC-5: kurkarte_id=None must raise ToskanaThermeKurkarteError
    import pytest
    with pytest.raises(ToskanaThermeKurkarteError) as excinfo:
        adapter.sell_ticket(
            kurkarte_id=None,
            visit_date=AC5_TEST_VISIT_DATE,
        )
    assert "kurkarte_id" in str(excinfo.value).lower(), (
        f"AC-5 contract violated: ToskanaThermeKurkarteError message="
        f"{str(excinfo.value)!r} expected to mention 'kurkarte_id'"
    )