"""kurort_engine.ev_charging.meter — wallbox meter read (AC-2).

Reads a wallbox charging session into a :class:`MeterReading` dataclass
with kWh + session_id + start/stop timestamps. Iteration 24 (Developer)
Q5.2 Tier-2 ev_charging — implements AC-2 (Event-driven).

Envelope (single-pilot)
-----------------------

* 1× E-Bike (Garage) ~ 0.5 kWh per session
* 1× E-Auto (Tiefgarage) ~ 30 kWh per session

``kwh`` uses :class:`decimal.Decimal` (NOT float) to keep folio-line-item
arithmetic aligned with the Kurort-Engine ``Decimal`` policy (no
floating-point rounding errors on `net_eur`, `ust_eur`, `gross_eur` in
the AC-3 invoice line item builder).

Validation
----------

``read_session`` raises :class:`ValueError` if:

* ``start >= stop`` (zero-length or negative-duration session)
* ``kwh < 0`` (physically impossible negative energy)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

# ---------------------------------------------------------------------------
# AC-2 — MeterReading dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MeterReading:
    """Immutable wallbox meter read for a single charging session.

    Attributes:
        wallbox_id: Wallbox identifier (e.g. ``WALLBOX-EBIKE-01``).
        booking_id: Hotel booking ID this session is associated with.
        start: Session start as timezone-aware ``datetime`` (ISO 8601 UTC).
        stop: Session stop as timezone-aware ``datetime`` (ISO 8601 UTC).
        kwh: Energy delivered in kWh (Decimal, ≥ 0, ≤ 100 per single session).
        duration_minutes: Computed ``int`` floor of ``(stop - start) / 60``.
    """

    wallbox_id: str
    booking_id: str
    start: datetime
    stop: datetime
    kwh: Decimal
    duration_minutes: int


# ---------------------------------------------------------------------------
# AC-2 — read_session
# ---------------------------------------------------------------------------

def read_session(
    wallbox_id: str,
    booking_id: str,
    start: datetime,
    stop: datetime,
    kwh: Decimal,
) -> MeterReading:
    """Read a wallbox charging session into a :class:`MeterReading`.

    Args:
        wallbox_id: Wallbox identifier.
        booking_id: Hotel booking ID this session is associated with.
        start: Session start as timezone-aware ``datetime``.
        stop: Session stop as timezone-aware ``datetime``.
        kwh: Energy delivered in kWh (Decimal, ≥ 0).

    Returns:
        Frozen :class:`MeterReading` with computed ``duration_minutes``.

    Raises:
        ValueError: If ``start >= stop`` or ``kwh < 0``.
    """
    if start >= stop:
        raise ValueError(
            f"MeterReading requires start < stop; got start={start!r}, "
            f"stop={stop!r} (start >= stop)"
        )
    if kwh < Decimal("0"):
        raise ValueError(
            f"MeterReading.kwh must be >= 0; got kwh={kwh!r} (negative energy)"
        )

    duration_minutes = int((stop - start).total_seconds() // 60)

    return MeterReading(
        wallbox_id=wallbox_id,
        booking_id=booking_id,
        start=start,
        stop=stop,
        kwh=kwh,
        duration_minutes=duration_minutes,
    )