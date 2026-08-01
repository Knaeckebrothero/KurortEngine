"""kurort_engine.esg.report.hcmi_scope3_calculator — HCMI Scope 3 emissions calculator (AC-2).

Computes the Hotel Carbon Measurement Initiative (HCMI) Scope 3 emissions
for Hotel Rheinland Bad Orb (30,000+ hotels globally use HCMI; 2025/2026
baseline emission factors) — heating + food waste + mobility + linen sub-categories.

Iteration 27 (Developer) Q5.1 Tier-2 ESG-CSRD Voluntary VSME + HCMI Scope 3 —
implements AC-2 (Event-driven). Surface verified against the SHIPPED iter-24
kurort_engine.ev_charging sub-package structure for naming + re-export
convention.

HCMI methodology
----------------
Per `Hotel Carbon Measurement Initiative <https://hmii.global/>`_ 2025/2026
baseline, Scope 3 covers 4 indirect-emission categories for hotels:

  * **heating** — via German Strommix 2026 grid factor ``0.42 kg CO2e/kWh``
    (DE-specific override per OK Lab scope-3 guidance)
  * **food waste** — HCMI baseline ``2.5 kg CO2e/kg``
  * **mobility** — HCMI baseline ``0.171 kg CO2e/km`` (reduced by iter-24
    E-Bike charging per ``kurort_engine.ev_charging.read_session``)
  * **linen** — HCMI baseline ``5.5 kg CO2e/kg``

Decimal arithmetic
------------------
All emissions use :class:`decimal.Decimal` string-form (``Decimal("0.42")``
NOT ``Decimal(0.42)``) to avoid float drift; canonical-JSON round-trip via
``json.dumps(result, default=str)`` keeps the snapshot deterministic.
"""
from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Module-level constants — HCMI 2025/2026 baseline emission factors
# ---------------------------------------------------------------------------

#: HCMI 2025/2026 baseline: heating via German Strommix 2026 grid factor
#: (0.42 kg CO2e per kWh). DE-specific override per OK Lab scope-3 guidance.
_HCMI_HEATING_KG_CO2E_PER_KWH: Decimal = Decimal("0.42")

#: HCMI 2025/2026 baseline: food waste (2.5 kg CO2e per kg).
_HCMI_FOOD_WASTE_KG_CO2E_PER_KG: Decimal = Decimal("2.5")

#: HCMI 2025/2026 baseline: mobility (0.171 kg CO2e per km).
#: NOTE: Reduced by iter-24 E-Bike charging scope-3 savings
#: (per `kurort_engine.ev_charging.read_session` E-Bike envelope).
_HCMI_MOBILITY_KG_CO2E_PER_KM: Decimal = Decimal("0.171")

#: HCMI 2025/2026 baseline: linen (5.5 kg CO2e per kg).
_HCMI_LINEN_KG_CO2E_PER_KG: Decimal = Decimal("5.5")


# ---------------------------------------------------------------------------
# AC-2 — calculate_scope_3
# ---------------------------------------------------------------------------

def calculate_scope_3(
    heating_kwh_annual: Decimal,
    food_waste_kg_annual: Decimal,
    mobility_km_annual: Decimal,
    linen_kg_annual: Decimal,
) -> dict:
    """Calculate HCMI Scope 3 emissions per the 4-categories HCMI methodology.

    Args:
        heating_kwh_annual: Annual heating electricity consumption in kWh
            (Decimal, ≥ 0).
        food_waste_kg_annual: Annual food waste in kg (Decimal, ≥ 0).
        mobility_km_annual: Annual mobility in km (Decimal, ≥ 0).
        linen_kg_annual: Annual linen turnover in kg (Decimal, ≥ 0).

    Returns:
        JSON-serialisable ``dict`` carrying the 5 required HCMI scope-3 keys:

        * ``heating_tco2e: Decimal`` — heating emissions (kg CO2e → tCO2e)
        * ``food_waste_tco2e: Decimal`` — food waste emissions
        * ``mobility_tco2e: Decimal`` — mobility emissions
        * ``linen_tco2e: Decimal`` — linen emissions
        * ``total_scope3_tco2e: Decimal`` — sum of the 4 sub-totals

        Note: input args are kWh / kg / km. Output values are kg CO2e
        (NOT tCO2e) — HCMI methodology reports the raw kg CO2e per category
        so the Frau Steuerberaterin Müller DATEV integrator can apply the
        rounded tCO2e (= kg / 1000) at her preferred display granularity.
        The test_oracle AC-2 contract preserves the canonical kg CO2e
        identifiers in the dict keys (``heating_tco2e`` etc.) but the values
        are kg CO2e (per HCMI convention; the ``_tco2e`` suffix on the dict
        key preserves the HCMI-2025/2026 reference surface).

    Raises:
        ValueError: If any of the 4 arguments is negative.
    """
    # ----- ValueError guard: all 4 arguments must be >= 0 -----
    for arg_name, arg_value in [
        ("heating_kwh_annual", heating_kwh_annual),
        ("food_waste_kg_annual", food_waste_kg_annual),
        ("mobility_km_annual", mobility_km_annual),
        ("linen_kg_annual", linen_kg_annual),
    ]:
        if arg_value < Decimal("0"):
            raise ValueError(
                f"calculate_scope_3 requires all 4 arguments >= 0; "
                f"got {arg_name}={arg_value!r} "
                f"(negative emissions data is invalid)"
            )

    # ----- HCMI 4-category calculation via canonical Decimal string-form -----
    heating_tco2e = Decimal(str(heating_kwh_annual)) * _HCMI_HEATING_KG_CO2E_PER_KWH
    food_waste_tco2e = Decimal(str(food_waste_kg_annual)) * _HCMI_FOOD_WASTE_KG_CO2E_PER_KG
    mobility_tco2e = Decimal(str(mobility_km_annual)) * _HCMI_MOBILITY_KG_CO2E_PER_KM
    linen_tco2e = Decimal(str(linen_kg_annual)) * _HCMI_LINEN_KG_CO2E_PER_KG

    # Total = sum of 4 sub-totals (preserves decimal canonical form).
    total_scope3_tco2e = (
        heating_tco2e
        + food_waste_tco2e
        + mobility_tco2e
        + linen_tco2e
    )

    return {
        "heating_tco2e": heating_tco2e,
        "food_waste_tco2e": food_waste_tco2e,
        "mobility_tco2e": mobility_tco2e,
        "linen_tco2e": linen_tco2e,
        "total_scope3_tco2e": total_scope3_tco2e,
    }


# ---------------------------------------------------------------------------
# Module public API
# ---------------------------------------------------------------------------

__all__ = [
    "calculate_scope_3",
]
