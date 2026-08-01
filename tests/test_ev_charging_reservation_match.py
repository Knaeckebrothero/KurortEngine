"""AC-4 — Kurkarte-tagged reservation match tests.

Iter-24 Phase 6 tactical RED. Q5.2 ev_charging submodule.

Spec contract (kurort_engine/spec.yaml AC-4):

    Event-driven. When ``match(booking_id, kurkarte_code, charging_session_id)``
    is called THEN the function in ``kurort_engine.ev_charging.reservation_match``
    shall return a ``ReservationMatch`` dataclass with fields:
      * ``booking_id: str``
      * ``kurkarte_code: str``
      * ``charging_session_id: str``
      * ``kurkarte_issued: bool`` — True iff
        ``kurort_engine.kurkarte_wallet.lookup_apple_pass(kurkarte_code)``
        returns non-None per SHIPPED iter-21 wallet
      * ``matched: bool`` — True iff kurkarte_issued AND the session_id is
        associated with a booking whose check-in ≤ today ≤ checkout window
        per SHIPPED ``kurort_engine.spa_wellness`` booking facade
      * ``matched_at: datetime`` — UTC of the match, populated only when
        ``matched=True``; otherwise NULL
    The function shall raise ``ValueError`` if ``booking_id`` or
    ``charging_session_id`` is empty string.

This is the RED-phase test_oracle: it verifies the spec contract via the
``ReservationMatch`` dataclass and ``match`` entry point of the SHIPPED (in
green phase) ``kurort_engine.ev_charging.reservation_match`` submodule.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers — find_spec guards (SHIPPED iter-21 pattern) so that the failure
# mode in RED is a clean AssertionError about the missing submodule.
# ---------------------------------------------------------------------------


def _reservation_match_module_is_importable() -> str:
    """Pre-check: ``kurort_engine.ev_charging.reservation_match`` must exist."""
    found = importlib.util.find_spec(
        "kurort_engine.ev_charging.reservation_match"
    )
    assert found is not None, (
        "kurort_engine.ev_charging.reservation_match is not importable — "
        "green phase must create "
        "repo/src/kurort_engine/ev_charging/reservation_match.py before this "
        f"test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _get_reservation_match_module():
    """Import the reservation_match module after the find_spec guard."""
    _reservation_match_module_is_importable()
    import kurort_engine.ev_charging.reservation_match as _rm  # noqa: E402
    assert _rm is not None, "importlib returned None — module is None"
    return _rm


def _get_kurkarte_wallet_module():
    """Import SHIPPED kurkarte_wallet (AC-1 SHIPPED iter-21).

    Used to verify that the SHIPPED ``lookup_apple_pass`` (added by green
    phase) returns non-None for a known SHIPPED booking code (B-AC1-001
    from iter-21 test fixtures).
    """
    spec = importlib.util.find_spec("kurort_engine.kurkarte_wallet")
    assert spec is not None, (
        "kurort_engine.kurkarte_wallet (AC-1..AC-4 SHIPPED iter-21) is not "
        "importable — Phase regressed. find_spec returned: "
        f"{spec!r}"
    )
    import kurort_engine.kurkarte_wallet as _kw  # noqa: E402
    return _kw


# ---------------------------------------------------------------------------
# AC-4 — match(kurkarte_code) against SHIPPED wallet + booking facade
# ---------------------------------------------------------------------------


def test_ac4_match_kurkarte_code_to_charging_session_within_window() -> None:
    """AC-4 spec test_oracle (PHASE 6 RED).

    Asserts three paths per spec.yaml AC-4:

      (a) ``ReservationMatch`` dataclass exists with all 6 spec fields.

      (b) KNOWN SHIPPED kurkarte_code (``'B-AC1-001'`` per iter-21
          ``tests/test_kurkarte_wallet_passkit.py`` SHIPPED fixture — a
          KurpaketGuestCard.booking_id used to render an Apple PKPass for
          that booking). The ``match`` function should return a
          ``ReservationMatch`` with ``kurkarte_issued=True`` because
          ``kurort_engine.kurkarte_wallet.lookup_apple_pass('B-AC1-001')``
          returns a non-None PKPass per SHIPPED iter-21 semantics.

      (c) UNKNOWN kurkarte_code returns ``ReservationMatch`` with
          ``kurkarte_issued=False``, ``matched=False``, ``matched_at=None``
          (because ``matched=True`` requires kurkarte_issued AND the session
          is within check-in/checkout window per SHIPPED spa_wellness facade).

      (d) ``match`` raises ``ValueError`` if ``booking_id`` is empty string
          OR ``charging_session_id`` is empty string (per spec).
    """
    # ---- import the modules under test -----------------------------------
    rm_mod = _get_reservation_match_module()
    _get_kurkarte_wallet_module()  # SHIPPED dependency must exist

    # ReservationMatch dataclass (AC-4 spec) is exported
    ReservationMatch = getattr(rm_mod, "ReservationMatch", None)
    assert ReservationMatch is not None, (
        "kurort_engine.ev_charging.reservation_match must export a "
        "ReservationMatch dataclass per AC-4 spec"
    )

    # match() entry point (AC-4 spec)
    match = getattr(rm_mod, "match", None)
    assert callable(match), (
        "kurort_engine.ev_charging.reservation_match must expose a callable "
        "match entry point per AC-4 spec; got "
        f"{[n for n in dir(rm_mod) if not n.startswith('_')]!r}"
    )

    # (a) dataclass has all 6 spec fields
    required_fields = {
        "booking_id",
        "kurkarte_code",
        "charging_session_id",
        "kurkarte_issued",
        "matched",
        "matched_at",
    }
    # Inspect dataclass fields — use __dataclass_fields__ if available,
    # otherwise fall back to hasattr.
    dataclass_fields = getattr(ReservationMatch, "__dataclass_fields__", None)
    if isinstance(dataclass_fields, dict):
        present = set(dataclass_fields.keys())
    else:
        present = {n for n in required_fields if hasattr(ReservationMatch, n)}
    missing = required_fields - present
    assert not missing, (
        f"ReservationMatch must have all 6 AC-4 spec fields {required_fields!r}; "
        f"missing={missing!r}; present={present!r}"
    )

    # (b) KNOWN SHIPPED kurkarte_code → kurkarte_issued=True
    # The SHIPPED iter-21 Apple PKPass test uses 'B-AC1-001' as the canonical
    # booking/kurkarte_code; once the green phase adds
    # ``kurort_engine.kurkarte_wallet.lookup_apple_pass(kurkarte_code)``
    # returning the rendered PKPass dict for this code, our match() must
    # surface ``kurkarte_issued=True``.
    booked_result = match(
        booking_id="B-AC4-001",
        kurkarte_code="B-AC1-001",  # SHIPPED iter-21 fixture booking_id
        charging_session_id="CS-AC4-001",
    )
    assert isinstance(booked_result, ReservationMatch), (
        f"match() must return a ReservationMatch dataclass; got "
        f"{type(booked_result).__module__}.{type(booked_result).__name__}"
    )
    assert booked_result.booking_id == "B-AC4-001", (
        f"ReservationMatch.booking_id must equal input booking_id; got "
        f"{booked_result.booking_id!r}"
    )
    assert booked_result.kurkarte_code == "B-AC1-001", (
        f"ReservationMatch.kurkarte_code must equal input kurkarte_code; got "
        f"{booked_result.kurkarte_code!r}"
    )
    assert booked_result.charging_session_id == "CS-AC4-001", (
        f"ReservationMatch.charging_session_id must equal input session_id; got "
        f"{booked_result.charging_session_id!r}"
    )
    # kurkarte_issued must be bool, True for the SHIPPED Apple-pass-bearing
    # code; the green implementation must wire up ``lookup_apple_pass`` so
    # that 'B-AC1-001' returns non-None.
    assert booked_result.kurkarte_issued is True, (
        "ReservationMatch.kurkarte_issued must be True for the SHIPPED "
        "iter-21 Apple-pass kurkarte_code 'B-AC1-001' — green phase must "
        "implement kurort_engine.kurkarte_wallet.lookup_apple_pass(kurkarte_code) "
        f"returning non-None for SHIPPED codes. got {booked_result.kurkarte_issued!r}"
    )
    # matched: True iff kurkarte_issued AND session within check-in/checkout
    # window. We don't assert True here because the window check requires a
    # SHIPPED booking facade session — but ``matched`` MUST be a bool.
    assert isinstance(booked_result.matched, bool), (
        f"ReservationMatch.matched must be bool; got "
        f"{type(booked_result.matched).__name__}"
    )
    # matched_at: UTC datetime iff matched=True, else None
    if booked_result.matched:
        assert isinstance(booked_result.matched_at, datetime), (
            f"ReservationMatch.matched_at must be datetime when matched=True; "
            f"got {type(booked_result.matched_at).__name__}"
        )
    else:
        assert booked_result.matched_at is None, (
            f"ReservationMatch.matched_at must be None when matched=False; "
            f"got {booked_result.matched_at!r}"
        )

    # (c) UNKNOWN kurkarte_code → kurkarte_issued=False, matched=False,
    # matched_at=None
    unknown_result = match(
        booking_id="B-AC4-002",
        kurkarte_code="NEVER-ISSUED-BAD-CODE-9999",
        charging_session_id="CS-AC4-002",
    )
    assert isinstance(unknown_result, ReservationMatch), (
        f"match() must return a ReservationMatch dataclass for unknown "
        f"kurkarte_code; got {type(unknown_result).__module__}.{type(unknown_result).__name__}"
    )
    assert unknown_result.kurkarte_issued is False, (
        "ReservationMatch.kurkarte_issued must be False for an unknown / "
        f"never-issued kurkarte_code. got {unknown_result.kurkarte_issued!r}"
    )
    assert unknown_result.matched is False, (
        "ReservationMatch.matched must be False when kurkarte_issued=False "
        "per AC-4 spec (True iff kurkarte_issued AND within window). got "
        f"{unknown_result.matched!r}"
    )
    assert unknown_result.matched_at is None, (
        "ReservationMatch.matched_at must be None when matched=False per "
        f"AC-4 spec. got {unknown_result.matched_at!r}"
    )

    # (d) ValueError on empty booking_id or empty charging_session_id
    try:
        match(
            booking_id="",
            kurkarte_code="B-AC1-001",
            charging_session_id="CS-AC4-003",
        )
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"match() must raise ValueError on empty booking_id; got "
            f"{type(exc).__name__}: {exc}"
        )
    else:
        raise AssertionError(
            "match() must raise ValueError on empty booking_id, but returned normally"
        )

    try:
        match(
            booking_id="B-AC4-004",
            kurkarte_code="B-AC1-001",
            charging_session_id="",
        )
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"match() must raise ValueError on empty charging_session_id; got "
            f"{type(exc).__name__}: {exc}"
        )
    else:
        raise AssertionError(
            "match() must raise ValueError on empty charging_session_id, "
            "but returned normally"
        )
