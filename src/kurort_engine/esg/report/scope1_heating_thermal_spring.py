"""kurort_engine.esg.report.scope1_heating_thermal_spring — Scope 1 thermal-spring NiedrigEnergie baseline (companion stub).

Computes the Scope 1 (direct) emissions for Hotel Rheinland Bad Orb heating
via the Toskana Therme partnership thermal-spring NiedrigEnergie baseline.
Used by AC-3 Gastgeber-Klimaneutralität 2030 alignment (consumes the Scope 1
sub-total as one input) and AC-4 Kurort-vertical narrative generator
(anchors the thermal-spring NiedrigEnergie baseline mention).

Iteration 27 (Developer) Q5.1 Tier-2 ESG-CSRD Voluntary VSME + HCMI Scope 3 —
companion stub (per iter-25-proposal-002 §7; ~50 LOC budget; needed by
Group 2 AC-3 + AC-4 even though not directly asserted in AC-1+AC-2).

Toskana Therme partnership anchor
---------------------------------
Per Hotel Rheinland Bad Orb operations, the Toskana Therme partnership
delivers thermal-spring NiedrigEnergie water for hotel heating at a 2025/2026
baseline emission factor of ``0.05 kg CO2e/kWh`` (vs the DE Strommix
factor of 0.42 kg CO2e/kWh used in AC-2) — an 88 % Scope 1 reduction.
This module exposes that anchor as a separate, testable calc.

Decimal arithmetic
------------------
All numeric values use :class:`decimal.Decimal` string-form (NO float drift).
"""
from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Module-level constants — Toskana Therme NiedrigEnergie baseline
# ---------------------------------------------------------------------------

#: Scope 1 thermal-spring NiedrigEnergie emission factor (0.05 kg CO2e per kWh).
#: 88 % reduction vs DE Strommix (0.42 kg CO2e/kWh used in AC-2 heating).
_TOSKANA_THERMAL_SPRING_KG_CO2E_PER_KWH: Decimal = Decimal("0.05")

#: DE Strommix scope-1 heating baseline (0.42 kg CO2e per kWh) — used to
#: compute the "baseline vs NiedrigEnergie" delta for Gastgeber-Klimaneutralität
#: 2030 alignment reporting.
_DE_STROMMIX_HEATING_KG_CO2E_PER_KWH: Decimal = Decimal("0.42")


# ---------------------------------------------------------------------------
# Companion stub — scope1_heating_thermal_spring_emissions
# ---------------------------------------------------------------------------

def scope1_heating_thermal_spring_emissions(heating_kwh_annual: Decimal) -> dict:
    """Compute Scope 1 heating emissions using the Toskana thermal-spring baseline.

    Args:
        heating_kwh_annual: Annual heating electricity consumption in kWh
            (Decimal, ≥ 0).

    Returns:
        JSON-serialisable ``dict`` carrying the 2 required keys:

        * ``scope1_tco2e: Decimal`` — Scope 1 emissions (kg CO2e) using the
          Toskana thermal-spring NiedrigEnergie factor (0.05 kg CO2e/kWh).
        * ``thermal_spring_baseline_tco2e: Decimal`` — baseline emissions
          (kg CO2e) if the same heating had been sourced from DE Strommix
          (0.42 kg CO2e/kWh). Used by AC-3 to compute the
          ``aligned: bool`` flag (alignment iff scope1 ≤ baseline × trajectory).

    Raises:
        ValueError: If ``heating_kwh_annual`` is negative.
    """
    if heating_kwh_annual < Decimal("0"):
        raise ValueError(
            f"scope1_heating_thermal_spring_emissions requires "
            f"heating_kwh_annual >= 0; got {heating_kwh_annual!r} "
            f"(negative heating consumption is invalid)"
        )

    heating_kwh = Decimal(str(heating_kwh_annual))
    scope1_tco2e = heating_kwh * _TOSKANA_THERMAL_SPRING_KG_CO2E_PER_KWH
    thermal_spring_baseline_tco2e = heating_kwh * _DE_STROMMIX_HEATING_KG_CO2E_PER_KWH

    return {
        "scope1_tco2e": scope1_tco2e,
        "thermal_spring_baseline_tco2e": thermal_spring_baseline_tco2e,
    }


# ---------------------------------------------------------------------------
# Module public API
# ---------------------------------------------------------------------------

__all__ = [
    "scope1_heating_thermal_spring_emissions",
]
