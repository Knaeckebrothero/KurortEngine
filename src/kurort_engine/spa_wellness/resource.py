"""Resource entity for kurort_engine.spa_wellness (Sauna + Massage + Therme).

A Resource is a bookable capacity slot — Sauna (capacity-based, point-in-time)
or Massage (therapist-based, time-windowed). The Resource entity carries the
static configuration (type + capacity + therapist_id) and is consumed by the
Slot entity for instance-level state (bookings_count, is_bookable).

Reference tariffs live in :mod:`kurort_engine.spa_wellness.config`.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from kurort_engine.spa_wellness.config import (
    MASSAGE_FOLIO_PRICE_EUR,
    SAUNA_FOLIO_PRICE_EUR,
)

# Heilbad-standard reference tariffs per Hessischer Heilb\u00e4derverband (HHV)
# [413] Kurbeitragssatzung + \u00a723 SGB V ambulante Vorsorge reference.
# These are the v1 defaults; runtime overrides may apply via the property YAML
# config at `repo/tests/fixtures/spa_wellness_hotel_rheinland.yaml`.
_PRICE_TABLE: dict[str, Decimal] = {
    "sauna": SAUNA_FOLIO_PRICE_EUR,
    "massage": MASSAGE_FOLIO_PRICE_EUR,
}


@dataclass(frozen=True)
class Resource:
    """A bookable Spa/Wellness resource (Sauna × Massage room × Therme ticket type).

    Fields:
      - type: 'sauna' | 'massage' (the Kurort-vertical resource kinds)
      - capacity: integer default capacity (the maximum concurrent bookings)
      - therapist_id: optional therapist identifier (massage only)

    The `folio_price_eur` property derives from `_PRICE_TABLE[type]`.
    """

    type: str
    capacity: int = 1
    therapist_id: str | None = None

    def __post_init__(self) -> None:
        if self.type not in _PRICE_TABLE:
            raise ValueError(
                f"Resource type={self.type!r} is not supported. "
                f"Supported types: {sorted(_PRICE_TABLE.keys())}"
            )
        if self.capacity < 1:
            raise ValueError(
                f"Resource capacity={self.capacity} must be >= 1"
            )

    @property
    def folio_price_eur(self) -> Decimal:
        """The reference EUR price per booking for this Resource type.

        Sourced from `_PRICE_TABLE` (Heilbad-standard per HHV).
        """
        return _PRICE_TABLE[self.type]


__all__ = ["Resource"]
