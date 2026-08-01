"""Iter-30 Phase 3 RED tests — kurort_engine.esg.report HCMI Scope 1+2 EXTENSION (AC-1).

Iter-30 (Developer) — Pattern F chain-extension of iter-27 SHIPPED Q5.1 ESG.
Chosen by iter-29 Critic verdict (see `iter-29-critic-verdict-choose-iter-28-proposal-002-hcmi-scope-12-extension-as-it`)
from iter-28 Scholar Proposal 002 (Axis B HCMI Scope 1+2 EXTENSION).

AC-1 contract (verbatim from spec.yaml PROTECTED block):

    Ubiquitous. The system shall expose a
    `calculate_scope_1(heating_kwh_annual, refrigeration_kwh_annual)` function
    in `kurort_engine.esg.report.hcmi_scope1_2_calculator` that, when given
    annual heating kWh (Decimal, >= 0) and refrigeration kWh (Decimal, >= 0),
    returns a JSON-serializable `dict` per the Sustainable Hospitality
    Alliance (SHA) HCMI methodology (30,000+ hotels globally use HCMI;
    2025/2026 baseline) with required keys: `heating_tco2e: Decimal`
    (Scope 1 direct heating emissions via the Toskana Therme partnership
    thermal-spring NiedrigEnergie baseline 0.05 kg CO2e/kWh, computed by
    re-using the SHIPPED iter-27 `scope1_heating_thermal_spring_emissions()`
    function as the canonical anchor), `refrigeration_tco2e: Decimal`
    (HCMI 2025/2026 baseline refrigeration factor 0.15 kg CO2e/kWh),
    `total_scope1_tco2e: Decimal` (heating + refrigeration sum);
    the function MUST raise `ValueError` if any argument is negative;
    the module docstring MUST cite "Sustainable Hospitality Alliance (SHA)
    HCMI methodology" as the canonical reference per Subagent-B KEPT-2
    forced-flaw mitigation.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check (wrapped in try/except) so
missing-module failures surface as ``AssertionError`` ("module should exist"),
not ``ModuleNotFoundError``.

Per `iter-30-pinned-tdd-rules-hcmi-scope-12-extension-tdd-discipline-5-shas-ant`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete Decimal string-form arithmetic for emission factors (no float drift)
  * Concrete `pytest.raises(ValueError)` guard for the invalid-input assertion
  * Concrete JSON-serialisability round-trip via `json.dumps(result, default=str)`
  * SHA methodology citation in module docstring (RED-5)
"""
from __future__ import annotations

import importlib.util
import json
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
    with ``AssertionError``, not ``ImportError`` / ``ModuleNotFoundError` /
    `SyntaxError``.
    """
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ImportError) as exc:
        scope = parent or module_name
        raise AssertionError(
            f"{scope} is not importable - green phase must create the "
            f"module before this test can pass. find_spec raised: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    assert found is not None, (
        f"{module_name} is not importable - green phase must create the "
        f"module before this test can pass. find_spec returned: {found!r}"
    )
    return f"found at {found.origin if hasattr(found, 'origin') else '<namespace>'}"


def _esg_report_package_is_importable() -> str:
    """Pre-check: the existing esg.report package must exist (SHIPPED iter-27)."""
    return _find_spec_or_assert("kurort_engine.esg.report")


def _hcmi_scope1_2_calculator_module_is_importable() -> str:
    """Pre-check: the new esg.report.hcmi_scope1_2_calculator module must exist (AC-1+AC-2+AC-3)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.hcmi_scope1_2_calculator",
        parent="kurort_engine.esg.report.hcmi_scope1_2_calculator",
    )


def _get_hcmi_scope1_2_calculator_module():
    """Import the esg.report.hcmi_scope1_2_calculator module after the find_spec guard."""
    _hcmi_scope1_2_calculator_module_is_importable()
    import kurort_engine.esg.report.hcmi_scope1_2_calculator as _h12c  # noqa: E402
    assert _h12c is not None, "importlib returned None - module is None"
    return _h12c


def _get_esg_report_package():
    """Import the esg.report package after the find_spec guard."""
    _esg_report_package_is_importable()
    import kurort_engine.esg.report as _rpt  # noqa: E402
    assert _rpt is not None, "importlib returned None - package is None"
    return _rpt


# ===========================================================================
# AC-1 + RED-5 — calculate_scope_1 emits HCMI Scope 1 dict
# ===========================================================================

def test_ac1_calculate_scope_1_emits_hcmi_scope_1_dict() -> None:
    """AC-1 spec test_oracle - happy-path HCMI Scope 1 calculation.

    Asserts that ``calculate_scope_1(Decimal("10000"), Decimal("2000"))``
    returns a JSON-serializable dict per the Sustainable Hospitality Alliance
    (SHA) HCMI methodology with required keys:
      * ``heating_tco2e`` - Decimal == Decimal("10000") * Decimal("0.05")
        (Toskana Therme thermal-spring NiedrigEnergie baseline 0.05 kg CO2e/kWh)
      * ``refrigeration_tco2e`` - Decimal == Decimal("2000") * Decimal("0.15")
        (HCMI 2025/2026 baseline refrigeration factor 0.15 kg CO2e/kWh)
      * ``total_scope1_tco2e`` - Decimal == heating_tco2e + refrigeration_tco2e
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    # ----- RED-5 docstring assertion: SHA methodology citation REQUIRED -----
    module_doc = h12c_mod.__doc__ or ""
    assert "Sustainable Hospitality Alliance (SHA) HCMI methodology" in module_doc, (
        f"AC-1 RED-5: hcmi_scope1_2_calculator module docstring MUST cite "
        f"'Sustainable Hospitality Alliance (SHA) HCMI methodology' as the "
        f"canonical reference per Subagent-B KEPT-2 forced-flaw mitigation; "
        f"got module_doc[:200]={module_doc[:200]!r}"
    )

    # ----- Function must be exposed under the canonical name (no rename allowed) -----
    calculate_scope_1 = getattr(h12c_mod, "calculate_scope_1", None)
    assert callable(calculate_scope_1), (
        "AC-1: hcmi_scope1_2_calculator must expose a callable calculate_scope_1 "
        f"entry point; found: {[n for n in dir(h12c_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: hotel-scale HCMI Scope 1 envelope -----
    heating_kwh = Decimal("10000")        # 10,000 kWh heating (33-room hotel envelope)
    refrigeration_kwh = Decimal("2000")   # 2,000 kWh refrigeration (kitchen cold storage)
    result = calculate_scope_1(heating_kwh, refrigeration_kwh)

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-1: calculate_scope_1 must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip (default=str handles Decimal) -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-1: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (3 required keys) -----
    required_keys = ["heating_tco2e", "refrigeration_tco2e", "total_scope1_tco2e"]
    for key in required_keys:
        assert key in result, (
            f"AC-1: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- expected emissions via canonical Decimal string-form arithmetic -----
    expected_heating = Decimal("10000") * Decimal("0.05")    # = Decimal("500.000")
    expected_refrigeration = Decimal("2000") * Decimal("0.15")  # = Decimal("300.000")
    expected_total = expected_heating + expected_refrigeration  # = Decimal("800.000")

    # ----- Decimal-type + exact-equality assertions -----
    for key, expected in [
        ("heating_tco2e", expected_heating),
        ("refrigeration_tco2e", expected_refrigeration),
        ("total_scope1_tco2e", expected_total),
    ]:
        assert isinstance(result[key], Decimal), (
            f"AC-1: {key} must be a Decimal; "
            f"got {type(result[key]).__name__}: {result[key]!r}"
        )
        assert result[key] == expected, (
            f"AC-1: {key} must equal {expected!r} (canonical Decimal arithmetic); "
            f"got {result[key]!r}"
        )


def test_ac1_calculate_scope_1_negative_input_raises_value_error() -> None:
    """AC-1 spec test_oracle - ValueError guard for negative input.

    Asserts that ``calculate_scope_1(Decimal("-1"), Decimal("0"))`` raises
    ``ValueError`` because ``heating_kwh_annual < 0`` (negative emissions
    data is invalid).
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    calculate_scope_1 = getattr(h12c_mod, "calculate_scope_1", None)
    assert callable(calculate_scope_1), (
        "AC-1: hcmi_scope1_2_calculator must expose a callable calculate_scope_1 "
        "for the ValueError guard to be testable"
    )

    # ----- negative heating input: must raise ValueError -----
    with pytest.raises(ValueError):
        calculate_scope_1(Decimal("-1"), Decimal("0"))


def test_ac1_hcmi_scope1_2_calculator_module_docstring_cites_sha_methodology() -> None:
    """AC-1 + RED-5 standalone docstring assertion.

    Asserts that the ``kurort_engine.esg.report.hcmi_scope1_2_calculator``
    module docstring explicitly cites 'Sustainable Hospitality Alliance (SHA)
    HCMI methodology' as the canonical reference per Subagent-B KEPT-2
    forced-flaw mitigation. This is the RED-5 mandatory test per
    `iter-29-critic-verdict-choose-iter-28-proposal-002-hcmi-scope-12-extension-as-it` §11.
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    # ----- The module docstring (or its file source) must contain SHA citation -----
    module_doc = h12c_mod.__doc__ or ""
    sha_citation = "Sustainable Hospitality Alliance (SHA) HCMI methodology"
    assert sha_citation in module_doc, (
        f"AC-1 RED-5: kurort_engine.esg.report.hcmi_scope1_2_calculator module "
        f"docstring MUST cite '{sha_citation}' as the canonical reference "
        f"per Subagent-B KEPT-2 forced-flaw mitigation; "
        f"got module_doc (length {len(module_doc)})[:500]={module_doc[:500]!r}"
    )


# ===========================================================================
# AC-1 re-export surface (kurort_engine.esg.report package must re-export
# calculate_scope_1 via the namespace per verdict §11)
# ===========================================================================

def test_ac1_kurort_engine_esg_report_reexports_calculate_scope_1() -> None:
    """AC-1 spec test_oracle - public API re-export.

    Asserts that ``calculate_scope_1`` is importable from the canonical
    ``kurort_engine.esg.report`` namespace (per verdict §11 public API
    surface contract).
    """
    _esg_report_package_is_importable()
    rpt_mod = _get_esg_report_package()

    # Function must be re-exported under the canonical name.
    calculate_scope_1 = getattr(rpt_mod, "calculate_scope_1", None)
    assert callable(calculate_scope_1), (
        "AC-1: kurort_engine.esg.report must re-export a callable "
        f"calculate_scope_1 entry point; found: "
        f"{[n for n in dir(rpt_mod) if not n.startswith('_')]!r}"
    )


# ===========================================================================
# AC-2 + RED-3 — calculate_scope_2 green_electricity_contract parameter
# ===========================================================================

def test_ac2_calculate_scope_2_green_contract_param_selects_factor() -> None:
    """AC-2 spec test_oracle - happy-path HCMI Scope 2 with green_contract parameter.

    Asserts that ``calculate_scope_2(purchased_electricity_kwh_annual,
    green_electricity_contract: bool)`` returns a JSON-serializable dict per
    the HCMI methodology with required keys (3 keys: grid_tco2e,
    green_electricity_tco2e, total_scope2_tco2e).

    RED-3 verbatim test_oracle (per Subagent-B KEPT-2 forced-flaw mitigation):
      * ``calculate_scope_2(Decimal("1000"), True)["total_scope2_tco2e"]`` MUST
        equal ``Decimal("1000") * Decimal("0.02")`` (= Decimal("20.000");
        OK Lab certified-green electricity factor 0.02 kg CO2e/kWh)
      * ``calculate_scope_2(Decimal("1000"), False)["total_scope2_tco2e"]`` MUST
        equal ``Decimal("1000") * Decimal("0.42")`` (= Decimal("420.000");
        DE Strommix 2026 grid factor 0.42 kg CO2e/kWh)
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    # ----- Function must be exposed under the canonical name -----
    calculate_scope_2 = getattr(h12c_mod, "calculate_scope_2", None)
    assert callable(calculate_scope_2), (
        "AC-2: hcmi_scope1_2_calculator must expose a callable calculate_scope_2 "
        f"entry point; found: {[n for n in dir(h12c_mod) if not n.startswith('_')]!r}"
    )

    # ----- RED-3 boundary case 1: green_electricity_contract=True -----
    purchased_kwh = Decimal("1000")
    result_green = calculate_scope_2(purchased_kwh, True)

    # ----- return-type check for green=True case -----
    assert isinstance(result_green, dict), (
        f"AC-2: calculate_scope_2 must return a JSON-serialisable dict; "
        f"got {type(result_green).__name__}: {result_green!r}"
    )

    # ----- RED-3 verbatim assertion: green=True MUST use OK Lab 0.02 factor -----
    expected_green_tco2e = Decimal("1000") * Decimal("0.02")  # = Decimal("20.000")
    assert result_green["total_scope2_tco2e"] == expected_green_tco2e, (
        f"AC-2 RED-3: calculate_scope_2(Decimal('1000'), True)['total_scope2_tco2e'] "
        f"must equal Decimal('1000') * Decimal('0.02') == {expected_green_tco2e!r} "
        f"(OK Lab certified-green 0.02 kg CO2e/kWh); "
        f"got {result_green['total_scope2_tco2e']!r}. Per Subagent-B KEPT-2 "
        f"forced-flaw mitigation, the green_contract=True branch MUST select "
        f"the OK Lab factor (NOT the DE Strommix grid 0.42 factor)."
    )

    # ----- structural key assertions for green=True case -----
    required_keys = ["grid_tco2e", "green_electricity_tco2e", "total_scope2_tco2e"]
    for key in required_keys:
        assert key in result_green, (
            f"AC-2: missing required key '{key}' in green=True case; "
            f"got {sorted(result_green.keys())!r}"
        )

    # ----- JSON-serialisability round-trip -----
    serialised_green = json.dumps(result_green, default=str)
    assert isinstance(serialised_green, str) and len(serialised_green) > 0, (
        f"AC-2: result_green must be JSON-serialisable; json.dumps returned "
        f"{type(serialised_green).__name__} of length {len(serialised_green)}"
    )

    # ----- Decimal-type + exact-equality assertions for green=True case -----
    for key, expected in [
        ("grid_tco2e", Decimal("1000") * Decimal("0.42")),
        ("green_electricity_tco2e", expected_green_tco2e),
        ("total_scope2_tco2e", expected_green_tco2e),
    ]:
        assert isinstance(result_green[key], Decimal), (
            f"AC-2 (green=True): {key} must be a Decimal; "
            f"got {type(result_green[key]).__name__}: {result_green[key]!r}"
        )
        assert result_green[key] == expected, (
            f"AC-2 (green=True): {key} must equal {expected!r} (canonical Decimal); "
            f"got {result_green[key]!r}"
        )

    # ----- RED-3 boundary case 2: green_electricity_contract=False -----
    result_grid = calculate_scope_2(purchased_kwh, False)

    # ----- return-type check for green=False case -----
    assert isinstance(result_grid, dict), (
        f"AC-2: calculate_scope_2 must return a JSON-serialisable dict when "
        f"green_electricity_contract=False; "
        f"got {type(result_grid).__name__}: {result_grid!r}"
    )

    # ----- RED-3 verbatim assertion: green=False MUST use DE Strommix 2026 0.42 factor -----
    expected_grid_tco2e = Decimal("1000") * Decimal("0.42")  # = Decimal("420.000")
    assert result_grid["total_scope2_tco2e"] == expected_grid_tco2e, (
        f"AC-2 RED-3: calculate_scope_2(Decimal('1000'), False)['total_scope2_tco2e'] "
        f"must equal Decimal('1000') * Decimal('0.42') == {expected_grid_tco2e!r} "
        f"(DE Strommix 2026 0.42 kg CO2e/kWh); "
        f"got {result_grid['total_scope2_tco2e']!r}. Per Subagent-B KEPT-2 "
        f"forced-flaw mitigation, the green_contract=False branch MUST select "
        f"the DE Strommix grid factor."
    )

    # ----- Decimal-type + exact-equality assertions for green=False case -----
    for key, expected in [
        ("grid_tco2e", expected_grid_tco2e),
        ("green_electricity_tco2e", Decimal("1000") * Decimal("0.02")),
        ("total_scope2_tco2e", expected_grid_tco2e),
    ]:
        assert isinstance(result_grid[key], Decimal), (
            f"AC-2 (green=False): {key} must be a Decimal; "
            f"got {type(result_grid[key]).__name__}: {result_grid[key]!r}"
        )
        assert result_grid[key] == expected, (
            f"AC-2 (green=False): {key} must equal {expected!r} (canonical Decimal); "
            f"got {result_grid[key]!r}"
        )


def test_ac2_calculate_scope_2_negative_input_raises_value_error() -> None:
    """AC-2 spec test_oracle - ValueError guard for negative input.

    Asserts that ``calculate_scope_2(Decimal("-1"), False)`` raises
    ``ValueError`` because ``purchased_electricity_kwh_annual < 0``
    (negative emissions data is invalid per spec.yaml AC-2 EARS contract).
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    calculate_scope_2 = getattr(h12c_mod, "calculate_scope_2", None)
    assert callable(calculate_scope_2), (
        "AC-2: hcmi_scope1_2_calculator must expose a callable calculate_scope_2 "
        "for the ValueError guard to be testable"
    )

    # ----- negative input: must raise ValueError -----
    with pytest.raises(ValueError):
        calculate_scope_2(Decimal("-1"), False)



# ===========================================================================
# AC-3 + RED-4 — calculate_scope_1_2 unified HCMI dict
# ===========================================================================

def test_ac3_calculate_scope_1_2_emits_unified_hcmi_dict() -> None:
    """AC-3 spec test_oracle - happy-path HCMI Scope 1+2 unified calculation.

    Asserts that ``calculate_scope_1_2(heating_kwh_annual, refrigeration_kwh_annual,
    purchased_electricity_kwh_annual, green_electricity_contract: bool)`` returns
    a JSON-serializable dict composing the AC-1 Scope 1 sub-result and the
    AC-2 Scope 2 sub-result, with required keys:
      * ``scope1`` - dict (verbatim AC-1 return dict)
      * ``scope2`` - dict (verbatim AC-2 return dict)
      * ``total_scope1_2_tco2e`` - Decimal (= AC-1 total + AC-2 total)

    RED-4 mandatory assertion (per Subagent-B KEPT-2 forced-flaw mitigation):
      * ``json.dumps(result, default=str)`` round-trip succeeds (JSON-serializable)
      * Stable top-level keys (``scope1``, ``scope2``, ``total_scope1_2_tco2e``)
    """
    _hcmi_scope1_2_calculator_module_is_importable()
    h12c_mod = _get_hcmi_scope1_2_calculator_module()

    # ----- Function must be exposed under the canonical name -----
    calculate_scope_1_2 = getattr(h12c_mod, "calculate_scope_1_2", None)
    assert callable(calculate_scope_1_2), (
        "AC-3: hcmi_scope1_2_calculator must expose a callable calculate_scope_1_2 "
        f"entry point; found: {[n for n in dir(h12c_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: hotel-scale HCMI Scope 1+2 envelope (green=False for grid factor) -----
    heating_kwh = Decimal("10000")
    refrigeration_kwh = Decimal("2000")
    purchased_electricity_kwh = Decimal("1000")
    green_contract = False  # use DE Strommix 2026 grid factor 0.42
    result = calculate_scope_1_2(
        heating_kwh, refrigeration_kwh, purchased_electricity_kwh, green_contract
    )

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-3: calculate_scope_1_2 must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    # ----- RED-4 JSON-serialisability round-trip -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-3 RED-4: result must be JSON-serializable via "
        f"json.dumps(result, default=str) round-trip; got "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (3 required top-level keys) -----
    required_keys = ["scope1", "scope2", "total_scope1_2_tco2e"]
    for key in required_keys:
        assert key in result, (
            f"AC-3: missing required top-level key '{key}'; "
            f"got {sorted(result.keys())!r}"
        )

    # ----- scope1 sub-dict must contain the 3 AC-1 keys -----
    scope1 = result["scope1"]
    assert isinstance(scope1, dict), (
        f"AC-3: result['scope1'] must be a dict; "
        f"got {type(scope1).__name__}: {scope1!r}"
    )
    for scope1_key in ["heating_tco2e", "refrigeration_tco2e", "total_scope1_tco2e"]:
        assert scope1_key in scope1, (
            f"AC-3: result['scope1'] missing required key '{scope1_key}'; "
            f"got {sorted(scope1.keys())!r}"
        )

    # ----- scope2 sub-dict must contain the 3 AC-2 keys -----
    scope2 = result["scope2"]
    assert isinstance(scope2, dict), (
        f"AC-3: result['scope2'] must be a dict; "
        f"got {type(scope2).__name__}: {scope2!r}"
    )
    for scope2_key in ["grid_tco2e", "green_electricity_tco2e", "total_scope2_tco2e"]:
        assert scope2_key in scope2, (
            f"AC-3: result['scope2'] missing required key '{scope2_key}'; "
            f"got {sorted(scope2.keys())!r}"
        )

    # ----- total_scope1_2_tco2e: Decimal == AC-1 total + AC-2 total -----
    expected_scope1_total = Decimal("10000") * Decimal("0.05") + Decimal("2000") * Decimal("0.15")
    # = Decimal("800.000")
    expected_scope2_total = Decimal("1000") * Decimal("0.42")  # green=False; = Decimal("420.000")
    expected_total = expected_scope1_total + expected_scope2_total
    # = Decimal("1220.000")

    assert isinstance(result["total_scope1_2_tco2e"], Decimal), (
        f"AC-3: total_scope1_2_tco2e must be a Decimal; "
        f"got {type(result['total_scope1_2_tco2e']).__name__}: "
        f"{result['total_scope1_2_tco2e']!r}"
    )
    assert result["total_scope1_2_tco2e"] == expected_total, (
        f"AC-3: total_scope1_2_tco2e must equal {expected_total!r} "
        f"(AC-1 total {expected_scope1_total!r} + AC-2 total {expected_scope2_total!r}); "
        f"got {result['total_scope1_2_tco2e']!r}"
    )

    # ----- scope1['total_scope1_tco2e'] must equal AC-1 total -----
    assert scope1["total_scope1_tco2e"] == expected_scope1_total, (
        f"AC-3: scope1['total_scope1_tco2e'] must equal AC-1 total "
        f"{expected_scope1_total!r}; got {scope1['total_scope1_tco2e']!r}"
    )

    # ----- scope2['total_scope2_tco2e'] must equal AC-2 total (green=False) -----
    assert scope2["total_scope2_tco2e"] == expected_scope2_total, (
        f"AC-3: scope2['total_scope2_tco2e'] must equal AC-2 total "
        f"{expected_scope2_total!r} (green=False grid factor); "
        f"got {scope2['total_scope2_tco2e']!r}"
    )



# ===========================================================================
# Canonical 6 Kurort-vertical anchors (per iter-27 SHIPPED A-5 anchor set)
# ===========================================================================

HCMI_AC4_SIX_ANCHORS = (
    "Spessart Bike Tage",
    "R3 Kinzigtal",
    "WaldErfahren",
    "E-Bike charging",
    "Toskana Therme",
    "thermal-spring NiedrigEnergie",
)


def _heilbad_module_is_importable() -> str:
    """Pre-check: the new esg.report.heilbad_predicate_2036_repraedikatisierung module must exist (AC-4+AC-5)."""
    return _find_spec_or_assert(
        "kurort_engine.esg.report.heilbad_predicate_2036_repraedikatisierung",
        parent="kurort_engine.esg.report.heilbad_predicate_2036_repraedikatisierung",
    )


def _get_heilbad_module():
    """Import the heilbad_predicate_2036_repraedikatisierung module via importlib.

    Module name contains a-umlaut; use importlib.import_module to sidestep
    Python identifier limitations.
    """
    _heilbad_module_is_importable()
    import importlib as _il
    _hp36 = _il.import_module("kurort_engine.esg.report.heilbad_predicate_2036_repraedikatisierung")
    assert _hp36 is not None, "importlib returned None - module is None"
    return _hp36


# ===========================================================================
# AC-4 - generate_heilbad_2036_esg_narrative emits Heilbad 2036 Repraedikatisierung dict
# ===========================================================================

def test_ac4_generate_heilbad_2036_esg_narrative_emits_repraedikatisierung_dict() -> None:
    """AC-4 spec test_oracle - happy-path Heilbad 2036 Repraedikatisierung ESG narrative.

    Asserts that generate_heilbad_2036_esg_narrative(heating_kwh_annual,
    refrigeration_kwh_annual, purchased_electricity_kwh_annual,
    green_electricity_contract: bool) returns a JSON-serializable dict
    describing the Heilbad 2036 Repraedikatisierung ESG narrative for Hotel
    Rheinland Bad Orb, with required keys:
      * predicate_label - str == "Heilbad Bad Orb (Hessischer Heilbaederverband)"
      * narrative_de - str >= 300 chars mentioning all 6 canonical Kurort-vertical anchors
      * narrative_en - str >= 300 chars with same 6 anchors (DATEV verification surface)
      * representative_period - tuple[date, date] == (date(2036, 1, 1), date(2036, 12, 31))
      * lang - str == "de" (BFSG-EAA primary language)
      * accessibility_label - str >= 20 chars (WCAG 2.1 SC 4.1.3)
    """
    _heilbad_module_is_importable()
    hp36_mod = _get_heilbad_module()

    generate_heilbad_2036_esg_narrative = getattr(
        hp36_mod, "generate_heilbad_2036_esg_narrative", None
    )
    assert callable(generate_heilbad_2036_esg_narrative), (
        "AC-4: heilbad_predicate_2036_repraedikatisierung must expose a callable "
        f"generate_heilbad_2036_esg_narrative entry point; "
        f"found: {[n for n in dir(hp36_mod) if not n.startswith("_")]!r}"
    )

    result = generate_heilbad_2036_esg_narrative(
        Decimal("10000"), Decimal("2000"), Decimal("1000"), False
    )

    assert isinstance(result, dict), (
        f"AC-4: generate_heilbad_2036_esg_narrative must return a JSON-serialisable "
        f"dict; got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-4: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    required_keys = [
        "predicate_label",
        "narrative_de",
        "narrative_en",
        "representative_period",
        "lang",
        "accessibility_label",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-4: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    assert result["predicate_label"] == "Heilbad Bad Orb (Hessischer Heilbaederverband)", (
        f"AC-4: predicate_label must equal 'Heilbad Bad Orb (Hessischer Heilbaederverband)'; "
        f"got {result['predicate_label']!r}"
    )

    assert isinstance(result["narrative_de"], str), (
        f"AC-4: narrative_de must be a str; "
        f"got {type(result['narrative_de']).__name__}: {result['narrative_de']!r}"
    )
    assert len(result["narrative_de"]) >= 300, (
        f"AC-4: narrative_de must be >= 300 chars (per spec.yaml EARS AC-4); "
        f"got length {len(result['narrative_de'])}: {result['narrative_de'][:80]!r}..."
    )

    assert isinstance(result["narrative_en"], str), (
        f"AC-4: narrative_en must be a str; "
        f"got {type(result['narrative_en']).__name__}: {result['narrative_en']!r}"
    )
    assert len(result["narrative_en"]) >= 300, (
        f"AC-4: narrative_en must be >= 300 chars (DATEV verification surface); "
        f"got length {len(result['narrative_en'])}: {result['narrative_en'][:80]!r}..."
    )

    from datetime import date as _date
    expected_period = (_date(2036, 1, 1), _date(2036, 12, 31))
    assert result["representative_period"] == expected_period, (
        f"AC-4: representative_period must equal {expected_period!r} "
        f"(2036 Vorbereitungszeitraum); "
        f"got {result['representative_period']!r}"
    )

    assert result["lang"] == "de", (
        f"AC-4: lang must equal 'de' (BFSG-EAA primary language); "
        f"got {result['lang']!r}"
    )

    assert isinstance(result["accessibility_label"], str), (
        f"AC-4: accessibility_label must be a str; "
        f"got {type(result['accessibility_label']).__name__}: "
        f"{result['accessibility_label']!r}"
    )
    assert len(result["accessibility_label"]) >= 20, (
        f"AC-4: accessibility_label must be >= 20 chars per WCAG 2.1 SC 4.1.3 "
        f"+ EN 301 549 baseline; got length {len(result['accessibility_label'])}: "
        f"{result['accessibility_label']!r}"
    )


def test_ac4_generate_heilbad_2036_esg_narrative_six_anchors_in_both_narratives() -> None:
    """AC-4 spec test_oracle - 6-anchor substring coverage in narrative_de + narrative_en.

    Asserts that BOTH narrative_de AND narrative_en contain all 6
    canonical Kurort-vertical anchor substrings per spec.yaml A-5 + AC-4
    EARS contract. Total: 12 substring assertions (6 anchors x 2 narratives).
    """
    _heilbad_module_is_importable()
    hp36_mod = _get_heilbad_module()

    generate_heilbad_2036_esg_narrative = getattr(
        hp36_mod, "generate_heilbad_2036_esg_narrative", None
    )
    assert callable(generate_heilbad_2036_esg_narrative), (
        "AC-4: heilbad_predicate_2036_repraedikatisierung must expose a callable "
        "generate_heilbad_2036_esg_narrative for the 6-anchor assertion"
    )

    result = generate_heilbad_2036_esg_narrative(
        Decimal("10000"), Decimal("2000"), Decimal("1000"), False
    )
    narrative_de = result.get("narrative_de", "")
    narrative_en = result.get("narrative_en", "")

    for anchor in HCMI_AC4_SIX_ANCHORS:
        assert anchor in narrative_de, (
            f"AC-4: German narrative_de must contain anchor '{anchor}' "
            f"(spec.yaml A-5 Kurort-vertical anchor); "
            f"got narrative_de[:120]={narrative_de[:120]!r}"
        )
        assert anchor in narrative_en, (
            f"AC-4: English narrative_en must contain anchor '{anchor}' "
            f"(DATEV verification surface); "
            f"got narrative_en[:120]={narrative_en[:120]!r}"
        )


# ===========================================================================
# AC-5 - export_scope1_2_bfsg_aa BFSG-AA ESG disclosure with RED-1 + RED-2 footer
# ===========================================================================

def test_ac5_export_scope1_2_bfsg_aa_enforces_lang_de_and_non_affirmation_footer() -> None:
    """AC-5 spec test_oracle - happy-path BFSG-AA ESG disclosure emits compliance_ok=True
    with RED-1 verbatim non-affirmation clause + RED-2 SHA methodology citation in
    the disclosure footer.

    Asserts that export_scope1_2_bfsg_aa(valid_payload) returns a
    JSON-serialisable dict with the following:
      * compliance_ok - bool == True at top-level (per spec.yaml EARS)
      * formatVersion + badOrbEsgDisclosureStyle (screen-reader text contrast
        >= 4.5:1 metadata) passed through
      * Each sub-field has lang="de" + accessibility_label >= 20 chars
        (BFSG-EAA + WCAG 2.1 SC 4.1.3)

    RED-1 verbatim non-affirmation clause (per Subagent-B KEPT-1 mitigation).
    RED-2 SHA methodology citation (per Subagent-B KEPT-2 mitigation).
    """
    _heilbad_module_is_importable()
    hp36_mod = _get_heilbad_module()

    export_scope1_2_bfsg_aa = getattr(hp36_mod, "export_scope1_2_bfsg_aa", None)
    assert callable(export_scope1_2_bfsg_aa), (
        "AC-5: heilbad_predicate_2036_repraedikatisierung must expose a callable "
        f"export_scope1_2_bfsg_aa entry point; "
        f"found: {[n for n in dir(hp36_mod) if not n.startswith("_")]!r}"
    )

    valid_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {
            "textContrastRatio": "4.5:1",
            "minFontSizePt": 12,
        },
        "field1": {
            "lang": "de",
            "accessibility_label": "Heilbad 2036 ESG-readiness fuer Hotel Rheinland Bad Orb",
        },
    }
    result = export_scope1_2_bfsg_aa(valid_payload)

    assert isinstance(result, dict), (
        f"AC-5: export_scope1_2_bfsg_aa must return a JSON-serialisable dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-5: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

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

    # RED-1 verbatim non-affirmation clause (per Subagent-B KEPT-1 mitigation)
    RED1_VERBATIM_TEXT = (
        "This ESG disclosure is voluntary and is provided as ESG-readiness "
        "positioning for Bad Orb Heilbad 2036 Reprädikatisierung planning window; "
        "it is NOT a regulatory compliance attestation"
    )
    result_str = json.dumps(result, default=str, ensure_ascii=False)
    assert RED1_VERBATIM_TEXT in result_str, (
        f"AC-5 RED-1: export_scope1_2_bfsg_aa disclosure MUST include the "
        f"verbatim non-affirmation footer clause "
        f"(per Subagent-B KEPT-1 forced-flaw mitigation); "
        f"clause (length {len(RED1_VERBATIM_TEXT)}): "
        f"{RED1_VERBATIM_TEXT!r}; "
        f"got result_str (length {len(result_str)}) "
        f"first 300 chars: {result_str[:300]!r}"
    )

    # RED-2 SHA methodology citation (per Subagent-B KEPT-2 mitigation)
    RED2_SHA_CITATION = "Sustainable Hospitality Alliance (SHA) HCMI methodology"
    assert RED2_SHA_CITATION in result_str, (
        f"AC-5 RED-2: export_scope1_2_bfsg_aa disclosure MUST cite "
        f"'Sustainable Hospitality Alliance (SHA) HCMI methodology' "
        f"(per Subagent-B KEPT-2 forced-flaw mitigation); "
        f"got result_str (length {len(result_str)}) "
        f"first 300 chars: {result_str[:300]!r}"
    )


def test_ac5_export_scope1_2_bfsg_aa_missing_accessibility_label_raises_bfsg_error() -> None:
    """AC-5 spec test_oracle - missing accessibility_label raises BFSGComplianceError.

    Asserts that export_scope1_2_bfsg_aa(payload) raises
    BFSGComplianceError (re-using the SHIPPED iter-21
    kurort_engine.kurkarte_wallet.BFSGComplianceError exception class)
    when a sub-field lacks the accessibility_label key (WCAG 2.1
    SC 4.1.3 + EN 301 549 baseline violation).
    """
    _heilbad_module_is_importable()
    hp36_mod = _get_heilbad_module()

    export_scope1_2_bfsg_aa = getattr(hp36_mod, "export_scope1_2_bfsg_aa", None)
    assert callable(export_scope1_2_bfsg_aa), (
        "AC-5: heilbad_predicate_2036_repraedikatisierung must expose a callable "
        "export_scope1_2_bfsg_aa for the BFSGComplianceError guard to be testable"
    )

    bad_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {"textContrastRatio": "4.5:1", "minFontSizePt": 12},
        "field1": {"lang": "de"},  # MISSING accessibility_label
    }

    from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_scope1_2_bfsg_aa(bad_payload)

    err_msg = str(excinfo.value)
    assert "accessibility_label" in err_msg, (
        f"AC-5: BFSGComplianceError message must name the missing field "
        f"'accessibility_label' (per kurort_engine.kurkarte_wallet docstring contract); "
        f"got err_msg={err_msg!r}"
    )


def test_ac5_export_scope1_2_bfsg_aa_lang_not_de_raises_bfsg_error() -> None:
    """AC-5 spec test_oracle - lang != "de" raises BFSGComplianceError.

    Asserts that export_scope1_2_bfsg_aa(payload) raises BFSGComplianceError
    when a sub-field has lang != "de" (BFSG-EAA violation per
    Barrierefreiheitsstaerkungsgesetz in force 28.06.2025).
    """
    _heilbad_module_is_importable()
    hp36_mod = _get_heilbad_module()

    export_scope1_2_bfsg_aa = getattr(hp36_mod, "export_scope1_2_bfsg_aa", None)
    assert callable(export_scope1_2_bfsg_aa), (
        "AC-5: heilbad_predicate_2036_repraedikatisierung must expose a callable "
        "export_scope1_2_bfsg_aa for the lang-not-de guard to be testable"
    )

    bad_payload = {
        "formatVersion": "1.0",
        "badOrbEsgDisclosureStyle": {"textContrastRatio": "4.5:1", "minFontSizePt": 12},
        "field1": {
            "lang": "en",  # WRONG - must be "de"
            "accessibility_label": "x" * 25,  # >= 20 chars is fine; lang is the issue
        },
    }

    from kurort_engine.kurkarte_wallet import BFSGComplianceError  # noqa: E402

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_scope1_2_bfsg_aa(bad_payload)

    err_msg = str(excinfo.value)
    assert "lang" in err_msg, (
        f"AC-5: BFSGComplianceError message must name the offending "
        f"field 'lang' (per BFSG-EAA in force 28.06.2025 contract); "
        f"got err_msg={err_msg!r}"
    )
