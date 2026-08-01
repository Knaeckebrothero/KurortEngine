"""AC-3 + AC-4: Massage appointment creation + Massage conflict detection.

Test_oracle paths recorded in spec.yaml:85,100 and spec_lock.md PROTECTED block.
This is the red-phase test for AC-3 + AC-4 that will fail with an AssertionError
against the placeholder (or absent) implementation. The
`kurort_engine.spa_wellness` package does not yet exist; `SpaManager.detect_conflicts`
does not yet exist.

AC-3 contract (spec.yaml:73-85):
    Event-driven. When `SpaManager.create_slot(resource, date, time, *,
    therapist_id=...)` is invoked with a `Resource(type='massage',
    therapist_id='t1')`, the returned `Slot` shall carry
    `slot.resource == resource`,
    `slot.therapist_id == 't1'`,
    `slot.date == date`,
    `slot.time == time`, and
    `slot.folio_price_eur == Decimal('35.00')` (Heilbad-standard per HHV).

AC-4 contract (spec.yaml:87-100):
    Unwanted-behavior. If `SpaManager.detect_conflicts(slots)` is invoked
    with a tuple of `Slot` objects, the manager shall return a
    `tuple[tuple[Slot, Slot], ...]` listing one entry per pair of slots that
    share the same `(resource_id, date)` AND whose `[start, end)` time
    windows overlap by any duration > 0 minutes; slots whose
    `therapist_id` differs and whose overlap is exactly 0 minutes (touching,
    e.g. 14:00..14:30 vs 14:30..15:00) shall NOT be flagged as a conflict.

RED VERIFY
----------
These tests are expected to FAIL during the red phase. The failure mode MUST be
`AssertionError` (a failing assertion on the helper gate), NOT
`ImportError` / `ModuleNotFoundError`.

We enforce the failure mode by:
  1. Using `importlib.util.find_spec` to pre-check the package exists BEFORE
     attempting the import.
  2. Asserting concrete values on returned Slot objects per the AC-3 contract.
  3. Asserting the conflict detection returns exactly 1 conflict entry for
     (s1, s2) only — not the touching pair, not the different-date pair.
"""
from __future__ import annotations

import importlib.util
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-3 + AC-4 contract constants (verbatim from spec.yaml PROTECTED block)
# ---------------------------------------------------------------------------

AC3_MASSAGE_FOLIO_PRICE_EUR: Decimal = Decimal("35.00")
AC3_TEST_THERAPIST_ID: str = "t1"
AC3_TEST_DATE: str = "2026-12-20"
AC3_TEST_TIME: str = "14:00"

# AC-4 overlapping (same therapist, overlapping windows)
AC4_MASSAGE_DURATION_MIN: int = 30  # Heilbad-standard 30-minute Massage per HHV
AC4_OVERLAP_S1_START: str = "14:00"  # 14:00..14:30
AC4_OVERLAP_S2_START: str = "14:15"  # 14:15..14:45 (overlaps s1 by 15 min)

# AC-4 touching (same therapist, back-to-back = NO conflict)
AC4_TOUCHING_S3_START: str = "14:00"  # 14:00..14:30
AC4_TOUCHING_S4_START: str = "14:30"  # 14:30..15:00 (touches s3, NO conflict)


def _load_spa_wellness_or_assert():
    """Import `kurort_engine.spa_wellness` and return the module.

    Raises `AssertionError` (NOT `ModuleNotFoundError`) when the package is
    absent — AC-3 + AC-4 red-phase RED VERIFY contract.
    """
    spec = importlib.util.find_spec("kurort_engine.spa_wellness")
    assert spec is not None, (
        "AC-3 + AC-4 contract violated: kurort_engine.spa_wellness package not "
        "found in sys.path. The red phase expects this AssertionError (NOT "
        "ImportError) until the green phase implements the package under "
        "repo/src/kurort_engine/spa_wellness/__init__.py."
    )
    module = importlib.import_module("kurort_engine.spa_wellness")
    return module


def test_ac3_massage_appointment_creation() -> None:
    """AC-3 master contract: SpaManager.create_slot carries Massage-specific fields.

    Asserts the returned Slot object has:
      - slot.resource == resource (Resource(type='massage', therapist_id='t1'))
      - slot.therapist_id == 't1'
      - slot.date == '2026-12-20'
      - slot.time == '14:00'
      - slot.folio_price_eur == Decimal('35.00') (Heilbad-standard per HHV)
      - slot.is_bookable == True (just created, no bookings yet)
    """
    module = _load_spa_wellness_or_assert()

    SpaManager = getattr(module, "SpaManager", None)
    Resource = getattr(module, "Resource", None)
    assert SpaManager is not None, (
        "AC-3 contract violated: kurort_engine.spa_wellness.SpaManager is missing. "
        "Red phase expects this AssertionError until the green phase adds "
        "SpaManager to the package __init__.py."
    )
    assert Resource is not None, (
        "AC-3 contract violated: kurort_engine.spa_wellness.Resource is missing. "
        "Red phase expects this AssertionError until the green phase adds "
        "Resource to the package __init__.py."
    )

    manager = SpaManager()
    resource = Resource(type="massage", therapist_id=AC3_TEST_THERAPIST_ID)

    slot = manager.create_slot(
        resource=resource,
        date=AC3_TEST_DATE,
        time=AC3_TEST_TIME,
    )

    # Resource reference is the SAME object passed to create_slot
    assert slot.resource == resource, (
        f"AC-3 contract violated: slot.resource={slot.resource!r} expected "
        f"the same Resource object passed to create_slot"
    )

    # Therapist ID carried through verbatim
    assert slot.therapist_id == AC3_TEST_THERAPIST_ID, (
        f"AC-3 contract violated: slot.therapist_id={slot.therapist_id!r} "
        f"expected {AC3_TEST_THERAPIST_ID!r}"
    )

    # Date / time carry-through
    assert slot.date == AC3_TEST_DATE, (
        f"AC-3 contract violated: slot.date={slot.date!r} expected "
        f"{AC3_TEST_DATE!r}"
    )
    assert slot.time == AC3_TEST_TIME, (
        f"AC-3 contract violated: slot.time={slot.time!r} expected "
        f"{AC3_TEST_TIME!r}"
    )

    # Price is the Heilbad-standard 30-minute Massage per HHV
    assert slot.folio_price_eur == AC3_MASSAGE_FOLIO_PRICE_EUR, (
        f"AC-3 contract violated: slot.folio_price_eur="
        f"{slot.folio_price_eur!r} expected {AC3_MASSAGE_FOLIO_PRICE_EUR!r} "
        f"(Heilbad-standard 30-minute Massage per HHV)"
    )

    # is_bookable True when capacity remains
    assert slot.is_bookable is True, (
        "AC-3 contract violated: slot.is_bookable is not True for a freshly "
        "created Massage slot (no bookings yet, capacity remains)"
    )


def test_ac4_massage_conflict_detection_flags_overlapping_slots() -> None:
    """AC-4 master contract: detect_conflicts flags overlap, ignores touching.

    Test setup (per AC-4 contract):
      - s1 (Massage t1) 14:00..14:30  — overlaps with s2 by 15 min ⇒ CONFLICT
      - s2 (Massage t1) 14:15..14:45  — overlaps with s1 by 15 min ⇒ CONFLICT
        ⇒ detect_conflicts must return tuple containing (s1, s2)
      - s3 (Massage t1) 14:00..14:30  — touches s4 at 14:30, no overlap
      - s4 (Massage t1) 14:30..15:00  — touches s3 at 14:30, no overlap
        ⇒ touching (back-to-back) = NOT a conflict, MUST be excluded

    Asserts:
      - result is a tuple
      - result contains exactly 1 conflict entry
      - that conflict entry is the (s1, s2) overlapping pair
      - the (s3, s4) touching pair is NOT in the result
    """
    module = _load_spa_wellness_or_assert()

    SpaManager = getattr(module, "SpaManager", None)
    Resource = getattr(module, "Resource", None)
    assert SpaManager is not None and Resource is not None, (
        "AC-4 contract violated: kurort_engine.spa_wellness.SpaManager or "
        "Resource is missing. Red phase expects this AssertionError."
    )

    manager = SpaManager()
    resource = Resource(type="massage", therapist_id=AC3_TEST_THERAPIST_ID)

    # AC-4 massage slots have explicit duration (30 min per HHV).
    # The Slot entity must carry this end-time window so detect_conflicts can
    # compute overlap. We assume create_slot() accepts a `duration_minutes`
    # keyword or similar parameter (the implementation will pin this in GREEN).
    s1 = manager.create_slot(
        resource=resource,
        date=AC3_TEST_DATE,
        time=AC4_OVERLAP_S1_START,
        duration_minutes=AC4_MASSAGE_DURATION_MIN,
    )
    s2 = manager.create_slot(
        resource=resource,
        date=AC3_TEST_DATE,
        time=AC4_OVERLAP_S2_START,
        duration_minutes=AC4_MASSAGE_DURATION_MIN,
    )
    s3 = manager.create_slot(
        resource=resource,
        date=AC3_TEST_DATE,
        time=AC4_TOUCHING_S3_START,
        duration_minutes=AC4_MASSAGE_DURATION_MIN,
    )
    s4 = manager.create_slot(
        resource=resource,
        date=AC3_TEST_DATE,
        time=AC4_TOUCHING_S4_START,
        duration_minutes=AC4_MASSAGE_DURATION_MIN,
    )

    detect_conflicts = getattr(manager, "detect_conflicts", None)
    assert detect_conflicts is not None, (
        "AC-4 contract violated: SpaManager.detect_conflicts is missing. "
        "Red phase expects this AssertionError until the green phase adds "
        "detect_conflicts to SpaManager."
    )

    result = detect_conflicts((s1, s2, s3, s4))

    # Must be a tuple
    assert isinstance(result, tuple), (
        f"AC-4 contract violated: detect_conflicts returned {type(result).__name__} "
        f"expected tuple"
    )

    # Exactly 1 conflict entry (the s1/s2 overlapping pair only — NOT s3/s4 touching)
    assert len(result) == 1, (
        f"AC-4 contract violated: detect_conflicts returned {len(result)} "
        f"conflict entries, expected exactly 1. The (s1, s2) overlapping pair "
        f"MUST be reported; the (s3, s4) back-to-back touching pair MUST NOT "
        f"be reported as a conflict."
    )

    # The 1 conflict entry must be the (s1, s2) pair (the overlapping one)
    conflict_pair = result[0]
    assert isinstance(conflict_pair, tuple) and len(conflict_pair) == 2, (
        f"AC-4 contract violated: each conflict entry must be a 2-tuple of Slot "
        f"objects; got {conflict_pair!r}"
    )
    conflict_ids = {conflict_pair[0].id, conflict_pair[1].id}
    expected_ids = {s1.id, s2.id}
    assert conflict_ids == expected_ids, (
        f"AC-4 contract violated: conflict entry ids={conflict_ids!r} "
        f"expected {expected_ids!r}. The overlapping pair (s1, s2) MUST be "
        f"reported as a conflict; the back-to-back (s3, s4) pair MUST NOT "
        f"be reported."
    )