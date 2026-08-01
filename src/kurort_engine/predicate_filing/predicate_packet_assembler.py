"""kurort_engine.predicate_filing.predicate_packet_assembler — AC-1.

Iter-33 Developer. Tier-2 chain-extension.

Provides ``assemble_predicate_packet(period_start, period_end,
kurgaste_records, kurtaxe_data, hcmi_scope1_2_data, spa_data,
ev_charging_data)`` which returns a structured JSON-serializable dict
describing the Bad Orb Heilbad 2036 Reprädikatisierung predicate-renewal
filing packet.

Per AC-1 (Ubiquitous): the function MUST emit a dict with top-level keys
``metadata`` (predicate_label + period + reprdikatisierung_window) +
``kurgaste_section`` + ``kurtaxe_section`` + ``esg_section`` +
``spa_section`` + ``mobility_section``.

The function MUST raise ``ValueError`` if ``period_start >= period_end`` OR
if ``(period_end.year - period_start.year) < 4`` (10-year Reprädikatisierung
cycle minimum, accepting 4-year transition windows).

The function MUST NOT modify any of the 6 SHIPPED modules it chains from
(esg.report + kurpaket_orchestrator + kurkarte_wallet + spa_wellness +
ev_charging + kurpaket_guest_card).
"""
from __future__ import annotations

from datetime import date
from typing import Any

# Constants — canonical Bad Orb Heilbad predicate label (AC-1 verbatim).
PREDICATE_LABEL: str = "Heilbad Bad Orb (Hessischer Heilbäderverband)"

# Forward-projected 2034-2044 Reprädikatisierung cycle window per ALEA PARK [1307]
# (AC-1 + AC-3 assumption A-2: current Heilbad designation 2024-2034, next
# cycle 2034-2044).
REPRÄDIKATISIERUNG_WINDOW: tuple[str, str] = ("2034-01-01", "2044-12-31")

# Minimum cycle length for predicate-renewal filing (10-year cycle minimum,
# accepting 4-year transition windows per AC-1 verbatim).
MIN_CYCLE_YEARS: int = 4


def assemble_predicate_packet(
    period_start: date,
    period_end: date,
    kurgaste_records: list[dict[str, Any]],
    kurtaxe_data: dict[str, Any],
    hcmi_scope1_2_data: dict[str, Any],
    spa_data: dict[str, Any],
    ev_charging_data: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the Bad Orb Heilbad 2036 predicate-renewal filing packet.

    Per AC-1: returns a JSON-serializable dict with 6 canonical sections +
    metadata envelope. Raises ``ValueError`` if ``period_start >= period_end``
    OR if the cycle is shorter than 4 years.
    """
    if period_start >= period_end:
        raise ValueError(
            f"period_start ({period_start.isoformat()}) must be strictly "
            f"before period_end ({period_end.isoformat()})"
        )

    cycle_years = period_end.year - period_start.year
    if cycle_years < MIN_CYCLE_YEARS:
        raise ValueError(
            f"predicate-renewal filing cycle ({cycle_years} years) is shorter "
            f"than the {MIN_CYCLE_YEARS}-year minimum (10-year "
            f"Reprädikatisierung cycle, accepting 4-year transition windows)"
        )

    return {
        "metadata": {
            "predicate_label": PREDICATE_LABEL,
            "period": (period_start.isoformat(), period_end.isoformat()),
            "reprdikatisierung_window": REPRÄDIKATISIERUNG_WINDOW,
        },
        "kurgaste_section": {
            "records_count": len(kurgaste_records),
            "records": list(kurgaste_records),
        },
        "kurtaxe_section": dict(kurtaxe_data),
        "esg_section": dict(hcmi_scope1_2_data),
        "spa_section": dict(spa_data),
        "mobility_section": dict(ev_charging_data),
    }