"""SpaManager — the Kurort-vertical Spa/Wellness resource manager (full surface).

Holds the in-memory slot store and exposes:
  - create_slot(resource, date, time, *, capacity=None, duration_minutes=None)
  - list_slots(resource_type, date, min_available_capacity=1)
  - detect_conflicts(slots) [AC-4]
  - book_slot(slot, guest_id, payment_method) [AC-6/AC-7, implemented in G3]

The class is split across two files for the GREEN-phase delivery to keep each
file < 150 LOC. The ``__init__.py`` re-imports the public symbol and binds it
to ``SpaManager`` here for the full-featured facade.
"""
from __future__ import annotations

from kurort_engine.spa_wellness.resource import Resource
from kurort_engine.spa_wellness.slot import _DEFAULT_DURATION_MINUTES, Slot

# Resource-type id prefix for Slot.id (per the test_oracle contract).
_SLOT_ID_PREFIX: dict[str, str] = {
    "sauna": "sa",
    "massage": "ms",
}


def _time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' to minutes since midnight (used for AC-4 conflict sweep)."""
    hh, mm = time_str.split(":")
    return int(hh) * 60 + int(mm)


class SpaManager:
    """The Kurort-vertical Spa/Wellness resource manager."""

    def __init__(self) -> None:
        self._slots: list[Slot] = []

    def create_slot(
        self,
        resource: Resource,
        date: str,
        time: str,
        *,
        capacity: int | None = None,
        duration_minutes: int | None = None,
    ) -> Slot:
        prefix = _SLOT_ID_PREFIX.get(resource.type)
        if prefix is None:
            raise ValueError(
                f"Cannot create slot for unsupported resource type={resource.type!r}"
            )

        slot_id = f"{prefix}-{date}-T{time}"
        slot_capacity = capacity if capacity is not None else resource.capacity
        slot_duration = (
            duration_minutes
            if duration_minutes is not None
            else _DEFAULT_DURATION_MINUTES.get(resource.type, 0)
        )

        slot = Slot(
            id=slot_id,
            resource=resource,
            date=date,
            time=time,
            capacity=slot_capacity,
            bookings_count=0,
            duration_minutes=slot_duration,
            folio_price_eur=resource.folio_price_eur,
        )
        self._slots.append(slot)
        return slot

    def list_slots(
        self,
        resource_type: str,
        date: str,
        min_available_capacity: int = 1,
    ) -> tuple[Slot, ...]:
        result = []
        for slot in self._slots:
            if slot.resource.type != resource_type:
                continue
            if slot.date != date:
                continue
            if slot.remaining_capacity < min_available_capacity:
                continue
            result.append(slot)
        return tuple(result)

    def detect_conflicts(
        self,
        slots: tuple[Slot, ...],
    ) -> tuple[tuple[Slot, Slot], ...]:
        """Detect overlapping slot windows (AC-4).

        Algorithm (O(n log n)):
          (1) Group slots by (resource, date) so we only sweep within a
              single therapist / sauna cabin on a single day.
          (2) Deduplicate by `slot.id` within each group (slots with the same
              id are the same logical slot, NOT two conflicting bookings).
          (3) Sort by start time (minutes since midnight).
          (4) Sweep adjacent pairs. If slot_i.end_time > slot_{i+1}.start_time
              (overlap > 0 minutes), emit the pair. Touching back-to-back
              (end_time == start_time) is NOT a conflict.
          (5) Greedy left-to-right: each slot participates in at most one
              conflict pair.

        Empty input returns an empty tuple.
        """
        if not slots:
            return ()

        # (1) Group by (resource id, date).
        groups: dict[tuple[int, str], list[Slot]] = {}
        for slot in slots:
            key = (id(slot.resource), slot.date)
            groups.setdefault(key, []).append(slot)

        conflicts: list[tuple[Slot, Slot]] = []
        for group_slots in groups.values():
            # (2) Deduplicate by slot.id (keep first occurrence).
            seen_ids: set[str] = set()
            deduped: list[Slot] = []
            for slot in group_slots:
                if slot.id in seen_ids:
                    continue
                seen_ids.add(slot.id)
                deduped.append(slot)

            # (3) Sort by start time; tiebreak by id for determinism.
            sorted_slots = sorted(
                deduped,
                key=lambda s: (_time_to_minutes(s.time), s.id),
            )
            # (4) Sweep adjacent pairs; (5) greedy left-to-right pairing.
            used: set[int] = set()  # ids of slots already in a conflict pair
            for i in range(len(sorted_slots) - 1):
                a = sorted_slots[i]
                b = sorted_slots[i + 1]
                if id(a) in used or id(b) in used:
                    continue
                a_end = _time_to_minutes(a.time) + a.duration_minutes
                b_start = _time_to_minutes(b.time)
                if a_end > b_start:
                    conflicts.append((a, b))
                    used.add(id(a))
                    used.add(id(b))

        return tuple(conflicts)


__all__ = ["SpaManager"]
