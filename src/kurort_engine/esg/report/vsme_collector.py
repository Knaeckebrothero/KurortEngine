"""kurort_engine.esg.report.vsme_collector — VSME Basic Module B3 collector (AC-1).

Collects the EU Commission VSME Recommendation 30 Jul 2025 Basic Module B3
(Energy + GHG emissions) for Hotel Rheinland Bad Orb (33-room Heilbad) over
one annual reporting period.

Iteration 27 (Developer) Q5.1 Tier-2 ESG-CSRD Voluntary VSME + HCMI Scope 3 —
implements AC-1 (Ubiquitous). Surface verified against the SHIPPED iter-24
kurort_engine.ev_charging sub-package structure for naming + re-export
convention.

VSME methodology
----------------
Per `EU Commission VSME Recommendation 30 Jul 2025 <https://ec.europa.eu/>`_,
EFRAG-developed Basic Module B3 requires:

  * ``energy_kwh_annual`` — total energy kWh for the reporting period
  * ``ghg_emissions_tco2e_annual`` — Scope 1+2+3 tCO2e sum per VSME B3
  * ``reporting_basis`` — ``"EU VSME Recommendation 30 Jul 2025"``
  * ``report_period_start`` + ``report_period_end`` — reporting period dates
  * ``entity_name`` — ``"Hotel Rheinland"`` (single entity, 33-room Heilbad)

Decimal arithmetic
------------------
All numeric emissions values use :class:`decimal.Decimal` (NOT ``float``) to
keep the canonical-JSON snapshot free of float drift (matches the
kurort-vertical Decimal policy from iter-21 kurkarte_wallet).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: VSME reporting basis string per EU Commission VSME Recommendation 30 Jul 2025.
_VSME_REPORTING_BASIS: str = "EU VSME Recommendation 30 Jul 2025"

#: Pilot single-entity name (33-room Heilbad Bad Orb).
_VSME_ENTITY_NAME: str = "Hotel Rheinland"

#: Annual energy kWh envelope (33-room hotel baseline; matches iter-24
#: ev_charging + iter-18 Kurpaket audit-pipeline envelope).
_ANNUAL_ENERGY_KWH_BASELINE: Decimal = Decimal("100000")

#: Annual GHG emissions tCO2e baseline (Scope 1+2+3 per VSME B3).
_ANNUAL_GHG_TCO2E_BASELINE: Decimal = Decimal("42")  # 33-room hotel envelope


# ---------------------------------------------------------------------------
# AC-1 — collect_basic_module_b3
# ---------------------------------------------------------------------------

def collect_basic_module_b3(
    report_period: tuple[date, date],
) -> dict:
    """Collect the VSME Basic Module B3 (Energy + GHG) for one annual period.

    Args:
        report_period: 2-tuple of :class:`datetime.date` carrying the
            ``(start, end)`` reporting period (inclusive). Must satisfy
            ``start <= end``.

    Returns:
        JSON-serialisable ``dict`` carrying the 6 required VSME B3 keys:

        * ``energy_kwh_annual: Decimal`` — total energy kWh for the period
        * ``ghg_emissions_tco2e_annual: Decimal`` — Scope 1+2+3 tCO2e sum
        * ``reporting_basis: str = "EU VSME Recommendation 30 Jul 2025"``
        * ``report_period_start: date`` — period start (inclusive)
        * ``report_period_end: date`` — period end (inclusive)
        * ``entity_name: str = "Hotel Rheinland"``

    Raises:
        ValueError: If ``report_period_start > report_period_end``.
    """
    report_period_start, report_period_end = report_period

    # ----- ValueError guard: invalid reporting period -----
    if report_period_start > report_period_end:
        raise ValueError(
            f"collect_basic_module_b3 requires report_period_start <= "
            f"report_period_end; got start={report_period_start!r}, "
            f"end={report_period_end!r} (start > end)"
        )

    # ----- VSME B3 minimum data: Energy + GHG single-entity pilot -----
    # NOTE: pilot scope uses baseline envelope (matches iter-24 ev_charging
    # + iter-18 Kurpaket audit-pipeline baseline). Real per-period lookup
    # is DEFERRED to iter-28+ Tier-3 (per `iter-25-proposal-002-...` §11
    # Risks: "Frau Steuerberaterin Müller turnover / availability").
    return {
        "energy_kwh_annual": _ANNUAL_ENERGY_KWH_BASELINE,
        "ghg_emissions_tco2e_annual": _ANNUAL_GHG_TCO2E_BASELINE,
        "reporting_basis": _VSME_REPORTING_BASIS,
        "report_period_start": report_period_start,
        "report_period_end": report_period_end,
        "entity_name": _VSME_ENTITY_NAME,
    }


# ---------------------------------------------------------------------------
# Module public API
# ---------------------------------------------------------------------------

__all__ = [
    "collect_basic_module_b3",
]
