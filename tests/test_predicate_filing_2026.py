"""Iter-36 Phase 2 RED tests — kurort_engine.predicate_filing.2026_validate +
kurort_engine.predicate_filing.2026_attestation + hessen_bad_orb_2026.yaml
(Bad Orb Kurbeitragssatzung 01.07.2026 validation — versioned profile +
re-pointed attestation template + anti-drift SHA integrity).

Iter-36 (Developer) — Pattern F chain-extension of iter-33 SHIPPED
`kurort_engine.predicate_filing` (predicate_packet_assembler +
kurgaste_health_data_aggregator + heilbad_2036_narrative_generator +
predicate_filing_export) + iter-21 SHIPPED
`kurort_engine.kurkarte_wallet.BFSGComplianceError`.

Chosen by iter-35 Critic verdict (P1 H1-NARROW-Satzung-2026 PRIMARY;
Tier-1; 9/9 Pattern D clean; 22.1/35 risk-adjusted; reversal-pattern
HARD PASS per `iter-35-critic-verdict-choose-proposal-1-h1-narrow-satzung-2026-as-iter-36-devel`).
The 5 SHAs + iter-33 SHIPPED `kurort_engine.predicate_filing` chain-extension
are preserved verbatim (anti-drift discipline; 113 baseline tests PASS at
entry on commit 29f03b6).

AC-1 contract (verbatim from spec.yaml PROTECTED block):

    Event-driven. When a fresh Bad Orb Kurbeitragssatzung 2026 PDF is
    published (or 60 days before 01.07.2026 effective), the system shall
    extract the full attestation schema (Beglaubigung clauses + new
    attestation fields) and produce `hessen_bad_orb_2026.yaml` profile
    in ≤1 minute wall-time; the extraction function shall be exposed as
    `extract_2026_satzung_schema(satzung_source: str) -> dict` in
    `kurort_engine.predicate_filing.2026_validate` returning a JSON-
    serializable dict containing `satzung_date: str = "2026-07-01"`,
    `bundesland: str = "hessen"`, `kurort: str = "bad_orb"`,
    `predicate: str = "heilbad"`, `attestation_template_id: str` (e.g.
    "bad_orb_2026_v1"), and `beglaubigung_clauses: list[dict]` (each
    dict containing `clause_id: str`, `clause_text: str`,
    `signature_required: bool`, `notarization_required: bool`,
    `effective_date: str`).

AC-2 contract:

    State-driven. While the `hessen_bad_orb_2026.yaml` profile is loaded
    via `load_2026_profile() -> dict` in
    `kurort_engine.predicate_filing.2026_validate`, the system shall
    preserve all 6 iter-33-SHIPPED attestation fields
    (`predicate_label: str`, `period: tuple[str, str]`,
    `reprdikatisierung_window: tuple[str, str]`,
    `accessibility_label: str`, `non_affirmation_footer: str`,
    `bfsg_aa_compliant: bool`) AND add ≥0 new attestation fields per the
    actual 2026 Satzung including any Beglaubigung clauses
    (signature/date/notarization patterns); the loaded profile dict
    shall contain `bundesland: str = "hessen"`, `kurort: str = "bad_orb"`,
    `predicate: str = "heilbad"`, `satzung_date: str = "2026-07-01"`,
    `attestation_template_id: str = "bad_orb_2026_v1"`,
    `beglaubigung_clauses: list[dict]`, `stale_pending: bool = False`
    (set True on Stadtverordnetenversammlung re-amendment per
    forced-flaw Weakness #3), `bands: list[dict]` (5 rate bands
    including `adult: 2.50`), and `preserves_iter33_fields: bool =
    True` (anti-drift marker).

AC-3 contract:

    Ubiquitous. The system shall expose
    `apply_2026_attestation_template(profile: dict, attestation_data:
    dict) -> dict` in
    `kurort_engine.predicate_filing.2026_attestation` that returns a
    JSON-serializable dict describing a Kurort-predicate attestation
    generated against the 2026 profile, with required keys:
    `attestation_template_id: str = "bad_orb_2026_v1"`, `satzung_date:
    str = "2026-07-01"`, `predicate_label: str = "Heilbad Bad Orb
    (Hessischer Heilbäderverband)"`, `adult_rate_applied: str = "2.50"`
    (100% precision match for the `adult` band), `beglaubigung_sealed:
    bool = True` (all Beglaubigung clauses applied), `accessibility_label:
    str` ≥ 20 chars, `non_affirmation_footer: str` containing the
    verbatim clause "This Kurort-predicate attestation is generated
    against the Bad Orb Kurbeitragssatzung 01.07.2026 and is provided
    as voluntary predicate-renewal positioning; it is NOT a regulatory
    compliance attestation".

AC-4 contract:

    Ubiquitous. The system shall expose
    `compute_anti_drift_sha(profile: dict, baseline_sha: str | None =
    None) -> str` in
    `kurort_engine.predicate_filing.2026_attestation` that returns the
    SHA-256 hex digest of a canonical JSON representation of the
    iter-33-SHIPPED `kurort_engine.predicate_filing` chain-extension
    (`assemble_predicate_packet` + `validate_kurgaste_health_data` +
    `generate_heilbad_2036_narrative` + `export_predicate_filing_bfsg_aa`
    + `aggregate_kurgaste_health_data`); the function shall return
    `baseline_sha` unchanged if provided AND a NEW SHA-256 if the
    iter-33 SHIPPED modules are unmodified; the function shall raise
    `kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-used from
    SHIPPED iter-21) if the iter-33 SHIPPED chain-extension has drifted
    (i.e. the computed SHA does not match `baseline_sha` when one is
    provided); the system shall NOT modify any of the 6 SHIPPED modules
    when computing the SHA.

AC-5 contract:

    Ubiquitous. The system shall pass 113 (iter-33 SHIPPED baseline) +
    5 (iter-36 NEW) = 118/118 tests when running `PYTHONPATH=src
    .venv/bin/pytest tests/ -q --override-ini="addopts=--tb=line"`; the
    5 NEW tests (`test_ac1..test_ac5`) shall pass; the 113 baseline
    tests shall pass without modification; the test suite shall exit
    code 0; the test suite shall report 0 failed and 0 error; the test
    suite shall be runnable from the workspace root via the exact
    command above.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check (wrapped in try/except) so
missing-module failures surface as ``AssertionError`` ("module should exist"),
not ``ModuleNotFoundError``.

Per `iter-36-developer-pinned-rules-p1-h1-narrow-satzung-2026-tdd-discipline-forbidde`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete ISO date string-form assertions (no datetime arithmetic drift)
  * Concrete ``pytest.raises(BFSGComplianceError)`` guards for AC-4 anti-drift
  * Chain-extension to SHIPPED modules is exercised via real imports
    (NOT mocked) — confirms the 5 SHAs + iter-33 SHIPPED
    `predicate_filing` are importable
  * All 5 SHAs + iter-33 SHIPPED `predicate_filing` MUST remain verbatim
    UNCHANGED
"""
from __future__ import annotations

import importlib.util
import json
import re
import time

import pytest


# ===========================================================================
# Module-importability helpers (per iter-33 honest-RED pattern)
# ===========================================================================

def _find_spec_or_assert(module_name: str, *, parent: str | None = None) -> str:
    """Run ``importlib.util.find_spec`` and coerce missing-module failures
    into ``AssertionError`` so the test surfaces a "spec unmet" failure
    rather than a ``ModuleNotFoundError`` import failure.

    Per pinned rule 3 (RED verification protocol): red-phase tests must fail
    with ``AssertionError``, not ``ImportError`` / ``ModuleNotFoundError` /
    `SyntaxError`.
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


# Pre-check helpers — convert missing-module failures to AssertionError
def _predicate_filing_package_is_importable() -> str:
    """Pre-check: the iter-33 SHIPPED predicate_filing package must exist."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing",
        parent="kurort_engine.predicate_filing",
    )


def _predicate_filing_2026_validate_module_is_importable() -> str:
    """Pre-check: NEW 2026_validate module must exist (AC-1, AC-2)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.2026_validate",
        parent="kurort_engine.predicate_filing.2026_validate",
    )


def _predicate_filing_2026_attestation_module_is_importable() -> str:
    """Pre-check: NEW 2026_attestation module must exist (AC-3, AC-4)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.2026_attestation",
        parent="kurort_engine.predicate_filing.2026_attestation",
    )


def _hessen_bad_orb_2026_profile_yaml_exists() -> str:
    """Pre-check: NEW hessen_bad_orb_2026.yaml profile must exist on disk."""
    import os

    candidate_paths = [
        "src/kurort_engine/profiles/hessen_bad_orb_2026.yaml",
        "repo/src/kurort_engine/profiles/hessen_bad_orb_2026.yaml",
    ]
    found_paths = [p for p in candidate_paths if os.path.isfile(p)]
    assert found_paths, (
        "AC-2 pre-check: hessen_bad_orb_2026.yaml profile MUST be created in "
        "kurort_engine/profiles/ before this test can pass. Checked paths: "
        f"{candidate_paths!r}"
    )
    return f"found at {found_paths[0]}"


# SHIPPED modules anti-drift helpers (must remain importable in iter-36 GREEN)
def _kurkarte_wallet_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.kurkarte_wallet")


def _predicate_filing_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.predicate_filing")


def _esg_report_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.esg.report")


def _spa_wellness_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.spa_wellness")


def _ev_charging_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.ev_charging")


# Import helpers (after find_spec guard)
def _get_2026_validate_module():
    _predicate_filing_2026_validate_module_is_importable()
    _mod = __import__("kurort_engine.predicate_filing.2026_validate", fromlist=["_dummy_"])  # noqa: E402
    # Python does not allow digit-prefixed identifiers in direct import statements;
    # __import__() with fromlist is the canonical workaround (used per iter-33 spec.yaml spec).
    assert _mod is not None
    return _mod


def _get_2026_attestation_module():
    _predicate_filing_2026_attestation_module_is_importable()
    _mod = __import__("kurort_engine.predicate_filing.2026_attestation", fromlist=["_dummy_"])  # noqa: E402
    # Python does not allow digit-prefixed identifiers in direct import statements;
    # __import__() with fromlist is the canonical workaround (used per iter-33 spec.yaml spec).
    assert _mod is not None
    return _mod


# ===========================================================================
# Synthetic 2026 Satzung fixture (schema-agnostic; NOT a real PDF parse)
# ===========================================================================

_SYNTHETIC_2026_SATZUNG_SOURCE = """
# Synthetic Bad Orb Kurbeitragssatzung 01.07.2026 source for iter-36 RED tests.
# Per NI-1 + spec.yaml A-3: the test target is the versioned profile layer
# (synthetic schema fixture), NOT real PDF parsing.
Satzung: Kurbeitragssatzung der Stadt Bad Orb (Hessen)
Effective: 2026-07-01
Published: 2026-03-06 by Bad Orb Stadtverordnetenversammlung
Predicates: Heilbad
Bundeland: Hessen
Kurort: Bad Orb
Beglaubigung:
  - clause_id: BG-2026-001
    clause_text: "Der Beitragsgläubiger (Hotel Rheinland) hat die ordnungsgemäße Erhebung des Kurbeitrags zu bestätigen."
    signature_required: True
    notarization_required: False
    effective_date: 2026-07-01
  - clause_id: BG-2026-002
    clause_text: "Die Beglaubigung der Meldescheine erfolgt durch den Beitragsgläubiger mit Unterschrift und Datum."
    signature_required: True
    notarization_required: True
    effective_date: 2026-07-01
Bands:
  - name: adult
    rate_eur: "2.50"
  - name: adult_disabled_70
    rate_eur: "1.25"
  - name: youth
    rate_eur: "1.00"
  - name: youth_disabled_70
    rate_eur: "0.50"
  - name: child
    rate_eur: "0.00"
"""


# ===========================================================================
# AC-1 — extract_2026_satzung_schema produces hessen_bad_orb_2026 profile
# ===========================================================================

def test_ac1_extract_2026_satzung_schema_produces_hessen_bad_orb_2026_profile() -> None:
    """AC-1 spec test_oracle - happy-path: schema extract produces 2026 profile.

    Asserts that ``extract_2026_satzung_schema(satzung_source: str) -> dict``
    returns a JSON-serializable dict with required keys:
      * ``satzung_date: str == "2026-07-01"``
      * ``bundesland: str == "hessen"``
      * ``kurort: str == "bad_orb"``
      * ``predicate: str == "heilbad"``
      * ``attestation_template_id: str`` (e.g. ``"bad_orb_2026_v1"``)
      * ``beglaubigung_clauses: list[dict]`` (each containing ``clause_id``,
        ``clause_text``, ``signature_required``, ``notarization_required``,
        ``effective_date``)

    The function MUST produce the `hessen_bad_orb_2026.yaml` profile in
    ≤1 minute wall-time.
    """
    _predicate_filing_2026_validate_module_is_importable()
    mod = _get_2026_validate_module()

    # ----- function existence check -----
    extract_2026_satzung_schema = getattr(mod, "extract_2026_satzung_schema", None)
    assert callable(extract_2026_satzung_schema), (
        "AC-1: 2026_validate must expose a callable extract_2026_satzung_schema "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- wall-time budget: ≤1 minute -----
    start = time.monotonic()
    result = extract_2026_satzung_schema(_SYNTHETIC_2026_SATZUNG_SOURCE)
    elapsed = time.monotonic() - start
    assert elapsed <= 60.0, (
        f"AC-1: extract_2026_satzung_schema must produce profile in ≤1 minute "
        f"wall-time; took {elapsed:.2f}s"
    )

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-1: extract_2026_satzung_schema must return a JSON-serialisable "
        f"dict; got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # ----- structural key assertions -----
    required_keys = [
        "satzung_date",
        "bundesland",
        "kurort",
        "predicate",
        "attestation_template_id",
        "beglaubigung_clauses",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-1: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- satzung_date concrete ISO date string -----
    assert result["satzung_date"] == "2026-07-01", (
        f"AC-1: satzung_date must equal '2026-07-01' (Bad Orb "
        f"Kurbeitragssatzung effective date); got {result['satzung_date']!r}"
    )

    # ----- bundesland + kurort + predicate assertions -----
    assert result["bundesland"] == "hessen", (
        f"AC-1: bundesland must equal 'hessen'; got {result['bundesland']!r}"
    )
    assert result["kurort"] == "bad_orb", (
        f"AC-1: kurort must equal 'bad_orb'; got {result['kurort']!r}"
    )
    assert result["predicate"] == "heilbad", (
        f"AC-1: predicate must equal 'heilbad'; got {result['predicate']!r}"
    )

    # ----- attestation_template_id (e.g. "bad_orb_2026_v1") -----
    attestation_template_id = result["attestation_template_id"]
    assert isinstance(attestation_template_id, str), (
        f"AC-1: attestation_template_id must be a str; "
        f"got {type(attestation_template_id).__name__}: {attestation_template_id!r}"
    )
    assert re.match(r"^bad_orb_2026_v\d+$", attestation_template_id), (
        f"AC-1: attestation_template_id must match 'bad_orb_2026_v<digit>+'; "
        f"got {attestation_template_id!r}"
    )

    # ----- beglaubigung_clauses: list[dict] with required sub-fields -----
    beglaubigung_clauses = result["beglaubigung_clauses"]
    assert isinstance(beglaubigung_clauses, list), (
        f"AC-1: beglaubigung_clauses must be a list; "
        f"got {type(beglaubigung_clauses).__name__}"
    )
    assert len(beglaubigung_clauses) >= 1, (
        f"AC-1: beglaubigung_clauses must have ≥1 entry (per 2026 Satzung); "
        f"got {len(beglaubigung_clauses)} entries"
    )

    for clause in beglaubigung_clauses:
        assert isinstance(clause, dict), (
            f"AC-1: each beglaubigung_clauses entry must be a dict; "
            f"got {type(clause).__name__}: {clause!r}"
        )
        for sub_key in ("clause_id", "clause_text", "signature_required",
                        "notarization_required", "effective_date"):
            assert sub_key in clause, (
                f"AC-1: beglaubigung_clauses entry missing '{sub_key}'; "
                f"got {sorted(clause.keys())!r}"
            )

    # ----- anti-drift: profile YAML is produced (hessen_bad_orb_2026.yaml) -----
    _hessen_bad_orb_2026_profile_yaml_exists()


# ===========================================================================
# AC-2 — load_2026_profile preserves 6 iter-33 fields + includes Beglaubigung
# ===========================================================================

def test_ac2_load_2026_profile_preserves_iter33_fields_and_includes_beglaubigung() -> None:
    """AC-2 spec test_oracle - happy-path: profile preserves iter-33 fields.

    Asserts that ``load_2026_profile() -> dict`` returns a dict containing:
      * All 6 iter-33-SHIPPED attestation fields (predicate_label, period,
        reprdikatisierung_window, accessibility_label, non_affirmation_footer,
        bfsg_aa_compliant)
      * NEW 2026-specific fields (bundesland, kurort, predicate,
        satzung_date=2026-07-01, attestation_template_id=bad_orb_2026_v1,
        beglaubigung_clauses, stale_pending=False, bands including adult: 2.50,
        preserves_iter33_fields=True)
    """
    _predicate_filing_2026_validate_module_is_importable()
    _hessen_bad_orb_2026_profile_yaml_exists()
    mod = _get_2026_validate_module()

    load_2026_profile = getattr(mod, "load_2026_profile", None)
    assert callable(load_2026_profile), (
        "AC-2: 2026_validate must expose a callable load_2026_profile entry "
        f"point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    profile = load_2026_profile()

    # ----- return-type check -----
    assert isinstance(profile, dict), (
        f"AC-2: load_2026_profile must return a dict; "
        f"got {type(profile).__name__}: {profile!r}"
    )

    serialised = json.dumps(profile, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # ----- 6 iter-33-SHIPPED attestation fields preserved -----
    iter33_fields = [
        "predicate_label",
        "period",
        "reprdikatisierung_window",
        "accessibility_label",
        "non_affirmation_footer",
        "bfsg_aa_compliant",
    ]
    for field in iter33_fields:
        assert field in profile, (
            f"AC-2: iter-33 SHIPPED attestation field '{field}' MUST be "
            f"preserved in 2026 profile (anti-drift discipline); "
            f"got keys {sorted(profile.keys())!r}"
        )

    # ----- predicate_label concrete value -----
    assert profile["predicate_label"] == "Heilbad Bad Orb (Hessischer Heilbäderverband)", (
        f"AC-2: predicate_label must equal 'Heilbad Bad Orb "
        f"(Hessischer Heilbäderverband)'; got {profile['predicate_label']!r}"
    )

    # ----- reprdikatisierung_window tuple[str, str] concrete value -----
    assert profile["reprdikatisierung_window"] == ("2034-01-01", "2044-12-31"), (
        f"AC-2: reprdikatisierung_window must equal ('2034-01-01', '2044-12-31') "
        f"(forward-projected 2024-2034 cycle per ALEA PARK); "
        f"got {profile['reprdikatisierung_window']!r}"
    )

    # ----- NEW 2026-specific fields -----
    assert profile["bundesland"] == "hessen", (
        f"AC-2: bundesland must equal 'hessen'; got {profile['bundesland']!r}"
    )
    assert profile["kurort"] == "bad_orb", (
        f"AC-2: kurort must equal 'bad_orb'; got {profile['kurort']!r}"
    )
    assert profile["predicate"] == "heilbad", (
        f"AC-2: predicate must equal 'heilbad'; got {profile['predicate']!r}"
    )
    assert profile["satzung_date"] == "2026-07-01", (
        f"AC-2: satzung_date must equal '2026-07-01'; "
        f"got {profile['satzung_date']!r}"
    )
    assert profile["attestation_template_id"] == "bad_orb_2026_v1", (
        f"AC-2: attestation_template_id must equal 'bad_orb_2026_v1'; "
        f"got {profile['attestation_template_id']!r}"
    )

    # ----- Beglaubigung clauses (forced-flaw Weakness #1 KEPT mitigation) -----
    beglaubigung_clauses = profile["beglaubigung_clauses"]
    assert isinstance(beglaubigung_clauses, list), (
        f"AC-2: beglaubigung_clauses must be a list; "
        f"got {type(beglaubigung_clauses).__name__}"
    )
    assert len(beglaubigung_clauses) >= 1, (
        f"AC-2: beglaubigung_clauses must have ≥1 entry per 2026 Satzung "
        f"(forced-flaw Weakness #1 KEPT mitigation); "
        f"got {len(beglaubigung_clauses)} entries"
    )

    # ----- stale_pending flag (forced-flaw Weakness #3 DISMISSED mitigation) -----
    assert profile["stale_pending"] is False, (
        f"AC-2: stale_pending must default to False "
        f"(forced-flaw Weakness #3 mitigation; set True on "
        f"Stadtverordnetenversammlung re-amendment); "
        f"got {profile['stale_pending']!r}"
    )

    # ----- bands list with adult: 2.50 -----
    bands = profile["bands"]
    assert isinstance(bands, list), (
        f"AC-2: bands must be a list; got {type(bands).__name__}"
    )
    assert len(bands) == 5, (
        f"AC-2: bands must contain 5 rate bands (adult + adult_disabled_70 + "
        f"youth + youth_disabled_70 + child); got {len(bands)} bands"
    )
    adult_band = next((b for b in bands if b.get("name") == "adult"), None)
    assert adult_band is not None, (
        f"AC-2: bands MUST contain 'adult' band; got names {[b.get('name') for b in bands]!r}"
    )
    adult_rate = adult_band.get("rate_eur") or adult_band.get("rate_per_day")
    assert str(adult_rate) == "2.50", (
        f"AC-2: adult band MUST have rate 2.50 EUR/day per Bad Orb 2026 "
        f"Kurbeitragssatzung; got {adult_rate!r}"
    )

    # ----- preserves_iter33_fields anti-drift marker -----
    assert profile["preserves_iter33_fields"] is True, (
        f"AC-2: preserves_iter33_fields MUST be True (anti-drift marker "
        f"confirming all 6 iter-33 fields preserved); "
        f"got {profile['preserves_iter33_fields']!r}"
    )


# ===========================================================================
# AC-3 — apply_2026_attestation_template applies adult rate with 100% precision
# ===========================================================================

def test_ac3_apply_2026_attestation_template_applies_adult_rate_with_100_precision() -> None:
    """AC-3 spec test_oracle - happy-path: 2026 attestation with adult=2.50.

    Asserts that ``apply_2026_attestation_template(profile: dict,
    attestation_data: dict) -> dict`` returns a JSON-serializable dict with
    required keys:
      * attestation_template_id="bad_orb_2026_v1"
      * satzung_date="2026-07-01"
      * predicate_label="Heilbad Bad Orb (Hessischer Heilbäderverband)"
      * adult_rate_applied="2.50" (100% precision)
      * beglaubigung_sealed=True (all Beglaubigung clauses applied)
      * accessibility_label ≥ 20 chars
      * non_affirmation_footer containing the verbatim 2026 Satzung clause
    """
    _predicate_filing_2026_attestation_module_is_importable()
    mod = _get_2026_attestation_module()

    apply_2026_attestation_template = getattr(
        mod, "apply_2026_attestation_template", None,
    )
    assert callable(apply_2026_attestation_template), (
        "AC-3: 2026_attestation must expose a callable "
        f"apply_2026_attestation_template entry point; "
        f"found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: minimal 2026 profile + minimal attestation_data -----
    profile = {
        "bundesland": "hessen",
        "kurort": "bad_orb",
        "predicate": "heilbad",
        "satzung_date": "2026-07-01",
        "attestation_template_id": "bad_orb_2026_v1",
        "predicate_label": "Heilbad Bad Orb (Hessischer Heilbäderverband)",
        "beglaubigung_clauses": [
            {
                "clause_id": "BG-2026-001",
                "clause_text": "Der Beitragsgläubiger hat die Erhebung zu bestätigen.",
                "signature_required": True,
                "notarization_required": False,
                "effective_date": "2026-07-01",
            },
        ],
        "bands": [{"name": "adult", "rate_eur": "2.50"}],
        "preserves_iter33_fields": True,
    }
    attestation_data = {
        "guest_name": "Test Guest",
        "arrival": "2026-07-15",
        "departure": "2026-07-20",
        "rate_band": "adult",
    }

    result = apply_2026_attestation_template(profile, attestation_data)

    # ----- return-type check -----
    assert isinstance(result, dict), (
        f"AC-3: apply_2026_attestation_template must return a "
        f"JSON-serialisable dict; got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # ----- structural key assertions -----
    for key in (
        "attestation_template_id",
        "satzung_date",
        "predicate_label",
        "adult_rate_applied",
        "beglaubigung_sealed",
        "accessibility_label",
        "non_affirmation_footer",
    ):
        assert key in result, (
            f"AC-3: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- attestation_template_id concrete value -----
    assert result["attestation_template_id"] == "bad_orb_2026_v1", (
        f"AC-3: attestation_template_id must equal 'bad_orb_2026_v1'; "
        f"got {result['attestation_template_id']!r}"
    )

    # ----- satzung_date concrete ISO date -----
    assert result["satzung_date"] == "2026-07-01", (
        f"AC-3: satzung_date must equal '2026-07-01'; "
        f"got {result['satzung_date']!r}"
    )

    # ----- predicate_label concrete value -----
    assert result["predicate_label"] == "Heilbad Bad Orb (Hessischer Heilbäderverband)", (
        f"AC-3: predicate_label must equal 'Heilbad Bad Orb "
        f"(Hessischer Heilbäderverband)'; got {result['predicate_label']!r}"
    )

    # ----- adult_rate_applied with 100% precision -----
    adult_rate_applied = result["adult_rate_applied"]
    assert str(adult_rate_applied) == "2.50", (
        f"AC-3: adult_rate_applied MUST equal '2.50' with 100% precision "
        f"per Bad Orb 2026 Kurbeitragssatzung; got {adult_rate_applied!r}"
    )

    # ----- beglaubigung_sealed=True -----
    assert result["beglaubigung_sealed"] is True, (
        f"AC-3: beglaubigung_sealed MUST be True (all Beglaubigung clauses "
        f"applied per AC-2 + forced-flaw Weakness #1); "
        f"got {result['beglaubigung_sealed']!r}"
    )

    # ----- accessibility_label ≥ 20 chars (BFSG-EAA WCAG 2.1 SC 4.1.3) -----
    accessibility_label = result["accessibility_label"]
    assert isinstance(accessibility_label, str), (
        f"AC-3: accessibility_label must be a str; "
        f"got {type(accessibility_label).__name__}"
    )
    assert len(accessibility_label) >= 20, (
        f"AC-3: accessibility_label must be ≥ 20 chars per WCAG 2.1 SC 4.1.3 "
        f"+ EN 301 549 baseline; got {len(accessibility_label)} chars: "
        f"{accessibility_label!r}"
    )

    # ----- non_affirmation_footer verbatim 2026 Satzung clause -----
    non_aff = result["non_affirmation_footer"]
    assert isinstance(non_aff, str), (
        f"AC-3: non_affirmation_footer must be a str; "
        f"got {type(non_aff).__name__}"
    )
    expected_clause = (
        "This Kurort-predicate attestation is generated against the Bad Orb "
        "Kurbeitragssatzung 01.07.2026 and is provided as voluntary "
        "predicate-renewal positioning; it is NOT a regulatory compliance "
        "attestation"
    )
    assert expected_clause in non_aff, (
        f"AC-3: non_affirmation_footer MUST contain the verbatim 2026 Satzung "
        f"clause per spec.yaml AC-3; got non_aff={non_aff!r}"
    )


# ===========================================================================
# AC-4 — compute_anti_drift_sha preserves iter-33 chain-extension integrity
# ===========================================================================

def test_ac4_compute_anti_drift_sha_preserves_iter33_chain_extension_integrity() -> None:
    """AC-4 spec test_oracle - happy-path: SHA-256 of iter-33 chain-extension.

    Asserts that ``compute_anti_drift_sha(profile: dict, baseline_sha: str |
    None = None) -> str`` returns the SHA-256 hex digest (64 chars) of a
    canonical JSON representation of the iter-33-SHIPPED
    `kurort_engine.predicate_filing` chain-extension. The function MUST:
      * return a 64-char hex SHA-256 digest
      * return ``baseline_sha`` unchanged if provided AND the iter-33
        chain-extension has NOT drifted
      * raise ``kurort_engine.kurkarte_wallet.BFSGComplianceError`` if the
        iter-33 SHIPPED chain-extension has drifted (i.e. computed SHA does
        NOT match ``baseline_sha``)
      * NOT modify any of the 6 SHIPPED modules
    """
    _kurkarte_wallet_is_importable()
    _predicate_filing_is_importable()
    _esg_report_is_importable()
    _spa_wellness_is_importable()
    _ev_charging_is_importable()
    _predicate_filing_2026_attestation_module_is_importable()

    # Import SHIPPED BFSGComplianceError for the drift-raises test
    import kurort_engine.kurkarte_wallet as _kw  # noqa: E402
    BFSGComplianceError = getattr(_kw, "BFSGComplianceError", None)
    assert BFSGComplianceError is not None, (
        f"AC-4: kurort_engine.kurkarte_wallet must expose BFSGComplianceError; "
        f"found: {[n for n in dir(_kw) if not n.startswith('_')]!r}"
    )

    mod = _get_2026_attestation_module()

    compute_anti_drift_sha = getattr(mod, "compute_anti_drift_sha", None)
    assert callable(compute_anti_drift_sha), (
        "AC-4: 2026_attestation must expose a callable compute_anti_drift_sha "
        f"entry point; found: {[n for n in dir(mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path: compute SHA-256 of iter-33 chain-extension -----
    profile = {
        "bundesland": "hessen",
        "kurort": "bad_orb",
        "predicate": "heilbad",
        "satzung_date": "2026-07-01",
        "attestation_template_id": "bad_orb_2026_v1",
        "preserves_iter33_fields": True,
    }

    sha = compute_anti_drift_sha(profile)

    # ----- SHA-256 hex digest: 64 chars + hex-only -----
    assert isinstance(sha, str), (
        f"AC-4: compute_anti_drift_sha must return a str; "
        f"got {type(sha).__name__}: {sha!r}"
    )
    assert len(sha) == 64, (
        f"AC-4: compute_anti_drift_sha must return 64-char SHA-256 hex "
        f"digest; got {len(sha)} chars: {sha!r}"
    )
    assert re.match(r"^[0-9a-f]{64}$", sha), (
        f"AC-4: compute_anti_drift_sha must return lowercase hex; "
        f"got {sha!r}"
    )

    # ----- stable across re-invocations -----
    sha2 = compute_anti_drift_sha(profile)
    assert sha == sha2, (
        f"AC-4: compute_anti_drift_sha must be stable across re-invocations; "
        f"first={sha!r} second={sha2!r}"
    )

    # ----- happy-path: baseline_sha matches → return baseline_sha -----
    returned_baseline = compute_anti_drift_sha(profile, baseline_sha=sha)
    assert returned_baseline == sha, (
        f"AC-4: compute_anti_drift_sha must return baseline_sha unchanged "
        f"when iter-33 chain-extension is intact; "
        f"baseline={sha!r} returned={returned_baseline!r}"
    )

    # ----- drift detection: wrong baseline_sha → raise BFSGComplianceError -----
    wrong_baseline = "0" * 64
    with pytest.raises(BFSGComplianceError) as excinfo:
        compute_anti_drift_sha(profile, baseline_sha=wrong_baseline)
    error_msg = str(excinfo.value)
    assert "anti-drift" in error_msg.lower() or "drift" in error_msg.lower(), (
        f"AC-4: BFSGComplianceError message MUST mention 'anti-drift' or "
        f"'drift'; got message={error_msg!r}"
    )


# ===========================================================================
# AC-5 — full test suite: 113 baseline + 5 new = 118/118 tests PASS
# ===========================================================================

def test_ac5_full_test_suite_113_baseline_plus_5_new_passes_118_of_118() -> None:
    """AC-5 spec test_oracle - full test suite integration.

    Verifies that the iter-36 NEW test file contains exactly 5 tests
    (test_ac1..test_ac5) AND that pytest can collect them. The actual
    113+5 = 118/118 run is verified at Phase 3 green via done_when[1]
    (full pytest suite run). This RED test asserts:
      * 5 NEW tests are present in this file (test_ac1..test_ac5)
      * pytest can collect them without ImportError / CollectionError
      * the iter-33 SHIPPED baseline (113 tests) is preserved (per
        spec.yaml A-6 + pinned rule 3)
    """
    import os
    import subprocess

    # ----- 5 NEW tests present in this file -----
    test_path = os.path.abspath(__file__)
    assert os.path.isfile(test_path), (
        f"AC-5: this test file must exist at {test_path}"
    )

    with open(test_path, encoding="utf-8") as f:
        content = f.read()

    new_test_names = [
        "test_ac1_extract_2026_satzung_schema_produces_hessen_bad_orb_2026_profile",
        "test_ac2_load_2026_profile_preserves_iter33_fields_and_includes_beglaubigung",
        "test_ac3_apply_2026_attestation_template_applies_adult_rate_with_100_precision",
        "test_ac4_compute_anti_drift_sha_preserves_iter33_chain_extension_integrity",
        "test_ac5_full_test_suite_113_baseline_plus_5_new_passes_118_of_118",
    ]
    for name in new_test_names:
        assert f"def {name}(" in content, (
            f"AC-5: NEW test '{name}' MUST be defined in this file "
            f"(spec.yaml test_oracle contract)"
        )

    # ----- pytest can collect all 5 NEW tests -----
    repo_dir = os.path.dirname(test_path)
    parent_dir = os.path.dirname(repo_dir)  # workspace root
    cwd_candidates = [repo_dir, parent_dir]
    collected_count = None
    last_err = None
    for cwd in cwd_candidates:
        try:
            proc = subprocess.run(
                [
                    ".venv/bin/pytest",
                    f"tests/test_predicate_filing_2026.py",
                    "--collect-only",
                    "-q",
                    "--override-ini=addopts=--tb=line",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            last_err = output
            # Look for "5 tests collected" line
            import re as _re
            m = _re.search(r"(\d+)\s+tests?\s+collected", output)
            if m:
                collected_count = int(m.group(1))
                break
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            continue

    assert collected_count is not None and collected_count >= 5, (
        f"AC-5: pytest must collect ≥5 NEW tests from "
        f"tests/test_predicate_filing_2026.py; got {collected_count!r}; "
        f"last pytest output: {last_err!r}"
    )

    # ----- iter-33 SHIPPED baseline importability preserved -----
    # Per pinned rule 3: 113 baseline tests must STILL pass after red-phase
    # additions (we have not modified any src/ or existing tests/ files).
    _predicate_filing_package_is_importable()
    _kurkarte_wallet_is_importable()
    _esg_report_is_importable()
    _spa_wellness_is_importable()
    _ev_charging_is_importable()

    # ----- NEW 2026 functions are exposed under the kurort_engine.predicate_filing namespace -----
    # Per spec.yaml AC-1, AC-2, AC-3, AC-4 + spec.yaml done_when[3]: the NEW
    # 2026 symbols MUST be importable via `from kurort_engine.predicate_filing
    # import extract_2026_satzung_schema, load_2026_profile, apply_2026_attestation_template,
    # compute_anti_drift_sha`. The chain-extension layer
    # `kurort_engine.predicate_filing.__init__` MUST re-export all 4 NEW symbols
    # (append-only, preserving the iter-33 SHIPPED 5 re-exports).
    # This assertion WILL FAIL in red phase because the NEW 2026 modules
    # do not exist yet (the modules MUST be created in Phase 3 green first).
    # Per pinned rule 3 (RED verification protocol): the failure MUST be
    # AssertionError, not ImportError.
    _predicate_filing_2026_validate_module_is_importable()
    _predicate_filing_2026_attestation_module_is_importable()
    validate_mod = _get_2026_validate_module()
    attestation_mod = _get_2026_attestation_module()
    assert callable(getattr(validate_mod, "extract_2026_satzung_schema", None)), (
        "AC-5: kurort_engine.predicate_filing.2026_validate must expose "
        "callable extract_2026_satzung_schema (AC-1)"
    )
    assert callable(getattr(validate_mod, "load_2026_profile", None)), (
        "AC-5: kurort_engine.predicate_filing.2026_validate must expose "
        "callable load_2026_profile (AC-2)"
    )
    assert callable(getattr(attestation_mod, "apply_2026_attestation_template", None)), (
        "AC-5: kurort_engine.predicate_filing.2026_attestation must expose "
        "callable apply_2026_attestation_template (AC-3)"
    )
    assert callable(getattr(attestation_mod, "compute_anti_drift_sha", None)), (
        "AC-5: kurort_engine.predicate_filing.2026_attestation must expose "
        "callable compute_anti_drift_sha (AC-4)"
    )

    # ----- NEW 2026 profile YAML exists on disk -----
    # Per spec.yaml AC-2: `hessen_bad_orb_2026.yaml` MUST be created in
    # `kurort_engine/profiles/` before AC-2 can pass.
    _hessen_bad_orb_2026_profile_yaml_exists()