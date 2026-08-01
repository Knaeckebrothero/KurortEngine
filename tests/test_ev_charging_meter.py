"""Q5.2 AC-2 — kurort_engine.ev_charging.meter module test surface (wallbox meter read).

AC-2 contract (verbatim from spec.yaml):

    Event-driven. When `read_session(wallbox_id, booking_id, start, stop)` is
    called THEN the function in `kurort_engine.ev_charging.meter` shall return
    a `MeterReading` dataclass with fields `wallbox_id: str`, `booking_id: str`,
    `start: datetime` (ISO 8601 UTC), `stop: datetime` (ISO 8601 UTC),
    `kwh: Decimal` (≥ 0, ≤ 100 per single charging session — E-Bike ~ 0.5 kWh,
    E-Auto ~ 30 kWh pilot envelope), `duration_minutes: int` (computed from
    stop - start, > 0); the function shall raise `ValueError` if `start >= stop`
    or `kwh < 0`.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check (wrapped in try/except) so
missing-module failures surface as ``AssertionError`` ("module should exist"),
not ``ModuleNotFoundError``.

Per `iter-24-pinned-tdd-rules-q5-2-e-bike-charging-scope-forbidden-patterns-loc-budget`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete dataclass field assertions for AC-2 MeterReading
  * Concrete ValueError assertions for AC-2 invalid-input cases
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from decimal import Decimal


def _find_spec_or_assert(module_name: str, *, parent: str | None = None) -> str:
    """Run ``importlib.util.find_spec`` and coerce missing-module failures
    into ``AssertionError`` so the test surfaces a "spec unmet" failure
    rather than a ``ModuleNotFoundError`` import failure.

    Per pinned memory: red-phase tests must fail with ``AssertionError``,
    not ``ImportError`` / ``ModuleNotFoundError`` / ``SyntaxError``.
    """
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError) as exc:
        scope = parent or module_name
        raise AssertionError(
            f"{scope} is not importable — green phase must create the "
            f"module before this test can pass. find_spec raised: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    assert found is not None, (
        f"{module_name} is not importable — green phase must create the "
        f"module before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _ev_charging_package_is_importable() -> str:
    """Pre-check: the new ev_charging package must exist."""
    return _find_spec_or_assert("kurort_engine.ev_charging")


def _meter_module_is_importable() -> str:
    """Pre-check: the new ev_charging.meter module must exist (AC-2)."""
    return _find_spec_or_assert(
        "kurort_engine.ev_charging.meter",
        parent="kurort_engine.ev_charging.meter",
    )


def _get_meter_module():
    """Import the ev_charging.meter module after the find_spec guard."""
    _meter_module_is_importable()
    import kurort_engine.ev_charging.meter as _mt  # noqa: E402
    assert _mt is not None, "importlib returned None — module is None"
    return _mt


# ===========================================================================
# AC-2 — read_session returns MeterReading dataclass with kwh + duration
# ===========================================================================

def test_ac2_read_session_returns_meter_reading_with_kwh_duration() -> None:
    """AC-2 spec test_oracle — happy-path E-Bike envelope.

    Calls ``read_session(wallbox_id, booking_id, start, stop)`` and asserts:
      * return type is a ``MeterReading`` dataclass
      * ``wallbox_id`` and ``booking_id`` round-trip
      * ``start`` and ``stop`` are ``datetime`` instances in UTC
      * ``kwh`` is a ``Decimal`` ≥ 0 (E-Bike ~ 0.5 kWh)
      * ``duration_minutes`` is an ``int`` > 0
    """
    _meter_module_is_importable()
    mt_mod = _get_meter_module()

    read_session = (
        getattr(mt_mod, "read_session", None)
        or getattr(mt_mod, "read", None)
    )
    assert callable(read_session), (
        "AC-2: meter must expose a callable read_session / read entry point; "
        f"found: {[n for n in dir(mt_mod) if not n.startswith('_')]!r}"
    )

    # MeterReading dataclass must exist.
    MeterReading = getattr(mt_mod, "MeterReading", None)
    assert MeterReading is not None and isinstance(MeterReading, type), (
        "AC-2: meter must export a MeterReading dataclass; "
        f"found: {[n for n in dir(mt_mod) if not n.startswith('_')]!r}"
    )

    # ---- E-Bike envelope: 0.5 kWh over 150 minutes ----
    wallbox_id = "WALLBOX-EBIKE-01"
    booking_id = "B-AC2-EBIKE-001"
    start = datetime(2026, 7, 5, 10, 0, 0, tzinfo=timezone.utc)
    stop = datetime(2026, 7, 5, 12, 30, 0, tzinfo=timezone.utc)  # +150 min

    reading = read_session(wallbox_id, booking_id, start, stop, kwh=Decimal("0.5"))

    # ----- return type -----
    assert isinstance(reading, MeterReading), (
        f"AC-2: read_session must return a MeterReading dataclass; "
        f"got {type(reading).__name__}: {reading!r}"
    )

    # ----- wallbox_id + booking_id round-trip -----
    assert reading.wallbox_id == wallbox_id, (
        f"AC-2: MeterReading.wallbox_id must round-trip; expected {wallbox_id!r}, "
        f"got {reading.wallbox_id!r}"
    )
    assert reading.booking_id == booking_id, (
        f"AC-2: MeterReading.booking_id must round-trip; expected {booking_id!r}, "
        f"got {reading.booking_id!r}"
    )

    # ----- start/stop = datetime (ISO 8601 UTC) -----
    assert isinstance(reading.start, datetime), (
        f"AC-2: MeterReading.start must be a datetime (ISO 8601 UTC); "
        f"got {type(reading.start).__name__}: {reading.start!r}"
    )
    assert isinstance(reading.stop, datetime), (
        f"AC-2: MeterReading.stop must be a datetime (ISO 8601 UTC); "
        f"got {type(reading.stop).__name__}: {reading.stop!r}"
    )
    assert reading.start.tzinfo is not None, (
        f"AC-2: MeterReading.start must be timezone-aware (ISO 8601 UTC); "
        f"got naive datetime: {reading.start!r}"
    )
    assert reading.stop.tzinfo is not None, (
        f"AC-2: MeterReading.stop must be timezone-aware (ISO 8601 UTC); "
        f"got naive datetime: {reading.stop!r}"
    )

    # ----- kwh: Decimal >= 0 (E-Bike envelope: 0.5) -----
    assert isinstance(reading.kwh, Decimal), (
        f"AC-2: MeterReading.kwh must be a Decimal; got {type(reading.kwh).__name__}: "
        f"{reading.kwh!r}"
    )
    assert reading.kwh >= Decimal("0"), (
        f"AC-2: MeterReading.kwh must be >= 0; got {reading.kwh!r}"
    )
    assert reading.kwh == Decimal("0.5"), (
        f"AC-2: MeterReading.kwh must equal the E-Bike envelope 0.5; "
        f"got {reading.kwh!r}"
    )

    # ----- duration_minutes: int > 0 (150 min for 10:00 → 12:30) -----
    assert isinstance(reading.duration_minutes, int), (
        f"AC-2: MeterReading.duration_minutes must be an int; got "
        f"{type(reading.duration_minutes).__name__}: {reading.duration_minutes!r}"
    )
    assert reading.duration_minutes > 0, (
        f"AC-2: MeterReading.duration_minutes must be > 0; got {reading.duration_minutes!r}"
    )
    assert reading.duration_minutes == 150, (
        f"AC-2: MeterReading.duration_minutes must equal 150 for 10:00 → 12:30; "
        f"got {reading.duration_minutes!r}"
    )


def test_ac2_read_session_returns_meter_reading_for_e_auto_envelope() -> None:
    """AC-2 secondary oracle — E-Auto envelope (30 kWh) for pilot.

    Same shape as the E-Bike test but using the E-Auto 30 kWh envelope
    specified in spec.yaml AC-2.
    """
    _meter_module_is_importable()
    mt_mod = _get_meter_module()

    read_session = (
        getattr(mt_mod, "read_session", None)
        or getattr(mt_mod, "read", None)
    )
    assert callable(read_session), (
        "AC-2: meter must expose a callable read_session / read entry point"
    )

    MeterReading = getattr(mt_mod, "MeterReading", None)
    assert MeterReading is not None and isinstance(MeterReading, type), (
        "AC-2: meter must export a MeterReading dataclass"
    )

    wallbox_id = "WALLBOX-EAUTO-01"
    booking_id = "B-AC2-EAUTO-001"
    start = datetime(2026, 7, 5, 8, 0, 0, tzinfo=timezone.utc)
    stop = datetime(2026, 7, 5, 14, 0, 0, tzinfo=timezone.utc)  # +360 min

    reading = read_session(wallbox_id, booking_id, start, stop, kwh=Decimal("30.0"))

    assert isinstance(reading, MeterReading), (
        f"AC-2: read_session must return a MeterReading; got {type(reading).__name__}"
    )
    assert reading.kwh == Decimal("30.0"), (
        f"AC-2: E-Auto envelope kwh must equal 30.0; got {reading.kwh!r}"
    )
    assert reading.duration_minutes == 360, (
        f"AC-2: E-Auto duration must equal 360 for 8h session; got {reading.duration_minutes!r}"
    )


# ===========================================================================
# AC-2 — read_session raises ValueError on invalid inputs
# ===========================================================================

def test_ac2_read_session_raises_value_error_on_invalid() -> None:
    """AC-2 spec test_oracle — ValueError surface.

    Asserts that ``read_session`` raises ``ValueError`` if:
      * ``start >= stop`` (zero-length or negative-duration session)
      * ``kwh < 0`` (physically impossible negative energy)
    """
    _meter_module_is_importable()
    mt_mod = _get_meter_module()

    read_session = (
        getattr(mt_mod, "read_session", None)
        or getattr(mt_mod, "read", None)
    )
    assert callable(read_session), (
        "AC-2: meter must expose a callable read_session / read entry point"
    )

    wallbox_id = "WALLBOX-EBIKE-01"
    booking_id = "B-AC2-INVALID-001"

    # ----- (a) start >= stop → ValueError -----
    # start == stop: zero-duration
    same_time = datetime(2026, 7, 5, 10, 0, 0, tzinfo=timezone.utc)
    try:
        read_session(wallbox_id, booking_id, same_time, same_time, kwh=Decimal("0.5"))
    except ValueError:
        pass  # expected
    else:
        raise AssertionError(
            "AC-2: read_session must raise ValueError when start == stop "
            "(zero-duration session); no exception raised"
        )

    # start > stop: negative-duration
    later_time = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
    earlier_time = datetime(2026, 7, 5, 10, 0, 0, tzinfo=timezone.utc)
    try:
        read_session(wallbox_id, booking_id, later_time, earlier_time, kwh=Decimal("0.5"))
    except ValueError:
        pass  # expected
    else:
        raise AssertionError(
            "AC-2: read_session must raise ValueError when start > stop "
            "(negative-duration session); no exception raised"
        )

    # ----- (b) kwh < 0 → ValueError -----
    valid_start = datetime(2026, 7, 5, 10, 0, 0, tzinfo=timezone.utc)
    valid_stop = datetime(2026, 7, 5, 12, 30, 0, tzinfo=timezone.utc)
    try:
        read_session(wallbox_id, booking_id, valid_start, valid_stop, kwh=Decimal("-0.5"))
    except ValueError:
        pass  # expected
    else:
        raise AssertionError(
            "AC-2: read_session must raise ValueError when kwh < 0 "
            "(physically impossible negative energy); no exception raised"
        )