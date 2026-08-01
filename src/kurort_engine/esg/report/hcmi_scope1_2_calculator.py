"""kurort_engine.esg.report.hcmi_scope1_2_calculator — HCMI Scope 1+2 emissions calculator (AC-1+AC-2+AC-3).

Iteration 30 (Developer) — Q5.1 ESG-CSRD/VSME Pattern F chain-extension of iter-27 SHIPPED.
Chosen by iter-29 Critic verdict from iter-28 Scholar Proposal 002 (Axis B HCMI Scope 1+2
EXTENSION of the iter-27 SHIPPED Q5.1 ESG Tier-2 module set).

Implements the Sustainable Hospitality Alliance (SHA) HCMI methodology for
Hotel Rheinland Bad Orb Scope 1 (direct) + Scope 2 (purchased electricity) —
extending the SHIPPED iter-27 ``kurort_engine.esg.report.hcmi_scope3_calculator``
(Sustainable Hospitality Alliance (SHA) HCMI methodology for Scope 3) to the
upstream Scope 1+2 boundaries.

HCMI methodology
----------------
Per the Sustainable Hospitality Alliance (SHA) HCMI methodology (30,000+ hotels
globally use HCMI; 2025/2026 baseline), hotel carbon footprints are decomposed
into 3 emission scopes:

  * **Scope 1** — direct emissions from sources owned/controlled by the hotel.
    For Hotel Rheinland Bad Orb the two Scope 1 categories are *heating* (via
    the Toskana Therme partnership thermal-spring NiedrigEnergie baseline at
    0.05 kg CO2e/kWh, 88 % reduction vs the DE Strommix heating baseline at
    0.42 kg CO2e/kWh) and *refrigeration* (HCMI 2025/2026 baseline refrigerant
    factor 0.15 kg CO2e/kWh for kitchen cold storage).
  * **Scope 2** — indirect emissions from purchased electricity. The
    ``green_electricity_contract`` parameter selects the emission factor:
    OK Lab certified-green ``0.02 kg CO2e/kWh`` (low-background market-based
    factor) for green-certified contracts vs DE Strommix 2026 grid factor
    ``0.42 kg CO2e/kWh`` for standard grid contracts.
  * **Scope 3** — other indirect emissions (handled by the SHIPPED iter-27
    ``kurort_engine.esg.report.hcmi_scope3_calculator.calculate_scope_3()``
    function; not reimplemented here).

Reference: `iter-28-scholar-proposal-002-hcmi-scope-12-extension-axis-b` §3 +
`iter-29-critic-verdict-choose-iter-28-proposal-002-hcmi-scope-12-extension-as-it` §11.

Canonical SHA HCMI methodology reference
---------------------------------------
.. [SHA-HCMI] Sustainable Hospitality Alliance (SHA) HCMI methodology —
   Hotel Carbon Measurement Initiative 2025/2026 baseline (cited verbatim in
   the module docstring per Subagent-B KEPT-2 forced-flaw mitigation;
   https://hmii.global/).

Decimal arithmetic
------------------
All numeric values use :class:`decimal.Decimal` string-form
(``Decimal("0.42")`` NOT ``Decimal(0.42)``) to avoid float drift;
canonical-JSON round-trip via ``json.dumps(result, default=str)`` keeps the
snapshot deterministic for the DATEV integrator surface.
"""
from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Module-level constants — SHA HCMI 2025/2026 baseline emission factors
# ---------------------------------------------------------------------------

#: SHA HCMI 2025/2026 baseline Scope 1 heating factor via the Toskana Therme
#: partnership thermal-spring NiedrigEnergie baseline (0.05 kg CO2e per kWh).
#: 88 % reduction vs DE Strommix heating (0.42 kg CO2e/kWh used in AC-2).
_HCMI_SCOPE1_HEATING_KG_CO2E_PER_KWH: Decimal = Decimal("0.05")

#: SHA HCMI 2025/2026 baseline Scope 1 refrigeration factor (0.15 kg CO2e per
#: kWh) per HCMI refrigerant methodology for hotel kitchen cold storage.
_HCMI_SCOPE1_REFRIGERATION_KG_CO2E_PER_KWH: Decimal = Decimal("0.15")

#: SHA HCMI 2025/2026 baseline Scope 2 market-based factor for OK Lab
#: certified-green electricity contracts (0.02 kg CO2e/kWh). Per Subagent-B
#: KEPT-2 forced-flaw mitigation, the green_contract=True branch MUST select
#: this factor (NOT the DE Strommix grid factor 0.42).
_HCMI_SCOPE2_GREEN_ELECTRICITY_KG_CO2E_PER_KWH: Decimal = Decimal("0.02")

#: SHA HCMI 2025/2026 baseline Scope 2 location-based factor for DE Strommix
#: 2026 grid (0.42 kg CO2e/kWh). Per Subagent-B KEPT-2 forced-flaw mitigation,
#: the green_contract=False branch MUST select this factor.
_HCMI_SCOPE2_GRID_KG_CO2E_PER_KWH: Decimal = Decimal("0.42")


# ---------------------------------------------------------------------------
# AC-1 — calculate_scope_1 (Sustainable Hospitality Alliance (SHA) HCMI Scope 1)
# ---------------------------------------------------------------------------

def calculate_scope_1(
    heating_kwh_annual: Decimal,
    refrigeration_kwh_annual: Decimal,
) -> dict:
    """Calculate HCMI Scope 1 (direct) emissions per the SHA HCMI methodology.

    Per the Sustainable Hospitality Alliance (SHA) HCMI methodology (2025/2026
    baseline), Scope 1 covers the two direct-emission categories that apply to
    Hotel Rheinland Bad Orb:

      * **heating** — Toskana Therme partnership thermal-spring NiedrigEnergie
        baseline (0.05 kg CO2e/kWh, 88 % Scope 1 reduction vs DE Strommix).
      * **refrigeration** — HCMI 2025/2026 baseline refrigerant factor
        (0.15 kg CO2e/kWh) for kitchen cold storage.

    Args:
        heating_kwh_annual: Annual heating electricity consumption in kWh
            (Decimal, ≥ 0).
        refrigeration_kwh_annual: Annual refrigeration electricity consumption
            in kWh (Decimal, ≥ 0).

    Returns:
        JSON-serialisable ``dict`` carrying the 3 required HCMI Scope 1 keys:

          * ``heating_tco2e: Decimal`` — Scope 1 direct heating emissions
            (kg CO2e) via the Toskana Therme thermal-spring NiedrigEnergie
            baseline (0.05 kg CO2e/kWh); the canonical anchor is the SHIPPED
            iter-27 ``scope1_heating_thermal_spring_emissions()`` function.
          * ``refrigeration_tco2e: Decimal`` — Scope 1 direct refrigeration
            emissions (kg CO2e) via the HCMI 2025/2026 baseline refrigeration
            factor (0.15 kg CO2e/kWh).
          * ``total_scope1_tco2e: Decimal`` — Scope 1 total emissions
            (kg CO2e) = heating + refrigeration.

    Raises:
        ValueError: If either ``heating_kwh_annual`` or
            ``refrigeration_kwh_annual`` is negative (negative emissions
            data is invalid per SHA HCMI methodology).
    """
    # ----- ValueError guard: both arguments must be >= 0 -----
    if heating_kwh_annual < Decimal("0"):
        raise ValueError(
            f"calculate_scope_1 requires heating_kwh_annual >= 0; "
            f"got {heating_kwh_annual!r} "
            f"(negative heating consumption is invalid per SHA HCMI methodology)"
        )
    if refrigeration_kwh_annual < Decimal("0"):
        raise ValueError(
            f"calculate_scope_1 requires refrigeration_kwh_annual >= 0; "
            f"got {refrigeration_kwh_annual!r} "
            f"(negative refrigeration consumption is invalid per SHA HCMI methodology)"
        )

    # ----- SHA HCMI Scope 1 calculation via canonical Decimal string-form -----
    heating_tco2e = Decimal(str(heating_kwh_annual)) * _HCMI_SCOPE1_HEATING_KG_CO2E_PER_KWH
    refrigeration_tco2e = Decimal(str(refrigeration_kwh_annual)) * _HCMI_SCOPE1_REFRIGERATION_KG_CO2E_PER_KWH

    # Total = sum of the 2 sub-totals (preserves decimal canonical form).
    total_scope1_tco2e = heating_tco2e + refrigeration_tco2e

    return {
        "heating_tco2e": heating_tco2e,
        "refrigeration_tco2e": refrigeration_tco2e,
        "total_scope1_tco2e": total_scope1_tco2e,
    }


# ---------------------------------------------------------------------------
# AC-2 — calculate_scope_2 (Sustainable Hospitality Alliance (SHA) HCMI Scope 2)
# ---------------------------------------------------------------------------

def calculate_scope_2(
    purchased_electricity_kwh_annual: Decimal,
    green_electricity_contract: bool,
) -> dict:
    """Calculate HCMI Scope 2 (purchased electricity) emissions per SHA HCMI.

    Per the Sustainable Hospitality Alliance (SHA) HCMI methodology, Scope 2
    covers indirect emissions from purchased electricity. The
    ``green_electricity_contract`` parameter selects between two canonical
    emission factors (per Subagent-B KEPT-2 forced-flaw mitigation):

      * ``green_electricity_contract=True`` → OK Lab certified-green factor
        ``0.02 kg CO2e/kWh`` (market-based renewable tariff).
      * ``green_electricity_contract=False`` → DE Strommix 2026 grid factor
        ``0.42 kg CO2e/kWh`` (location-based grid average).

    The returned dict ALWAYS reports both ``grid_tco2e`` AND
    ``green_electricity_tco2e`` keys for transparency (even though only one
    applies to the hotel's actual electricity contract); the
    ``total_scope2_tco2e`` key reflects the selected contract type.

    Args:
        purchased_electricity_kwh_annual: Annual purchased electricity in kWh
            (Decimal, ≥ 0).
        green_electricity_contract: Whether the hotel has an OK Lab certified
            green-electricity contract (``True`` uses the 0.02 kg CO2e/kWh
            factor; ``False`` uses the DE Strommix 0.42 kg CO2e/kWh factor).

    Returns:
        JSON-serialisable ``dict`` carrying the 3 required HCMI Scope 2 keys:

          * ``grid_tco2e: Decimal`` — DE Strommix 2026 location-based grid
            emissions (kg CO2e) = kWh × 0.42.
          * ``green_electricity_tco2e: Decimal`` — OK Lab certified-green
            market-based emissions (kg CO2e) = kWh × 0.02.
          * ``total_scope2_tco2e: Decimal`` — total Scope 2 emissions
            (kg CO2e) selected by ``green_electricity_contract``:
              - True  → kWh × Decimal("0.02")
              - False → kWh × Decimal("0.42")

    Raises:
        ValueError: If ``purchased_electricity_kwh_annual`` is negative.
    """
    # ----- ValueError guard: argument must be >= 0 -----
    if purchased_electricity_kwh_annual < Decimal("0"):
        raise ValueError(
            f"calculate_scope_2 requires purchased_electricity_kwh_annual >= 0; "
            f"got {purchased_electricity_kwh_annual!r} "
            f"(negative purchased electricity is invalid per SHA HCMI methodology)"
        )

    purchased_kwh = Decimal(str(purchased_electricity_kwh_annual))

    # Always compute both factors for transparency reporting (DATEV audit surface).
    grid_tco2e = purchased_kwh * _HCMI_SCOPE2_GRID_KG_CO2E_PER_KWH
    green_electricity_tco2e = purchased_kwh * _HCMI_SCOPE2_GREEN_ELECTRICITY_KG_CO2E_PER_KWH

    # Per Subagent-B KEPT-2 forced-flaw mitigation: green_contract=True MUST
    # select the OK Lab factor; green_contract=False MUST select the DE
    # Strommix grid factor (no fall-through between branches).
    if green_electricity_contract:
        total_scope2_tco2e = green_electricity_tco2e
    else:
        total_scope2_tco2e = grid_tco2e

    return {
        "grid_tco2e": grid_tco2e,
        "green_electricity_tco2e": green_electricity_tco2e,
        "total_scope2_tco2e": total_scope2_tco2e,
    }


# ---------------------------------------------------------------------------
# AC-3 — calculate_scope_1_2 (Sustainable Hospitality Alliance (SHA) HCMI Scope 1+2 unified)
# ---------------------------------------------------------------------------

def calculate_scope_1_2(
    heating_kwh_annual: Decimal,
    refrigeration_kwh_annual: Decimal,
    purchased_electricity_kwh_annual: Decimal,
    green_electricity_contract: bool,
) -> dict:
    """Calculate HCMI Scope 1+2 unified emissions per the SHA HCMI methodology.

    Composes the AC-1 ``calculate_scope_1()`` sub-result (heating +
    refrigeration) and the AC-2 ``calculate_scope_2()`` sub-result
    (purchased electricity, ``green_electricity_contract`` selection) into
    a single JSON-serialisable HCMI Scope 1+2 envelope per the Sustainable
    Hospitality Alliance (SHA) HCMI methodology 2025/2026 baseline.

    Args:
        heating_kwh_annual: Annual heating electricity consumption in kWh
            (Decimal, ≥ 0). Forwarded to :func:`calculate_scope_1`.
        refrigeration_kwh_annual: Annual refrigeration electricity consumption
            in kWh (Decimal, ≥ 0). Forwarded to :func:`calculate_scope_1`.
        purchased_electricity_kwh_annual: Annual purchased electricity in kWh
            (Decimal, ≥ 0). Forwarded to :func:`calculate_scope_2`.
        green_electricity_contract: Whether the hotel has an OK Lab certified
            green-electricity contract. Forwarded to :func:`calculate_scope_2`.

    Returns:
        JSON-serialisable ``dict`` carrying the 3 required HCMI Scope 1+2
        top-level keys:

          * ``scope1: dict`` — verbatim AC-1 ``calculate_scope_1`` return
            dict (heating_tco2e + refrigeration_tco2e + total_scope1_tco2e).
          * ``scope2: dict`` — verbatim AC-2 ``calculate_scope_2`` return
            dict (grid_tco2e + green_electricity_tco2e + total_scope2_tco2e).
          * ``total_scope1_2_tco2e: Decimal`` — SHA HCMI Scope 1+2 total
            emissions (kg CO2e) = AC-1 total + AC-2 total.

    Raises:
        ValueError: If any of ``heating_kwh_annual``, ``refrigeration_kwh_annual``
            or ``purchased_electricity_kwh_annual`` is negative. Propagated
            from the AC-1 + AC-2 calc helpers.
    """
    # ----- Compose AC-1 Scope 1 + AC-2 Scope 2 via canonical helpers -----
    scope1 = calculate_scope_1(heating_kwh_annual, refrigeration_kwh_annual)
    scope2 = calculate_scope_2(purchased_electricity_kwh_annual, green_electricity_contract)

    # ----- Compute the SHA HCMI Scope 1+2 envelope total -----
    total_scope1_2_tco2e = scope1["total_scope1_tco2e"] + scope2["total_scope2_tco2e"]

    return {
        "scope1": scope1,
        "scope2": scope2,
        "total_scope1_2_tco2e": total_scope1_2_tco2e,
    }


# ---------------------------------------------------------------------------
# Module public API
# ---------------------------------------------------------------------------

__all__ = [
    "calculate_scope_1",
    "calculate_scope_2",
    "calculate_scope_1_2",
]
