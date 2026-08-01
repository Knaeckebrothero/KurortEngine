"""MinLOS validator (AC-5).

Implements :class:`MinLosValidator` which inspects a set of existing
``kurort_engine.Reservation`` objects against a :class:`MinLosProfile` and
returns a :class:`MinLosValidationReport` flagging every (reservation, rule)
pair where:

    - the reservation's stay overlaps the rule's ``date_range`` (any date in
      ``[arrival, departure)`` falls within the rule's window), AND
    - the reservation's ``length_of_stay = (departure - arrival).days`` is
      strictly LESS than the rule's ``minlos``.

The validator reuses the same ``(departure - arrival).days`` formula that
``kurort_engine.calculator`` uses for the Kurtaxe day-count, ensuring
parity between the MinLOS validator and the existing rate engine
(spec.yaml:131-141 mandates this consistency).

The validator does NOT mutate state, write to stdout, or open files
(parity with the ``kurort_engine`` package AC-6 contract).
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
from typing import Any


def _parse_iso_date(s: str) -> _dt.date:
    """Parse an ISO-8601 ``YYYY-MM-DD`` date string into a :class:`date`.

    Mirrors the convention used by ``profile_loader``: the profile stores
    ``date_range`` as ISO strings (NOT ``date`` objects) so YAML parsing
    produces strings; the validator coerces to ``date`` for range overlap
    math.
    """
    return _dt.date.fromisoformat(s)


def _length_of_stay(arrival: _dt.date, departure: _dt.date) -> int:
    """Return ``(departure - arrival).days`` (parity with kurort_engine.calculator).

    Spec.yaml:131-141 mandates that the validator use the same day-count
    formula as the Kurtaxe calculator.
    """
    return (departure - arrival).days


def _ranges_overlap(
    res_arrival: _dt.date,
    res_departure: _dt.date,
    rule_start: _dt.date,
    rule_end: _dt.date,
) -> bool:
    """Return True iff any date in ``[res_arrival, res_departure)`` is in
    ``[rule_start, rule_end]``.

    The reservation span is half-open (departure day is not counted as a
    stay night) per the standard hotel-night convention. The rule span is
    also half-open (the ``rule_end`` is the LAST day the rule applies, not
    the first day it doesn't apply), so an inclusive overlap test works.
    """
    # Half-open on the reservation side; inclusive on the rule side.
    # Overlap iff: res_arrival <= rule_end AND rule_start < res_departure
    return res_arrival <= rule_end and rule_start < res_departure


@dataclasses.dataclass(frozen=True)
class MinLosValidationReport:
    """Immutable validator result (AC-5 contract).

    Attributes:
        violations: Tuple of ``(reservation, rule)`` pairs where the
            reservation's length-of-stay is below the matching rule's
            ``minlos``. Ordered by ``(reservation.reservation_id, rule.name)``
            for deterministic output (facilitates test assertions).
        conflicts: Tuple of conflicting rule pairs (currently always empty
            per the AC-5 contract: spec.yaml:131-141 says conflicts is empty
            when no reservations violate; the field is reserved for future
            extension).
    """

    violations: tuple[tuple[Any, Any], ...]
    conflicts: tuple[Any, ...] = ()


class MinLosValidator:
    """Validates existing reservations against a MinLOS profile (AC-5)."""

    def __init__(self) -> None:
        """Initialize the validator (stateless)."""
        pass

    def validate(
        self,
        profile: Any,
        existing_reservations: list[Any],
    ) -> MinLosValidationReport:
        """Validate ``existing_reservations`` against ``profile``.

        Args:
            profile: A :class:`~channel_manager_minstay.MinLosProfile` whose
                ``rules`` tuple carries ``MinLosRule`` entries with
                ``date_range: ("YYYY-MM-DD", "YYYY-MM-DD")`` strings +
                ``minlos: int`` + ``name: str``.
            existing_reservations: List of
                ``kurort_engine.calculator.Reservation`` objects (or
                duck-typed equivalents with ``arrival: date``,
                ``departure: date``, ``reservation_id: str``).

        Returns:
            A :class:`MinLosValidationReport` carrying ``violations`` (the
            list of (reservation, rule) pairs where length-of-stay <
            minlos for an overlapping rule) and ``conflicts`` (currently
            always empty per the AC-5 contract).
        """
        violations: list[tuple[Any, Any]] = []

        for reservation in existing_reservations:
            res_arrival = reservation.arrival
            res_departure = reservation.departure
            res_los = _length_of_stay(res_arrival, res_departure)

            for rule in profile.rules:
                rule_start = _parse_iso_date(rule.date_range[0])
                # The rule's end-date is interpreted as the LAST day the rule
                # applies. For the overlap test we use the day AFTER the rule
                # end (i.e. rule_end_exclusive = rule_end + 1 day) so that a
                # reservation arriving on the rule-end day still overlaps.
                rule_end = _parse_iso_date(rule.date_range[1])

                if not _ranges_overlap(
                    res_arrival,
                    res_departure,
                    rule_start,
                    rule_end,
                ):
                    continue

                if res_los < rule.minlos:
                    violations.append((reservation, rule))

        # Sort for deterministic output (helps test assertions + audit-trail
        # hash stability).
        violations.sort(
            key=lambda pair: (
                getattr(pair[0], "reservation_id", str(pair[0])),
                getattr(pair[1], "name", str(pair[1])),
            )
        )

        return MinLosValidationReport(
            violations=tuple(violations),
            conflicts=(),
        )
