"""kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030 — AC-3 alignment surface.

Iteration 27 (Developer) — Q5.1 ESG-CSRD/VSME Group 2.
Chosen by Critic verdict (iter-26) from iter-25 Scholar Proposal 002.

AC-3 contract (verbatim from spec.yaml):

    Event-driven. When `check_alignment(emissions_tco2e_annual, baseline_year)` is
    called in `kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030` THEN
    the system shall return a `dict` per the Gastgeber-Klimaneutralität 2030
    voluntary initiative + Thüringer Heilbäderverband "Klimaneutraler Kurort"
    2025 Modell-Kurorte precedent (Bad Klosterlausnitz / Bad Langensalza /
    Bad Sulza / Saalfeld), with required keys: `aligned: bool` (True iff
    `emissions_tco2e_annual * trajectory_factor(baseline_year) <= 0`),
    `offset_required_tco2e: Decimal` (residual CO2 to offset via Gold Standard
    VER credits at 2026-Q3 market rate €55-65/t), `reduction_trajectory: list`
    (yearly reduction factors from baseline_year to 2030, e.g. `[(2024, 1.0),
    (2026, 0.95), (2028, 0.75), (2030, 0.50)]`); the function MUST raise
    `ValueError` if `baseline_year > 2030`.

Reference: Gold Standard VER credit 2026-Q3 market rate €55-65/t per
`iter-25-proposal-002-q51-esg-csrd-voluntary-vsme-hcmi-scope-3-tier-2-410-loc` §3.
"""
from __future__ import annotations

from decimal import Decimal

# Gastgeber-Klimaneutralität 2030 voluntary trajectory.
# Linear interpolation between canonical anchor years (per spec.yaml §A-4).
# Step form used to keep the contract deterministic and easy to verify:
#   2024: 1.000  (baseline, no reduction)
#   2025: 0.980
#   2026: 0.950
#   2027: 0.850
#   2028: 0.750
#   2029: 0.625
#   2030: 0.500  (Klimaneutralität endpoint: 50% reduction)
#
# Years OUTSIDE the 2024..2030 inclusive range are invalid (raises ValueError
# per spec.yaml AC-3 EARS contract when baseline_year > 2030).
TRAJECTORY_FACTOR: dict[int, Decimal] = {
    2024: Decimal("1.000"),
    2025: Decimal("0.980"),
    2026: Decimal("0.950"),
    2027: Decimal("0.850"),
    2028: Decimal("0.750"),
    2029: Decimal("0.625"),
    2030: Decimal("0.500"),
}

# 4 canonical anchor tuples per spec.yaml AC-3 EARS contract
# (used both for the reduction_trajectory return value AND as the
# auditable public reduction trajectory the spec mandates).
REDUCTION_TRAJECTORY: list[tuple[int, float]] = [
    (2024, 1.0),
    (2026, 0.95),
    (2028, 0.75),
    (2030, 0.50),
]


def check_alignment(
    emissions_tco2e_annual: Decimal,
    baseline_year: int,
) -> dict:
    """Compute Gastgeber-Klimaneutralität 2030 alignment for Hotel Rheinland.

    Parameters
    ----------
    emissions_tco2e_annual : Decimal
        Annual emissions in tCO2e (Scope 1 + 2 + 3 per VSME Basic Module B3).
        Must be >= 0 (negative emissions are unphysical for a hotellerie).
    baseline_year : int
        The reporting baseline year. MUST be in the inclusive range
        [2024, 2030] (Klimaneutralität 2030 trajectory endpoint).
        Raises ``ValueError`` if ``baseline_year > 2030`` (and below 2024,
        per the trajectory table only).

    Returns
    -------
    dict
        A JSON-serialisable dict with required keys per spec.yaml AC-3 EARS:

          * ``aligned`` — ``bool``, ``True`` iff
            ``emissions_tco2e_annual * trajectory_factor(baseline_year) <= 0``
            (i.e. the residual offset has been driven to zero or below).
          * ``offset_required_tco2e`` — ``Decimal``, residual CO2 to offset
            via Gold Standard VER credits at 2026-Q3 market rate €55-65/t.
            Equal to ``emissions_tco2e_annual * trajectory_factor(baseline_year)``.
          * ``reduction_trajectory`` — ``list[tuple[int, float]]``, the 4
            canonical (year, factor) anchor tuples of the Klimaneutralität
            2030 voluntary trajectory. ALWAYS contains all 4 canonical
            tuples: ``[(2024, 1.0), (2026, 0.95), (2028, 0.75), (2030, 0.50)]``.

    Raises
    ------
    ValueError
        If ``baseline_year > 2030`` (Klimaneutralität 2030 trajectory endpoint)
        OR if ``baseline_year < 2024`` (trajectory table not defined for
        pre-2024 years per the Gastgeber-Klimaneutralität 2030 voluntary
        initiative scope which begins 2024).
    """
    # ----- input validation (per AC-3 EARS contract + Decimal discipline) -----
    if not isinstance(baseline_year, int):
        raise ValueError(
            f"baseline_year must be int, got {type(baseline_year).__name__}: "
            f"{baseline_year!r}"
        )
    if baseline_year > 2030:
        raise ValueError(
            f"baseline_year={baseline_year} exceeds Klimaneutralität 2030 "
            f"trajectory endpoint (2030)"
        )
    if baseline_year < 2024:
        raise ValueError(
            f"baseline_year={baseline_year} is below the 2024 Gastgeber-"
            f"Klimaneutralität 2030 trajectory start"
        )
    if not isinstance(emissions_tco2e_annual, Decimal):
        raise ValueError(
            f"emissions_tco2e_annual must be Decimal, got "
            f"{type(emissions_tco2e_annual).__name__}: "
            f"{emissions_tco2e_annual!r}"
        )
    if emissions_tco2e_annual < Decimal("0"):
        raise ValueError(
            f"emissions_tco2e_annual must be >= 0; "
            f"got {emissions_tco2e_annual!r}"
        )

    # ----- core computation via canonical Decimal string-form arithmetic -----
    factor = TRAJECTORY_FACTOR[baseline_year]
    residual_offset = emissions_tco2e_annual * factor

    # Aligned iff the residual offset has been driven to zero or below.
    # Note: Decimal("0") <= Decimal("0") is True, so a zero-emissions hotel
    # in baseline_year=2030 (0 * 0.5 = 0) is aligned.
    aligned = residual_offset <= Decimal("0")

    return {
        "aligned": aligned,
        "offset_required_tco2e": residual_offset,
        "reduction_trajectory": list(REDUCTION_TRAJECTORY),
    }


__all__ = ["check_alignment", "TRAJECTORY_FACTOR", "REDUCTION_TRAJECTORY"]
