"""AC-1 + AC-2: Sauna slot creation + Sauna slot listing filters.

Test_oracle paths recorded in spec.yaml:58,70 and spec_lock.md PROTECTED block.
This is the red-phase test for AC-1 + AC-2 that will fail with an AssertionError
against the placeholder (or absent) implementation. The
`kurort_engine.spa_wellness` package does not yet exist; `SpaManager`, `Resource`,
and `Slot` do not yet exist.

AC-1 contract (spec.yaml:42-58):
    Event-driven. When `SpaManager.create_slot(resource, date, time, *,
    capacity=None)` is invoked with a `Resource(type='sauna', capacity=N)`
    and a `Slot` is created for that resource on that date+time with the
    given capacity, the returned `Slot` shall carry
    `slot.resource == resource`,
    `slot.date == date`,
    `slot.time == time`,
    `slot.capacity == N` (or the resource's capacity if not given),
    `slot.bookings_count == 0`,
    `slot.folio_price_eur == Decimal('8.00')` (Heilbad-standard per HHV), and
    `slot.is_bookable == True` when `bookings_count < capacity`.

AC-2 contract (spec.yaml:60-70):
    Event-driven. When `SpaManager.list_slots(resource_type='sauna',
    date='YYYY-MM-DD', min_available_capacity=None)` is invoked, the manager
    shall return a `tuple[Slot, ...]` containing exactly the slots whose
    `Resource.type == 'sauna'`, whose `Slot.date == date`, and whose
    `remaining_capacity = capacity - bookings_count` is >= `min_available_capacity`
    (defaulting to 1 if not given). Slots whose `remaining_capacity == 0`
    and slots whose `Resource.type != 'sauna'` shall be excluded.

RED VERIFY
----------
These tests are expected to FAIL during the red phase. The failure mode MUST be
`AssertionError` (a failing assertion on the helper gate), NOT
`ImportError` / `ModuleNotFoundError` / `SyntaxError` / `CollectionError`.

We enforce the failure mode by:
  1. Using `importlib.util.find_spec` to pre-check the package exists BEFORE
     attempting the import. If the spec is missing, we raise `AssertionError`
     with a helpful message (NOT let `ModuleNotFoundError` propagate).
  2. Asserting concrete values on returned Slot objects (id, price, capacity,
     is_bookable, bookings_count) per the AC-1 contract.
  3. Asserting the list_slots filter behavior per the AC-2 contract.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-1 + AC-2 contract constants (verbatim from spec.yaml PROTECTED block)
# ---------------------------------------------------------------------------

AC1_SAUNA_FOLIO_PRICE_EUR: Decimal = Decimal("8.00")
AC1_SAUNA_CAPACITY: int = 6
AC1_TEST_DATE: str = "2026-12-20"
AC1_TEST_TIME: str = "16:00"
AC1_EXPECTED_SLOT_ID: str = "sa-2026-12-20-T16:00"

# Capacity-full fixture for AC-2 (capacity=2 with bookings_count=2 means
# remaining_capacity=0, which must be excluded from the filtered result).
AC2_FULL_CAPACITY: int = 2
AC2_FULL_BOOKINGS_COUNT: int = 2  # == AC2_FULL_CAPACITY => remaining_capacity == 0
AC2_FULL_TIME: str = "17:00"


def _load_spa_wellness_or_assert():
    """Import `kurort_engine.spa_wellness` and return the module.

    Raises `AssertionError` (NOT `ModuleNotFoundError`) when the package is
    absent — this is the AC-1 + AC-2 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("kurort_engine.spa_wellness")
    assert spec is not None, (
        "AC-1 + AC-2 contract violated: kurort_engine.spa_wellness package not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the package under "
        "repo/src/kurort_engine/spa_wellness/__init__.py."
    )
    module = importlib.import_module("kurort_engine.spa_wellness")
    return module


def test_ac1_sauna_slot_creation() -> None:
    """AC-1 master contract: SpaManager.create_slot returns a fully-formed Slot.

    Asserts:
      - slot.id == 'sa-2026-12-20-T16:00' (id format derived from resource-type
        prefix + date + time — 'sa' for sauna)
      - slot.folio_price_eur == Decimal('8.00') (Heilbad-standard per HHV)
      - slot.bookings_count == 0 (no bookings yet)
      - slot.is_bookable == True (capacity remains; bookings_count < capacity)
    """
    module = _load_spa_wellness_or_assert()

    SpaManager = getattr(module, "SpaManager", None)
    Resource = getattr(module, "Resource", None)
    assert SpaManager is not None, (
        "AC-1 contract violated: kurort_engine.spa_wellness.SpaManager is "
        "missing. Red phase expects this AssertionError until the green phase "
        "adds SpaManager to the package __init__.py."
    )
    assert Resource is not None, (
        "AC-1 contract violated: kurort_engine.spa_wellness.Resource is "
        "missing. Red phase expects this AssertionError until the green phase "
        "adds Resource to the package __init__.py."
    )

    manager = SpaManager()
    resource = Resource(type="sauna", capacity=AC1_SAUNA_CAPACITY)
    slot = manager.create_slot(
        resource=resource,
        date=AC1_TEST_DATE,
        time=AC1_TEST_TIME,
    )

    # Slot identity
    assert slot.id == AC1_EXPECTED_SLOT_ID, (
        f"AC-1 contract violated: slot.id={slot.id!r} expected "
        f"{AC1_EXPECTED_SLOT_ID!r} (format: <resource-prefix>-<date>-T<time>)"
    )

    # Slot carries the resource reference
    assert slot.resource == resource, (
        f"AC-1 contract violated: slot.resource={slot.resource!r} expected "
        f"the same Resource object passed to create_slot"
    )

    # Date / time / capacity carry-through
    assert slot.date == AC1_TEST_DATE, (
        f"AC-1 contract violated: slot.date={slot.date!r} expected "
        f"{AC1_TEST_DATE!r}"
    )
    assert slot.time == AC1_TEST_TIME, (
        f"AC-1 contract violated: slot.time={slot.time!r} expected "
        f"{AC1_TEST_TIME!r}"
    )
    assert slot.capacity == AC1_SAUNA_CAPACITY, (
        f"AC-1 contract violated: slot.capacity={slot.capacity!r} expected "
        f"{AC1_SAUNA_CAPACITY!r}"
    )

    # Bookings + price + is_bookable
    assert slot.bookings_count == 0, (
        f"AC-1 contract violated: slot.bookings_count={slot.bookings_count!r} "
        f"expected 0 (no bookings yet on a freshly created slot)"
    )
    assert slot.folio_price_eur == AC1_SAUNA_FOLIO_PRICE_EUR, (
        f"AC-1 contract violated: slot.folio_price_eur="
        f"{slot.folio_price_eur!r} expected {AC1_SAUNA_FOLIO_PRICE_EUR!r} "
        f"(Heilbad-standard Sauna entry per HHV Kurbeitragssatzung)"
    )
    assert slot.is_bookable is True, (
        "AC-1 contract violated: slot.is_bookable is not True when "
        "bookings_count < capacity"
    )


def test_ac2_sauna_slot_listing_filters_by_date_and_capacity() -> None:
    """AC-2 master contract: SpaManager.list_slots filters by resource_type + date + capacity.

    Test setup (per AC-2 contract):
      - Slot 1: Sauna at 2026-12-20 16:00 with capacity=6, bookings_count=0
                => remaining_capacity=6 >= 1  ⇒ MUST be in the result
      - Slot 2: Sauna at 2026-12-20 17:00 with capacity=2, bookings_count=2
                => remaining_capacity=0 < 1   ⇒ MUST NOT be in the result
      - Slot 3: Massage at 2026-12-20 18:00
                => resource.type != 'sauna'   ⇒ MUST NOT be in the result

    Asserts the returned tuple contains exactly 1 entry: Slot 1 (the Sauna
    slot at 16:00 with remaining_capacity >= 1).
    """
    module = _load_spa_wellness_or_assert()

    SpaManager = getattr(module, "SpaManager", None)
    Resource = getattr(module, "Resource", None)
    assert SpaManager is not None and Resource is not None, (
        "AC-2 contract violated: kurort_engine.spa_wellness.SpaManager or "
        "Resource is missing. Red phase expects this AssertionError."
    )

    manager = SpaManager()
    sauna_resource = Resource(type="sauna", capacity=AC1_SAUNA_CAPACITY)
    massage_resource = Resource(type="massage", therapist_id="t1")

    # Slot 1: Sauna at 16:00, capacity 6, bookings_count 0 — IN the result
    slot_sauna_16 = manager.create_slot(
        resource=sauna_resource, date=AC1_TEST_DATE, time="16:00"
    )
    assert slot_sauna_16.is_bookable is True  # AC-1 sanity

    # Slot 2: Sauna at 17:00, capacity 2, bookings_count 2 — EXCLUDED
    # (remaining_capacity = 2 - 2 = 0, fails the >= 1 filter)
    slot_sauna_17 = manager.create_slot(
        resource=sauna_resource,
        date=AC1_TEST_DATE,
        time=AC2_FULL_TIME,
        capacity=AC2_FULL_CAPACITY,
    )
    # Force bookings_count up to capacity to mimic a fully-booked slot
    # We mutate the bookings_count directly here ONLY for test fixture setup;
    # the production code path will increment via the manager's book_slot.
    object.__setattr__(slot_sauna_17, "bookings_count", AC2_FULL_BOOKINGS_COUNT)
    # Sanity: remaining_capacity should now be 0
    remaining_17 = slot_sauna_17.capacity - slot_sauna_17.bookings_count
    assert remaining_17 == 0, (
        f"Test fixture sanity failed: Sauna 17:00 remaining_capacity="
        f"{remaining_17} expected 0"
    )

    # Slot 3: Massage at 18:00 — EXCLUDED (resource.type != 'sauna')
    _slot_massage_18 = manager.create_slot(
        resource=massage_resource, date=AC1_TEST_DATE, time="18:00"
    )

    # Execute the AC-2 query
    result = manager.list_slots(
        resource_type="sauna",
        date=AC1_TEST_DATE,
        min_available_capacity=1,
    )

    # Must be a tuple
    assert isinstance(result, tuple), (
        f"AC-2 contract violated: list_slots returned {type(result).__name__} "
        f"expected tuple"
    )

    # Must contain exactly 1 entry (the 16:00 Sauna slot)
    assert len(result) == 1, (
        f"AC-2 contract violated: list_slots returned {len(result)} entries "
        f"expected 1 (the capacity-available Sauna slot at 16:00). The "
        f"capacity-full Sauna slot at 17:00 and the Massage slot at 18:00 "
        f"MUST be excluded."
    )

    # The single entry must be the 16:00 Sauna slot
    assert result[0].id == AC1_EXPECTED_SLOT_ID, (
        f"AC-2 contract violated: list_slots returned slot.id={result[0].id!r} "
        f"expected {AC1_EXPECTED_SLOT_ID!r} (the only capacity-available "
        f"Sauna slot on 2026-12-20)"
    )
    assert result[0].resource.type == "sauna", (
        "AC-2 contract violated: list_slots returned a non-Sauna slot"
    )
    assert result[0].date == AC1_TEST_DATE, (
        "AC-2 contract violated: list_slots returned a slot with the wrong date"
    )
    remaining = result[0].capacity - result[0].bookings_count
    assert remaining >= 1, (
        f"AC-2 contract violated: list_slots returned a slot with "
        f"remaining_capacity={remaining} (expected >= 1)"
    )