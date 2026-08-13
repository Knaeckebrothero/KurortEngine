"""Slot entity for kurort_engine.spa_wellness (a single bookable time window).

A Slot represents one bookable instance of a Resource at a specific date+time.
For Sauna (capacity-based, point-in-time), the slot's `duration_minutes`
defaults to 0 (capacity is the only constraint). For Massage (therapist-based,
time-windowed), `duration_minutes` defaults to 30 (HHV ambulante Vorsorge) and
the slot participates in conflict detection (AC-4).

Slot IDs follow the convention <resource-prefix>-<date>-T<time>:
  - 'sa' for sauna (sa-2026-12-20-T16:00)
  - 'ms' for massage (ms-2026-12-20-T14:00)

Default duration constants live in :mod:`kurort_engine.spa_wellness.config`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from kurort_engine.spa_wellness.config import (
    MASSAGE_DEFAULT_DURATION_MINUTES,
    SAUNA_DEFAULT_DURATION_MINUTES,
)

if TYPE_CHECKING:
    from kurort_engine.spa_wellness.resource import Resource


# Default duration_minutes per Resource type (the HHV-standard reference).
_DEFAULT_DURATION_MINUTES: dict[str, int] = {
    "sauna": SAUNA_DEFAULT_DURATION_MINUTES,
    "massage": MASSAGE_DEFAULT_DURATION_MINUTES,
}


@dataclass(frozen=True)
class Slot:
    id: str
    resource: Resource
    date: str
    time: str
    capacity: int
    bookings_count: int = 0
    duration_minutes: int = 0
    folio_price_eur: Decimal = field(default=Decimal("0.00"))

    @property
    def therapist_id(self) -> str | None:
        return self.resource.therapist_id

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - self.bookings_count

    @property
    def is_bookable(self) -> bool:
        return self.bookings_count < self.capacity

    @property
    def end_time(self) -> str:
        hh, mm = self.time.split(":")
        start_minutes = int(hh) * 60 + int(mm)
        end_minutes = start_minutes + self.duration_minutes
        end_hh = (end_minutes // 60) % 24
        end_mm = end_minutes % 60
        return f"{end_hh:02d}:{end_mm:02d}"


__all__ = ["Slot", "_DEFAULT_DURATION_MINUTES"]
