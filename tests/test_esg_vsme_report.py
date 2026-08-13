"""Q5.1 AC-1 + AC-2 — kurort_engine.esg.report.vsme_collector + hcmi_scope3_calculator test surface.

AC-1 contract (verbatim from spec.yaml):

    Ubiquitous. The system shall expose a `collect_basic_module_b3(report_period)`
    function in `kurort_engine.esg.report.vsme_collector` that, when given a
    `report_period: tuple[date, date]` (start, end inclusive) covering one
    annual reporting period, returns a `dict` per EU Commission VSME
    Recommendation 30 Jul 2025 (EFRAG-developed Basic Module B3 = Energy +
    GHG emissions) with required keys: `energy_kwh_annual: Decimal`, `ghg_emissions_tco2e_annual:
    Decimal`, `reporting_basis: str = "EU VSME Recommendation 30 Jul 2025"`,
    `report_period_start: date`, `report_period_end: date`, `entity_name: str = "Hotel Rheinland"`;
    the function MUST raise `ValueError` if `report_period_start > report_period_end`.

AC-2 contract (verbatim from spec.yaml):

    Event-driven. When `calculate_scope_3(heating_kwh_annual, food_waste_kg_annual,
    mobility_km_annual, linen_kg_annual)` is called in `kurort_engine.esg.report.hcmi_scope3_calculator`
    THEN the system shall return a `dict` per the Hotel Carbon Measurement
    Initiative (HCMI) methodology (30,000+ hotels globally, 2025/2026 baseline)
    with required keys: `heating_tco2e: Decimal` (heating emissions via
    German grid factor 0.42 kg CO2e/kWh — DE Strommix 2026), `food_waste_tco2e:
    Decimal` (food waste via HCMI 2.5 kg CO2e/kg baseline), `mobility_tco2e:
    Decimal`
    (mobility via HCMI 0.171 kg CO2e/km baseline; reduced by iter-24 E-Bike
    charging per `kurort_engine.ev_charging.read_session`), `linen_tco2e: Decimal`
    (linen via HCMI 5.5 kg CO2e/kg baseline), `total_scope3_tco2e: Decimal`
    (sum of the four sub-totals); the function MUST raise `ValueError` if
    any argument is negative.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check (wrapped in try/except) so
missing-module failures surface as ``AssertionError`` ("module should exist"),
not ``ModuleNotFoundError``.

Per `iter-27-pinned-tdd-rules-q5-1-esg-tdd-discipline-forbidden-test-patterns`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete Decimal string-form arithmetic for emission factors (no float drift)
  * Concrete `pytest.raises(ValueError)` guard for the invalid-input assertion
  * Concrete JSON-serialisability round-trip via `json.dumps(result, default=str)`
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from decimal import Decimal

import pytest

# ===========================================================================
# Module-importability helpers (per iter-24 honest-RED pattern)
# ===========================================================================

def _find_spec_or_assert(module_name: str, *, parent: str | None = None) -> str:
    """Run ``importlib.util.find_spec`` and coerce missing-module failures
    into ``AssertionError`` so the test surfaces a "spec unmet" failure
    rather than a ``ModuleNotFoundError`` import failure.

    Per pinned rule 3 (RED verification protocol): red-phase tests must fail
    with ``AssertionError``, not ``ImportError`` / ``ModuleNotFoundError`` /
    ``SyntaxError``.
    """
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError) as exc:
        scope = parent or module_name
        raise AssertionError(
            f"{scope} is not importable — green phase must create the "
            f"module before this test can pass. find_spec raised: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    assert found is not None, (
        f"{module_name} is not importable — green phase must create the "
        f"module before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _esg_report_package_is_importable() -> str:
    """Pre-check: the new esg.report package must exist."""
    return _find_spec_or_assert("kurort_engine.esg.report")


def _vsme_collector_module_is_importable() -> str:
    """Pre-check: the new esg.report.vsme_collector module must exist (AC-1)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.vsme_collector",
        parent="kurort_engine.esg.report.vsme_collector",
    )


def _hcmi_scope3_calculator_module_is_importable() -> str:
    """Pre-check: the new esg.report.hcmi_scope3_calculator module must exist (AC-2)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.hcmi_scope3_calculator",
        parent="kurort_engine.esg.report.hcmi_scope3_calculator",
    )


def _get_esg_report_package():
    """Import the esg.report package after the find_spec guard."""
    _esg_report_package_is_importable()
    import kurort_engine.esg.report as _rpt  # noqa: E402
    assert _rpt is not None, "importlib returned None — package is None"
    return _rpt


def _get_vsme_collector_module():
    """Import the esg.report.vsme_collector module after the find_spec guard."""
    _vsme_collector_module_is_importable()
    import kurort_engine.esg.report.vsme_collector as _vc  # noqa: E402
    assert _vc is not None, "importlib returned None — module is None"
    return _vc


def _get_hcmi_scope3_calculator_module():
    """Import the esg.report.hcmi_scope3_calculator module after the find_spec guard."""
    _hcmi_scope3_calculator_module_is_importable()
    import kurort_engine.esg.report.hcmi_scope3_calculator as _hcmi  # noqa: E402
    assert _hcmi is not None, "importlib returned None — module is None"
    return _hcmi


# ===========================================================================
# AC-1 — collect_basic_module_b3 returns VSME Basic Module B3 dict
# ===========================================================================

def test_ac1_collect_basic_module_b3_emits_vsme_b3_dict() -> None:
    """AC-1 spec test_oracle — happy-path 2024 annual reporting period.

    Asserts that ``collect_basic_module_b3((date(2024, 1, 1), date(2024, 12, 31)))``
    returns a JSON-serialisable dict per EU Commission VSME Recommendation
    30 Jul 2025 (EFRAG-developed Basic Module B3 = Energy + GHG emissions)
    with required keys:
      * ``energy_kwh_annual`` — Decimal (total energy kWh for the period)
      * ``ghg_emissions_tco2e_annual`` — Decimal (Scope 1+2+3 tCO2e sum per VSME B3)
      * ``reporting_basis`` — str, must equal ``"EU VSME Recommendation 30 Jul 2025"``
      * ``report_period_start`` — date, must equal ``date(2024, 1, 1)``
      * ``report_period_end`` — date, must equal ``date(2024, 12, 31)``
      * ``entity_name`` — str, must equal ``"Hotel Rheinland"``
    """
    _vsme_collector_module_is_importable()
    vc_mod = _get_vsme_collector_module()

    # Function must be exposed under the canonical name (no rename allowed).
    collect_basic_module_b3 = getattr(vc_mod, "collect_basic_module_b3", None)
    assert callable(collect_basic_module_b3), (
        "AC-1: vsme_collector must expose a callable collect_basic_module_b3 "
        f"entry point; found: {[n for n in dir(vc_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: 2024 annual reporting period -----
    report_period = (date(2024, 1, 1), date(2024, 12, 31))
    result = collect_basic_module_b3(report_period)

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-1: collect_basic_module_b3 must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip (default=str handles date + Decimal) -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-1: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (6 required keys) -----
    required_keys = [
        "energy_kwh_annual",
        "ghg_emissions_tco2e_annual",
        "reporting_basis",
        "report_period_start",
        "report_period_end",
        "entity_name",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-1: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- value-type + exact-value assertions (per AC-1 EARS) -----
    assert isinstance(result["energy_kwh_annual"], Decimal), (
        f"AC-1: energy_kwh_annual must be a Decimal; "
        f"got {type(result['energy_kwh_annual']).__name__}: "
        f"{result['energy_kwh_annual']!r}"
    )
    assert result["energy_kwh_annual"] >= Decimal("0"), (
        f"AC-1: energy_kwh_annual must be >= 0; "
        f"got {result['energy_kwh_annual']!r}"
    )

    assert isinstance(result["ghg_emissions_tco2e_annual"], Decimal), (
        f"AC-1: ghg_emissions_tco2e_annual must be a Decimal; "
        f"got {type(result['ghg_emissions_tco2e_annual']).__name__}: "
        f"{result['ghg_emissions_tco2e_annual']!r}"
    )
    assert result["ghg_emissions_tco2e_annual"] >= Decimal("0"), (
        f"AC-1: ghg_emissions_tco2e_annual must be >= 0; "
        f"got {result['ghg_emissions_tco2e_annual']!r}"
    )

    assert result["reporting_basis"] == "EU VSME Recommendation 30 Jul 2025", (
        f"AC-1: reporting_basis must equal 'EU VSME Recommendation 30 Jul 2025'; "
        f"got {result['reporting_basis']!r}"
    )

    assert result["report_period_start"] == date(2024, 1, 1), (
        f"AC-1: report_period_start must equal date(2024, 1, 1); "
        f"got {result['report_period_start']!r}"
    )
    assert result["report_period_end"] == date(2024, 12, 31), (
        f"AC-1: report_period_end must equal date(2024, 12, 31); "
        f"got {result['report_period_end']!r}"
    )
    assert result["entity_name"] == "Hotel Rheinland", (
        f"AC-1: entity_name must equal 'Hotel Rheinland'; "
        f"got {result['entity_name']!r}"
    )


# ===========================================================================
# AC-1 — ValueError guard: invalid report_period (start > end)
# ===========================================================================

def test_ac1_collect_basic_module_b3_invalid_period_raises_value_error() -> None:
    """AC-1 spec test_oracle — ValueError guard for invalid reporting period.

    Asserts that ``collect_basic_module_b3((date(2024, 12, 31), date(2024, 1, 1)))``
    raises ``ValueError`` because ``report_period_start > report_period_end``.
    """
    _vsme_collector_module_is_importable()
    vc_mod = _get_vsme_collector_module()

    collect_basic_module_b3 = getattr(vc_mod, "collect_basic_module_b3", None)
    assert callable(collect_basic_module_b3), (
        "AC-1: vsme_collector must expose a callable collect_basic_module_b3 "
        "for the ValueError guard to be testable"
    )

    # ----- invalid period: start (Dec 31) > end (Jan 1) — must raise ValueError -----
    invalid_period = (date(2024, 12, 31), date(2024, 1, 1))
    with pytest.raises(ValueError):
        collect_basic_module_b3(invalid_period)


# ===========================================================================
# AC-2 — calculate_scope_3 returns HCMI methodology dict
# ===========================================================================

def test_ac2_hcmi_calculate_scope_3_emits_hcmi_methodology_dict() -> None:
    """AC-2 spec test_oracle — happy-path HCMI Scope 3 calculation.

    Asserts that ``calculate_scope_3(Decimal("10000"), Decimal("2000"),
    Decimal("50000"), Decimal("500"))`` returns a JSON-serialisable dict per
    the HCMI methodology (30,000+ hotels globally, 2025/2026 baseline) with
    required keys (each value a Decimal, computed via canonical Decimal
    string-form arithmetic to avoid float drift):

      * ``heating_tco2e``  — Decimal == Decimal("10000") * Decimal("0.42")
      * ``food_waste_tco2e`` — Decimal == Decimal("2000") * Decimal("2.5")
      * ``mobility_tco2e`` — Decimal == Decimal("50000") * Decimal("0.171")
      * ``linen_tco2e`` — Decimal == Decimal("500") * Decimal("5.5")
      * ``total_scope3_tco2e`` — Decimal == sum of the four sub-totals
    """
    _hcmi_scope3_calculator_module_is_importable()
    hcmi_mod = _get_hcmi_scope3_calculator_module()

    # Function must be exposed under the canonical name.
    calculate_scope_3 = getattr(hcmi_mod, "calculate_scope_3", None)
    assert callable(calculate_scope_3), (
        "AC-2: hcmi_scope3_calculator must expose a callable calculate_scope_3 "
        f"entry point; found: {[n for n in dir(hcmi_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: hotel-scale HCMI envelope -----
    heating_kwh = Decimal("10000")    # 10,000 kWh heating (33-room hotel envelope)
    food_waste_kg = Decimal("2000")   # 2,000 kg food waste annually
    mobility_km = Decimal("50000")    # 50,000 km mobility (staff + guest excursions)
    linen_kg = Decimal("500")         # 500 kg linen turnover
    result = calculate_scope_3(heating_kwh, food_waste_kg, mobility_km, linen_kg)

    # ----- return-type check -----
    assert isinstance(result, dict), (
        f"AC-2: calculate_scope_3 must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-2: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (5 required keys) -----
    required_keys = [
        "heating_tco2e",
        "food_waste_tco2e",
        "mobility_tco2e",
        "linen_tco2e",
        "total_scope3_tco2e",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-2: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- expected emissions via canonical Decimal string-form arithmetic -----
    expected_heating = Decimal("10000") * Decimal("0.42")     # = Decimal("4200.000")
    expected_food_waste = Decimal("2000") * Decimal("2.5")    # = Decimal("5000.000")
    expected_mobility = Decimal("50000") * Decimal("0.171")   # = Decimal("8550.000")
    expected_linen = Decimal("500") * Decimal("5.5")           # = Decimal("2750.000")
    expected_total = expected_heating + expected_food_waste + expected_mobility + expected_linen
    # = Decimal("20500.000")

    # ----- Decimal-type + exact-equality assertions -----
    for key, expected in [
        ("heating_tco2e", expected_heating),
        ("food_waste_tco2e", expected_food_waste),
        ("mobility_tco2e", expected_mobility),
        ("linen_tco2e", expected_linen),
        ("total_scope3_tco2e", expected_total),
    ]:
        assert isinstance(result[key], Decimal), (
            f"AC-2: {key} must be a Decimal; "
            f"got {type(result[key]).__name__}: {result[key]!r}"
        )
        assert result[key] == expected, (
            f"AC-2: {key} must equal {expected!r} (canonical Decimal arithmetic); "
            f"got {result[key]!r}"
        )


# ===========================================================================
# AC-2 — ValueError guard: negative argument
# ===========================================================================

def test_ac2_hcmi_calculate_scope_3_negative_input_raises_value_error() -> None:
    """AC-2 spec test_oracle — ValueError guard for negative input.

    Asserts that ``calculate_scope_3(Decimal("-1"), Decimal("0"),
    Decimal("0"), Decimal("0"))`` raises ``ValueError`` because
    ``heating_kwh_annual < 0`` (negative emissions data is invalid).
    """
    _hcmi_scope3_calculator_module_is_importable()
    hcmi_mod = _get_hcmi_scope3_calculator_module()

    calculate_scope_3 = getattr(hcmi_mod, "calculate_scope_3", None)
    assert callable(calculate_scope_3), (
        "AC-2: hcmi_scope3_calculator must expose a callable calculate_scope_3 "
        "for the ValueError guard to be testable"
    )

    # ----- negative heating input: must raise ValueError -----
    with pytest.raises(ValueError):
        calculate_scope_3(Decimal("-1"), Decimal("0"), Decimal("0"), Decimal("0"))

# ===========================================================================
# AC-3 — check_alignment returns Gastgeber-Klimaneutralität 2030 dict
# ===========================================================================
# Per spec.yaml AC-3 (verbatim):
#   Event-driven. When `check_alignment(emissions_tco2e_annual, baseline_year)` is
#   called in `kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030` THEN
#   the system shall return a `dict` per the Gastgeber-Klimaneutralität 2030
#   voluntary initiative + Thüringer Heilbäderverband "Klimaneutraler Kurort"
#   2025 Modell-Kurorte precedent, with required keys: `aligned: bool` (True iff
#   `emissions_tco2e_annual * trajectory_factor(baseline_year) <= 0`),
#   `offset_required_tco2e: Decimal` (residual CO2 to offset via Gold Standard
#   VER credits at 2026-Q3 market rate €55-65/t), `reduction_trajectory: list`
#   (yearly reduction factors from baseline_year to 2030, e.g. `[(2024, 1.0),
#   (2026, 0.95), (2028, 0.75), (2030, 0.50)]`); the function MUST raise
#   `ValueError` if `baseline_year > 2030`.

def _gastgeber_module_is_importable() -> str:
    """Pre-check: the new esg.report.gastgeber_klimaneutralitaet_2030 module must exist (AC-3)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030",
        parent="kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030",
    )


def _get_gastgeber_module():
    """Import the esg.report.gastgeber_klimaneutralitaet_2030 module after the find_spec guard."""
    _gastgeber_module_is_importable()
    import kurort_engine.esg.report.gastgeber_klimaneutralitaet_2030 as _gk  # noqa: E402
    assert _gk is not None, "importlib returned None — module is None"
    return _gk


def test_ac3_check_alignment_emits_klimaneutralitaet_2030_dict() -> None:
    """AC-3 spec test_oracle — happy-path Gastgeber-Klimaneutralität 2030 alignment.

    Asserts that ``check_alignment(Decimal("100"), 2024)`` returns a
    JSON-serialisable dict per the Gastgeber-Klimaneutralität 2030 voluntary
    initiative + Thüringer Heilbäderverband "Klimaneutraler Kurort" 2025
    Modell-Kurorte precedent (Bad Klosterlausnitz / Bad Langensalza / Bad Sulza
    / Saalfeld), with required keys:

      * ``aligned`` — bool, True iff ``emissions_tco2e_annual * trajectory_factor(baseline_year) <= 0``
        For baseline_year=2024, trajectory_factor=1.0, so 100*1.0=100>0 → aligned=False
      * ``offset_required_tco2e`` — Decimal, residual CO2 to offset via Gold Standard
        VER credits at 2026-Q3 market rate €55-65/t (= emissions_tco2e_annual * 1.0 = 100)
      * ``reduction_trajectory`` — list of (year:int, factor:float) tuples from
        baseline_year=2024 to 2030, e.g. [(2024, 1.0), (2026, 0.95), (2028, 0.75), (2030, 0.50)]
    """
    _gastgeber_module_is_importable()
    gk_mod = _get_gastgeber_module()

    # Function must be exposed under the canonical name (no rename allowed).
    check_alignment = getattr(gk_mod, "check_alignment", None)
    assert callable(check_alignment), (
        "AC-3: gastgeber_klimaneutralitaet_2030 must expose a callable check_alignment "
        f"entry point; found: {[n for n in dir(gk_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: 100 tCO2e annual emissions, baseline_year=2024 -----
    emissions_tco2e_annual = Decimal("100")
    baseline_year = 2024
    result = check_alignment(emissions_tco2e_annual, baseline_year)

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-3: check_alignment must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip (default=str handles Decimal) -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-3: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (3 required keys) -----
    required_keys = ["aligned", "offset_required_tco2e", "reduction_trajectory"]
    for key in required_keys:
        assert key in result, (
            f"AC-3: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- aligned: bool, must be False (100*1.0=100 > 0) -----
    assert isinstance(result["aligned"], bool), (
        f"AC-3: aligned must be a bool; "
        f"got {type(result['aligned']).__name__}: {result['aligned']!r}"
    )
    assert result["aligned"] is False, (
        f"AC-3: aligned must be False (100*1.0=100 > 0); got {result['aligned']!r}"
    )

    # ----- offset_required_tco2e: Decimal == emissions * 1.0 (baseline factor) -----
    assert isinstance(result["offset_required_tco2e"], Decimal), (
        f"AC-3: offset_required_tco2e must be a Decimal; "
        f"got {type(result['offset_required_tco2e']).__name__}: "
        f"{result['offset_required_tco2e']!r}"
    )
    expected_offset = Decimal("100") * Decimal("1.0")  # = Decimal("100.0")
    assert result["offset_required_tco2e"] == expected_offset, (
        f"AC-3: offset_required_tco2e must equal {expected_offset!r} (canonical Decimal); "
        f"got {result['offset_required_tco2e']!r}"
    )

    # ----- reduction_trajectory: list of (year, factor) tuples -----
    trajectory = result["reduction_trajectory"]
    assert isinstance(trajectory, list), (
        f"AC-3: reduction_trajectory must be a list; "
        f"got {type(trajectory).__name__}: {trajectory!r}"
    )
    # Must contain the 4 canonical (year, factor) anchor tuples per spec.yaml
    expected_tuples = [(2024, 1.0), (2026, 0.95), (2028, 0.75), (2030, 0.50)]
    for expected_tup in expected_tuples:
        assert expected_tup in trajectory, (
            f"AC-3: reduction_trajectory must contain {expected_tup!r} per spec; "
            f"got {trajectory!r}"
        )


def test_ac3_check_alignment_baseline_year_above_2030_raises_value_error() -> None:
    """AC-3 spec test_oracle — ValueError guard for baseline_year > 2030.

    Asserts that ``check_alignment(Decimal("100"), 2031)`` raises ``ValueError``
    because the Gastgeber-Klimaneutralität 2030 trajectory is only defined for
    years ≤ 2030 (per spec.yaml: "the function MUST raise ``ValueError`` if
    ``baseline_year > 2030``"). The error message MUST mention the offending
    year "2031" for diagnostic clarity.
    """
    _gastgeber_module_is_importable()
    gk_mod = _get_gastgeber_module()
    check_alignment = getattr(gk_mod, "check_alignment", None)
    assert callable(check_alignment), (
        "AC-3: gastgeber_klimaneutralitaet_2030 must expose a callable check_alignment "
        "for the ValueError guard to be testable"
    )

    # ----- invalid baseline_year=2031 (after the 2030 trajectory endpoint) -----
    with pytest.raises(ValueError) as excinfo:
        check_alignment(Decimal("100"), 2031)

    # Diagnostic message must mention "2031" for operator clarity
    err_msg = str(excinfo.value)
    assert "2031" in err_msg, (
        f"AC-3: ValueError message must name the offending baseline_year '2031'; "
        f"got {err_msg!r}"
    )


def test_ac3_check_alignment_aligned_iff_offset_zero() -> None:
    """AC-3 spec test_oracle — boundary: aligned=True when offset=0.

    Asserts that ``check_alignment(Decimal("0"), 2030)`` returns aligned=True
    because the residual offset = Decimal("0") * trajectory_factor(2030) =
    Decimal("0") * Decimal("0.5") = Decimal("0") <= 0, satisfying the
    `aligned` invariant `emissions_tco2e_annual * trajectory_factor(baseline_year) <= 0`.
    """
    _gastgeber_module_is_importable()
    gk_mod = _get_gastgeber_module()
    check_alignment = getattr(gk_mod, "check_alignment", None)
    assert callable(check_alignment), (
        "AC-3: gastgeber_klimaneutralitaet_2030 must expose a callable check_alignment "
        "for the boundary-condition assertion"
    )

    # ----- boundary args: 0 tCO2e, baseline_year=2030 (final trajectory year) -----
    result = check_alignment(Decimal("0"), 2030)

    # ----- aligned must be True (0 * 0.5 = 0 <= 0) -----
    assert result["aligned"] is True, (
        f"AC-3: aligned must be True at the zero-emissions 2030 boundary "
        f"(0 * 0.5 = 0 <= 0); got {result['aligned']!r}"
    )
    # ----- offset_required_tco2e must be Decimal("0") -----
    assert isinstance(result["offset_required_tco2e"], Decimal), (
        f"AC-3: offset_required_tco2e must be a Decimal; "
        f"got {type(result['offset_required_tco2e']).__name__}: "
        f"{result['offset_required_tco2e']!r}"
    )
    assert result["offset_required_tco2e"] == Decimal("0"), (
        f"AC-3: offset_required_tco2e must equal Decimal('0') at the zero-emissions "
        f"boundary; got {result['offset_required_tco2e']!r}"
    )


# ===========================================================================
# AC-4 — generate_heilbad_predicate_2036 returns Kurort-vertical narrative
# ===========================================================================
# Per spec.yaml AC-4 (verbatim):
#   Event-driven. When `generate_heilbad_predicate_2036()` is called in
#   `kurort_engine.esg.report.kurort_vertical_narrative` THEN the system shall
#   return a `dict` describing the Heilbad predicate 2036 ESG narrative for
#   Hotel Rheinland Bad Orb, with required keys: `predicate_label: str = "Heilbad
#   Bad Orb (Hessischer Heilbäderverband)"`, `narrative_de: str` (German narrative
#   block ≥ 200 chars mentioning Spessart Bike Tage + R3 Kinzigtal + WaldErfahren
#   + E-Bike charging + Toskana Therme partnership + thermal-spring NiedrigEnergie
#   baseline), `narrative_en: str` (English narrative block ≥ 200 chars with
#   the same six anchors for Frau Steuerberaterin Müller DATEV verification surface),
#   `lang: str = "de"`, `accessibility_label: str` (BFSG-EAA compliant
#   accessibilityLabel ≥ 20 chars per WCAG 2.1 SC 4.1.3 + EN 301 549 baseline).

# Canonical 6 anchor substrings per spec.yaml AC-4 + reference A-5
AC4_SIX_ANCHORS = (
    "Spessart Bike Tage",
    "R3 Kinzigtal",
    "WaldErfahren",
    "E-Bike charging",
    "Toskana Therme",
    "thermal-spring NiedrigEnergie",
)


def _kurort_vertical_narrative_module_is_importable() -> str:
    """Pre-check: the new esg.report.kurort_vertical_narrative module must exist (AC-4)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.kurort_vertical_narrative",
        parent="kurort_engine.esg.report.kurort_vertical_narrative",
    )


def _get_kurort_vertical_narrative_module():
    """Import the esg.report.kurort_vertical_narrative module after the find_spec guard."""
    _kurort_vertical_narrative_module_is_importable()
    import kurort_engine.esg.report.kurort_vertical_narrative as _kvn  # noqa: E402
    assert _kvn is not None, "importlib returned None — module is None"
    return _kvn


def test_ac4_generate_heilbad_predicate_2036_emits_kurort_narrative_dict() -> None:
    """AC-4 spec test_oracle — happy-path Heilbad predicate 2036 narrative.

    Asserts that ``generate_heilbad_predicate_2036()`` (no args) returns a
    JSON-serialisable dict describing the Heilbad predicate 2036 ESG narrative
    for Hotel Rheinland Bad Orb, with required keys:

      * ``predicate_label`` — str, must equal "Heilbad Bad Orb (Hessischer Heilbäderverband)"
      * ``narrative_de`` — str, German narrative block ≥ 200 chars
      * ``narrative_en`` — str, English narrative block ≥ 200 chars (DATEV verification surface)
      * ``lang`` — str, must equal "de"
      * ``accessibility_label`` — str, BFSG-EAA compliant accessibilityLabel ≥ 20 chars
        per WCAG 2.1 SC 4.1.3 + EN 301 549 baseline
    """
    _kurort_vertical_narrative_module_is_importable()
    kvn_mod = _get_kurort_vertical_narrative_module()

    # Function must be exposed under the canonical name (no rename allowed).
    generate_heilbad_predicate_2036 = getattr(kvn_mod, "generate_heilbad_predicate_2036", None)
    assert callable(generate_heilbad_predicate_2036), (
        "AC-4: kurort_vertical_narrative must expose a callable "
        f"generate_heilbad_predicate_2036 entry point; "
        f"found: {[n for n in dir(kvn_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path: call with no args (factory-style ESG narrative builder) -----
    result = generate_heilbad_predicate_2036()

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-4: generate_heilbad_predicate_2036 must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-4: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (5 required keys) -----
    required_keys = [
        "predicate_label",
        "narrative_de",
        "narrative_en",
        "lang",
        "accessibility_label",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-4: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- predicate_label: str exact match -----
    assert result["predicate_label"] == "Heilbad Bad Orb (Hessischer Heilbäderverband)", (
        f"AC-4: predicate_label must equal 'Heilbad Bad Orb (Hessischer Heilbäderverband)'; "
        f"got {result['predicate_label']!r}"
    )

    # ----- narrative_de: German block ≥ 200 chars -----
    assert isinstance(result["narrative_de"], str), (
        f"AC-4: narrative_de must be a str; "
        f"got {type(result['narrative_de']).__name__}: {result['narrative_de']!r}"
    )
    assert len(result["narrative_de"]) >= 200, (
        f"AC-4: narrative_de must be ≥ 200 chars (per spec.yaml EARS); "
        f"got length {len(result['narrative_de'])}: {result['narrative_de'][:80]!r}..."
    )

    # ----- narrative_en: English block ≥ 200 chars (DATEV verification surface) -----
    assert isinstance(result["narrative_en"], str), (
        f"AC-4: narrative_en must be a str; "
        f"got {type(result['narrative_en']).__name__}: {result['narrative_en']!r}"
    )
    assert len(result["narrative_en"]) >= 200, (
        f"AC-4: narrative_en must be ≥ 200 chars (DATEV verification surface); "
        f"got length {len(result['narrative_en'])}: {result['narrative_en'][:80]!r}..."
    )

    # ----- lang: str, exact match "de" (BFSG-EAA primary language) -----
    assert result["lang"] == "de", (
        f"AC-4: lang must equal 'de' (BFSG-EAA primary language); "
        f"got {result['lang']!r}"
    )

    # ----- accessibility_label: BFSG-EAA compliant ≥ 20 chars -----
    assert isinstance(result["accessibility_label"], str), (
        f"AC-4: accessibility_label must be a str; "
        f"got {type(result['accessibility_label']).__name__}: "
        f"{result['accessibility_label']!r}"
    )
    assert len(result["accessibility_label"]) >= 20, (
        f"AC-4: accessibility_label must be ≥ 20 chars per WCAG 2.1 SC 4.1.3 "
        f"+ EN 301 549 baseline; got length {len(result['accessibility_label'])}: "
        f"{result['accessibility_label']!r}"
    )


def test_ac4_generate_heilbad_predicate_2036_six_anchors_in_narratives() -> None:
    """AC-4 spec test_oracle — 6-anchor substring coverage in narrative_de + narrative_en.

    Asserts that BOTH ``narrative_de`` AND ``narrative_en`` from
    ``generate_heilbad_predicate_2036()`` contain all 6 canonical Kurort-vertical
    anchor substrings per spec.yaml §12 + reference A-5:

      1. "Spessart Bike Tage"           — Spessart Bike Tage seasonal outdoor event
      2. "R3 Kinzigtal"                  — R3 Kinzigtalradweg cycling route waypoint
      3. "WaldErfahren"                  — WaldErfahren forest experience programme
      4. "E-Bike charging"               — iter-24 Q5.2 E-Bike charging station integration
      5. "Toskana Therme"                — Toskana Therme partnership Kur-thermal cross-sell
      6. "thermal-spring NiedrigEnergie" — Scope 1 thermal-spring NiedrigEnergie baseline

    Total: 12 substring assertions (6 anchors × 2 narratives). No mock — pure
    string containment per iter-27 honest-RED discipline (no mocking the UUT).
    """
    _kurort_vertical_narrative_module_is_importable()
    kvn_mod = _get_kurort_vertical_narrative_module()
    generate_heilbad_predicate_2036 = getattr(kvn_mod, "generate_heilbad_predicate_2036", None)
    assert callable(generate_heilbad_predicate_2036), (
        "AC-4: kurort_vertical_narrative must expose a callable "
        "generate_heilbad_predicate_2036 for the 6-anchor assertion to be testable"
    )

    result = generate_heilbad_predicate_2036()
    narrative_de = result.get("narrative_de", "")
    narrative_en = result.get("narrative_en", "")

    # ----- 12 substring assertions: 6 anchors × 2 narratives -----
    for anchor in AC4_SIX_ANCHORS:
        assert anchor in narrative_de, (
            f"AC-4: German narrative_de must contain anchor '{anchor}' "
            f"(spec.yaml §12 Kurort-vertical anchor); "
            f"got narrative_de[:120]={narrative_de[:120]!r}"
        )
        assert anchor in narrative_en, (
            f"AC-4: English narrative_en must contain anchor '{anchor}' "
            f"(DATEV verification surface per spec.yaml §12 Kurort-vertical anchor); "
            f"got narrative_en[:120]={narrative_en[:120]!r}"
        )


# ===========================================================================
# AC-5 — export_lang_de_accessibilitylabel BFSG-AA ESG disclosure
# ===========================================================================
# Per spec.yaml AC-5 (verbatim):
#   Unwanted-behavior. If `export_lang_de_accessibilitylabel(disclosure_payload)`
#   is called in `kurort_engine.esg.report.bfsg_aa_esg_disclosure` THEN the
#   function MUST raise `BFSGComplianceError` (re-using the SHIPPED
#   `kurort_engine.kurkarte_wallet.BFSGComplianceError` exception class
#   introduced in iter-21) naming the missing field if any field of
#   `disclosure_payload` lacks `lang="de"` (per BFSG-EAA in force
#   28.06.2025) or lacks `accessibility_label` (per WCAG 2.1 SC 4.1.3 + EN 301 549
#   baseline); the disclosure payload MUST include screen-reader text contrast
#   ≥ 4.5:1 metadata declared at the document level (`formatVersion` +
#   `badOrbEsgDisclosureStyle`); a `compliance_ok: bool` field at the dict
#   top-level MUST be `True` iff all sub-fields pass the BFSG check.

def _bfsg_aa_esg_disclosure_module_is_importable() -> str:
    """Pre-check: the new esg.report.bfsg_aa_esg_disclosure module must exist (AC-5)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.bfsg_aa_esg_disclosure",
        parent="kurort_engine.esg.report.bfsg_aa_esg_disclosure",
    )


def _get_bfsg_aa_esg_disclosure_module():
    """Import the esg.report.bfsg_aa_esg_disclosure module after the find_spec guard."""
    _bfsg_aa_esg_disclosure_module_is_importable()
    import kurort_engine.esg.report.bfsg_aa_esg_disclosure as _baa  # noqa: E402
    assert _baa is not None, "importlib returned None — module is None"
    return _baa


def test_ac5_bfsg_aa_esg_disclosure_compliance_ok_true_when_payload_valid() -> None:
    """AC-5 spec test_oracle — happy-path BFSG-AA ESG disclosure returns compliance_ok=True.

    Asserts that ``export_lang_de_accessibilitylabel(valid_payload)`` returns a
    JSON-serialisable dict with ``compliance_ok: bool = True`` at the top level
    when the disclosure payload contains:

      * document-level metadata: ``formatVersion: str = "1.0"`` + ``badOrbEsgDisclosureStyle``
        dict with ``textContrastRatio: str = "4.5:1"`` + ``minFontSizePt: int = 12``
        (screen-reader text contrast ≥ 4.5:1 per WCAG 2.1 SC 1.4.3)
      * all sub-fields pass BFSG-EAA check: ``lang: str = "de"`` +
        ``accessibility_label: str`` ≥ 20 chars (BFSG-EAA + WCAG 2.1 SC 4.1.3)
    """
    _bfsg_aa_esg_disclosure_module_is_importable()
    baa_mod = _get_bfsg_aa_esg_disclosure_module()

    # Function must be exposed under the canonical name (no rename allowed).
    export_lang_de_accessibilitylabel = getattr(baa_mod, "export_lang_de_accessibilitylabel", None)
    assert callable(export_lang_de_accessibilitylabel), (
        "AC-5: bfsg_aa_esg_disclosure must expose a callable "
        f"export_lang_de_accessibilitylabel entry point; "
        f"found: {[n for n in dir(baa_mod) if not n.startswith('_')]!r}"
    )

    # ----- valid payload: formatVersion + badOrbEsgDisclosureStyle + 1 BFSG-compliant field -----
    valid_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {
            "textContrastRatio": "4.5:1",
            "minFontSizePt": 12,
        },
        "field1": {
            "lang": "de",
            "accessibility_label": "ESG-Bericht Hotel Rheinland 2026 Heilbad 2030",
        },
    }
    result = export_lang_de_accessibilitylabel(valid_payload)

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-5: export_lang_de_accessibilitylabel must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-5: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- compliance_ok: bool = True at top level (per spec.yaml EARS) -----
    assert "compliance_ok" in result, (
        f"AC-5: missing required top-level key 'compliance_ok'; "
        f"got {sorted(result.keys())!r}"
    )
    assert isinstance(result["compliance_ok"], bool), (
        f"AC-5: compliance_ok must be a bool; "
        f"got {type(result['compliance_ok']).__name__}: {result['compliance_ok']!r}"
    )
    assert result["compliance_ok"] is True, (
        f"AC-5: compliance_ok must be True for a valid BFSG-AA disclosure payload; "
        f"got {result['compliance_ok']!r}"
    )


def test_ac5_bfsg_aa_esg_disclosure_missing_accessibility_label_raises_bfsg_error() -> None:
    """AC-5 spec test_oracle — missing accessibility_label raises BFSGComplianceError.

    Asserts that ``export_lang_de_accessibilitylabel(payload)`` raises
    ``BFSGComplianceError`` (per iter-21 ``kurort_engine.kurkarte_wallet`` exception
    class) when a sub-field lacks the ``accessibility_label`` key (WCAG 2.1
    SC 4.1.3 + EN 301 549 baseline violation). The exception message MUST
    name the missing field for diagnostic clarity (per BFSGComplianceError
    docstring contract).
    """
    _bfsg_aa_esg_disclosure_module_is_importable()
    baa_mod = _get_bfsg_aa_esg_disclosure_module()
    export_lang_de_accessibilitylabel = getattr(baa_mod, "export_lang_de_accessibilitylabel", None)
    assert callable(export_lang_de_accessibilitylabel), (
        "AC-5: bfsg_aa_esg_disclosure must expose a callable "
        "export_lang_de_accessibilitylabel for the BFSGComplianceError guard to be testable"
    )

    # ----- bad payload: sub-field has lang="de" but NO accessibility_label key -----
    bad_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {"textContrastRatio": "4.5:1", "minFontSizePt": 12},
        "field1": {"lang": "de"},  # MISSING accessibility_label
    }

    # BFSGComplianceError is a ValueError subclass — importable from iter-21 kurkarte_wallet
    from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_lang_de_accessibilitylabel(bad_payload)

    # Exception message must name the missing field "accessibility_label" for diagnostic clarity
    err_msg = str(excinfo.value)
    assert "accessibility_label" in err_msg, (
        f"AC-5: BFSGComplianceError message must name the missing field "
        f"'accessibility_label' (per kurort_engine.kurkarte_wallet docstring contract); "
        f"got {err_msg!r}"
    )


def test_ac5_bfsg_aa_esg_disclosure_lang_not_de_raises_bfsg_error() -> None:
    """AC-5 spec test_oracle — lang != 'de' raises BFSGComplianceError.

    Asserts that ``export_lang_de_accessibilitylabel(payload)`` raises
    ``BFSGComplianceError`` (per iter-21 ``kurort_engine.kurkarte_wallet`` exception
    class) when a sub-field has ``lang != "de"`` (BFSG-EAA violation per
    Barrierefreiheitsstärkungsgesetz in force 28.06.2025). The exception
    message MUST name the offending field for diagnostic clarity.
    """
    _bfsg_aa_esg_disclosure_module_is_importable()
    baa_mod = _get_bfsg_aa_esg_disclosure_module()
    export_lang_de_accessibilitylabel = getattr(baa_mod, "export_lang_de_accessibilitylabel", None)
    assert callable(export_lang_de_accessibilitylabel), (
        "AC-5: bfsg_aa_esg_disclosure must expose a callable "
        "export_lang_de_accessibilitylabel for the lang-not-de guard to be testable"
    )

    # ----- bad payload: sub-field has lang="en" + accessibility_label ≥ 20 chars -----
    # (accessibility_label is valid, lang is the offending field)
    bad_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {"textContrastRatio": "4.5:1", "minFontSizePt": 12},
        "field1": {
            "lang": "en",  # WRONG — must be "de"
            "accessibility_label": "x" * 25,  # ≥ 20 chars is fine, lang is the issue
        },
    }

    from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_lang_de_accessibilitylabel(bad_payload)

    # Exception message must name the offending "lang" field for diagnostic clarity
    err_msg = str(excinfo.value)
    assert "lang" in err_msg, (
        f"AC-5: BFSGComplianceError message must name the offending field "
        f"'lang' (per BFSG-EAA in force 28.06.2025 contract); "
        f"got {err_msg!r}"
    )
