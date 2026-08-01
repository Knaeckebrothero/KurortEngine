"""Iter-33 Phase 2 RED tests — kurort_engine.predicate_filing H1 Heilbad 2036
Reprädikatisierung predicate-renewal filing packet generator (AC-1..AC-5).

Iter-33 (Developer) — Pattern F chain-extension of iter-30 SHIPPED
kurort_engine.esg.report (HCMI Scope 1+2 + Heilbad 2036 ESG narrative) +
iter-21 SHIPPED kurort_engine.kurkarte_wallet (BFSGComplianceError) +
iter-18 SHIPPED kurort_engine.kurpaket_orchestrator (SGBV23CertificateMissing)
+ iter-3 SHIPPED kurort_engine.spa_wellness (SpaManager + ToskanaThermeAdapter)
+ iter-24 SHIPPED kurort_engine.ev_charging (reservation_match mobility data).

Chosen by iter-31 Scholar pick-first H1 Heilbad 2036 predicate filing (H1-NARROW
Tier-2 sub-package scope; 9/9 Pattern D clean per
`iter-31-idea-index-synthesis-3-pool-3-fresh-candidates-h1-heilbad-2036-h4-kiosk-`
§6 Scholar synthesis). 6 SHIPPED modules preserved verbatim (anti-drift discipline).

AC-1 contract (verbatim from spec.yaml PROTECTED block):

    Ubiquitous. The system shall expose an
    `assemble_predicate_packet(period_start: date, period_end: date,
    kurgaste_records: list[dict], kurtaxe_data: dict, hcmi_scope1_2_data:
    dict, spa_data: dict, ev_charging_data: dict) -> dict` function in
    `kurort_engine.predicate_filing.predicate_packet_assembler` that returns
    a JSON-serializable `dict` describing the Bad Orb Heilbad 2036
    Reprädikatisierung predicate-renewal filing packet, with required top-level
    keys: `metadata: dict` containing `predicate_label: str = "Heilbad Bad
    Orb (Hessischer Heilbäderverband)"`, `period: tuple[str, str]` (ISO format
    of period_start and period_end), and `reprdikatisierung_window:
    tuple[str, str] = ("2034-01-01", "2044-12-31")` (forward-projected 2024-2034
    cycle per ALEA PARK [1307]); `kurgaste_section: dict`; `kurtaxe_section:
    dict`; `esg_section: dict`; `spa_section: dict`; `mobility_section:
    dict`; the function MUST raise `ValueError` if `period_start >=
    period_end` OR if `(period_end.year - period_start.year) < 4` (10-year
    Reprädikatisierung cycle minimum, accepting 4-year transition windows);
    the function MUST NOT modify any of the 5 SHIPPED modules it chains from.

AC-2 contract:

    Event-driven. When `validate_kurgaste_health_data(kurgaste_records:
    list[dict])` is called in
    `kurort_engine.predicate_filing.kurgaste_health_data_aggregator` THEN the
    system shall return `True` if every record has `consent_dsgvo_art9:
    bool = True` AND every Spezial-Heilbad (template_code = "E") record
    carries a non-empty `muster13_id: str` (i.e. a §23 SGB V Muster 13
    Badekur certificate); the function MUST raise
    `kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing` (re-used
    from SHIPPED iter-18) for any Spezial-Heilbad record missing
    `muster13_id`; the function MUST raise `DSGVOArt9ValidationError` (a
    NEW exception class defined in `kurort_engine.predicate_filing`) for
    any record where `consent_dsgvo_art9` is `False` or missing.

AC-3 contract:

    Event-driven. When `generate_heilbad_2036_narrative(kurgaste_data: dict,
    hcmi_scope1_2_data: dict, kurtaxe_data: dict, lang: str = "de")` is
    called in `kurort_engine.predicate_filing.heilbad_2036_narrative_generator`
    THEN the system shall return a JSON-serializable `dict` describing the
    Heilbad 2036 Reprädikatisierung narrative for Hotel Rheinland Bad Orb,
    with required keys: `predicate_label`, `narrative_de` (≥ 300 chars
    mentioning all 6 canonical Kurort-vertical anchors: Spessart Bike Tage +
    R3 Kinzigtal + WaldErfahren + E-Bike charging (Q5.2) + Toskana Therme
    partnership + thermal-spring NiedrigEnergie baseline), `narrative_en`
    (≥ 300 chars with same 6 anchors), `representative_period =
    ("2034-01-01", "2044-12-31")`, `lang` defaulting to `"de"` accepting
    `"en"`, `accessibility_label` ≥ 20 chars; the function MUST chain-extend
    the SHIPPED iter-30
    `kurort_engine.esg.report.generate_heilbad_2036_esg_narrative` (NOT
    duplicate it) for the narrative_de and narrative_en blocks.

AC-4 contract:

    Unwanted-behavior. If `export_predicate_filing_bfsg_aa(predicate_packet:
    dict, narrative: dict, lang: str = "de", accessibility_label: str = "")`
    is called in
    `kurort_engine.predicate_filing.predicate_filing_export` THEN the
    function MUST raise
    `kurort_engine.kurkarte_wallet.BFSGComplianceError` (re-using the SHIPPED
    iter-21 `kurort_engine.kurkarte_wallet.BFSGComplianceError` exception
    class) naming the missing field if `lang != "de"` OR if
    `len(accessibility_label) < 20`; on the happy path the function MUST
    return a JSON-serializable `dict` with required keys: `predicate_packet`,
    `narrative`, `lang = "de"`, `accessibility_label` ≥ 20 chars,
    `screen_reader_contrast = "4.5:1"`, `compliance_ok = True`,
    `non_affirmation_footer` containing the verbatim clause "This ESG and
    Heilbad 2036 predicate filing is voluntary and is provided as
    ESG-readiness and predicate-renewal positioning for Bad Orb Kur GmbH;
    it is NOT a regulatory compliance attestation".

AC-5 contract:

    Ubiquitous. The system shall expose an
    `aggregate_kurgaste_health_data(kurgaste_records: list[dict]) -> dict`
    function in
    `kurort_engine.predicate_filing.kurgaste_health_data_aggregator` that
    returns a JSON-serializable `dict` with required keys:
    `total_records: int`, `badekurst_guests: int` (count of Spezial-Heilbad
    template_E bookings with valid `muster13_id`), `classic_guests: int`
    (count of template_A/B/C/D bookings), `consent_art9_count: int` (count
    of records with `consent_dsgvo_art9 = True`), `period: tuple[str, str]`
    (ISO format of first arrival + last departure among records), and
    `consent_compliance: bool` (True iff every record has
    `consent_dsgvo_art9 = True`); the function MUST raise
    `DSGVOArt9ValidationError` (defined in this package) if any record
    missing the `consent_dsgvo_art9` field entirely.

RED VERIFY
----------
Tests MUST fail with ``AssertionError``, NOT ImportError. We use
``importlib.util.find_spec`` as a pre-check (wrapped in try/except) so
missing-module failures surface as ``AssertionError`` ("module should exist"),
not ``ModuleNotFoundError``.

Per `iter-33-developer-pinned-rules-h1-heilbad-2036-predicate-filing-tdd-discipline-5`:
  * No mocking the unit under test
  * No ``pytest.skip``
  * Concrete ISO date string-form assertions (no datetime arithmetic drift)
  * Concrete ``pytest.raises(ValueError | SGBV23CertificateMissing |
    DSGVOArt9ValidationError | BFSGComplianceError)`` guards
  * Chain-extension to SHIPPED modules is exercised via real imports
    (NOT mocked) — confirms the 6 SHAs are importable
  * All 6 SHIPPED modules MUST remain verbatim UNCHANGED
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date

import pytest


# ===========================================================================
# Module-importability helpers (per iter-30 honest-RED pattern)
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


def _predicate_filing_package_is_importable() -> str:
    """Pre-check: the NEW predicate_filing package must exist (iter-33 NEW)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing",
        parent="kurort_engine.predicate_filing",
    )


def _predicate_packet_assembler_module_is_importable() -> str:
    """Pre-check: NEW predicate_packet_assembler module must exist (AC-1)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.predicate_packet_assembler",
        parent="kurort_engine.predicate_filing.predicate_packet_assembler",
    )


def _kurgaste_health_data_aggregator_module_is_importable() -> str:
    """Pre-check: NEW kurgaste_health_data_aggregator module must exist (AC-2+AC-5)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.kurgaste_health_data_aggregator",
        parent="kurort_engine.predicate_filing.kurgaste_health_data_aggregator",
    )


def _heilbad_2036_narrative_generator_module_is_importable() -> str:
    """Pre-check: NEW heilbad_2036_narrative_generator module must exist (AC-3)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.heilbad_2036_narrative_generator",
        parent="kurort_engine.predicate_filing.heilbad_2036_narrative_generator",
    )


def _predicate_filing_export_module_is_importable() -> str:
    """Pre-check: NEW predicate_filing_export module must exist (AC-4)."""
    return _find_spec_or_assert(
        "kurort_engine.predicate_filing.predicate_filing_export",
        parent="kurort_engine.predicate_filing.predicate_filing_export",
    )


# SHIPPED modules anti-drift helpers (must remain importable in iter-33 GREEN)
def _kurkarte_wallet_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.kurkarte_wallet")


def _kurpaket_orchestrator_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.kurpaket_orchestrator")


def _esg_report_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.esg.report")


def _spa_wellness_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.spa_wellness")


def _ev_charging_is_importable() -> str:
    return _find_spec_or_assert("kurort_engine.ev_charging")


# Import helpers (after find_spec guard)
def _get_predicate_filing_package():
    """Import the new predicate_filing package after the find_spec guard."""
    _predicate_filing_package_is_importable()
    import kurort_engine.predicate_filing as _pf  # noqa: E402
    assert _pf is not None, "importlib returned None - package is None"
    return _pf


def _get_predicate_packet_assembler():
    _predicate_packet_assembler_module_is_importable()
    import kurort_engine.predicate_filing.predicate_packet_assembler as _ppa  # noqa: E402
    assert _ppa is not None
    return _ppa


def _get_kurgaste_health_data_aggregator():
    _kurgaste_health_data_aggregator_module_is_importable()
    import kurort_engine.predicate_filing.kurgaste_health_data_aggregator as _khda  # noqa: E402
    assert _khda is not None
    return _khda


def _get_heilbad_2036_narrative_generator():
    _heilbad_2036_narrative_generator_module_is_importable()
    import kurort_engine.predicate_filing.heilbad_2036_narrative_generator as _h2036  # noqa: E402
    assert _h2036 is not None
    return _h2036


def _get_predicate_filing_export():
    _predicate_filing_export_module_is_importable()
    import kurort_engine.predicate_filing.predicate_filing_export as _pfe  # noqa: E402
    assert _pfe is not None
    return _pfe


# ===========================================================================
# AC-1 — assemble_predicate_packet emits 6 canonical sections
# ===========================================================================

def test_ac1_assemble_predicate_packet_emits_six_canonical_sections() -> None:
    """AC-1 spec test_oracle - happy-path predicate packet assembly.

    Asserts that ``assemble_predicate_packet(date(2034,1,1), date(2044,12,31),
    kurgaste_records, kurtaxe_data, hcmi_scope1_2_data, spa_data,
    ev_charging_data)`` returns a JSON-serializable dict with required
    top-level keys:
      * ``metadata`` dict containing ``predicate_label``,
        ``period: tuple[str, str]``, and ``reprdikatisierung_window =
        ("2034-01-01", "2044-12-31")``
      * ``kurgaste_section`` dict
      * ``kurtaxe_section`` dict
      * ``esg_section`` dict
      * ``spa_section`` dict
      * ``mobility_section`` dict
    """
    _predicate_packet_assembler_module_is_importable()
    ppa_mod = _get_predicate_packet_assembler()

    # Function must be exposed under the canonical name (no rename allowed)
    assemble_predicate_packet = getattr(ppa_mod, "assemble_predicate_packet", None)
    assert callable(assemble_predicate_packet), (
        "AC-1: predicate_packet_assembler must expose a callable "
        "assemble_predicate_packet entry point; found: "
        f"{[n for n in dir(ppa_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args: 2034-2044 Reprädikatisierung cycle -----
    period_start = date(2034, 1, 1)
    period_end = date(2044, 12, 31)
    kurgaste_records = [
        {
            "consent_dsgvo_art9": True,
            "template_code": "A",
            "muster13_id": None,
            "arrival": date(2034, 6, 1),
            "departure": date(2034, 6, 8),
        },
    ]
    kurtaxe_data = {
        "band": "A",
        "rate_eur": __import__("decimal").Decimal("2.20"),
        "kurbeitrag_eur": __import__("decimal").Decimal("2.20"),
    }
    hcmi_scope1_2_data = {
        "total_scope1_2_tco2e": __import__("decimal").Decimal("800.0"),
    }
    spa_data = {"sauna_slots": 0, "toskana_tickets": 0}
    ev_charging_data = {"sessions": 0, "kwh_delivered": __import__("decimal").Decimal("0")}

    result = assemble_predicate_packet(
        period_start, period_end,
        kurgaste_records, kurtaxe_data, hcmi_scope1_2_data,
        spa_data, ev_charging_data,
    )

    # ----- return-type check (JSON-serialisable dict) -----
    assert isinstance(result, dict), (
        f"AC-1: assemble_predicate_packet must return a JSON-serialisable "
        f"dict; got {type(result).__name__}: {result!r}"
    )

    # ----- JSON-serialisability round-trip -----
    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0, (
        f"AC-1: result must be JSON-serialisable; json.dumps returned "
        f"{type(serialised).__name__} of length {len(serialised)}"
    )

    # ----- structural key assertions (6 canonical sections + metadata) -----
    required_keys = [
        "metadata",
        "kurgaste_section",
        "kurtaxe_section",
        "esg_section",
        "spa_section",
        "mobility_section",
    ]
    for key in required_keys:
        assert key in result, (
            f"AC-1: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # ----- metadata nested assertions -----
    metadata = result["metadata"]
    assert isinstance(metadata, dict), (
        f"AC-1: metadata must be a dict; got {type(metadata).__name__}"
    )
    assert metadata.get("predicate_label") == "Heilbad Bad Orb (Hessischer Heilbäderverband)", (
        f"AC-1: metadata.predicate_label must equal 'Heilbad Bad Orb "
        f"(Hessischer Heilbäderverband)'; got {metadata.get('predicate_label')!r}"
    )
    assert metadata.get("period") == ("2034-01-01", "2044-12-31"), (
        f"AC-1: metadata.period must equal ('2034-01-01', '2044-12-31'); "
        f"got {metadata.get('period')!r}"
    )
    assert metadata.get("reprdikatisierung_window") == ("2034-01-01", "2044-12-31"), (
        f"AC-1: metadata.reprdikatisierung_window must equal "
        f"('2034-01-01', '2044-12-31'); got {metadata.get('reprdikatisierung_window')!r}"
    )


def test_ac1_invalid_period_raises_value_error() -> None:
    """AC-1 boundary test - period_start >= period_end raises ValueError."""
    _predicate_packet_assembler_module_is_importable()
    ppa_mod = _get_predicate_packet_assembler()
    assemble_predicate_packet = getattr(ppa_mod, "assemble_predicate_packet", None)
    assert callable(assemble_predicate_packet)

    with pytest.raises(ValueError):
        assemble_predicate_packet(
            date(2034, 12, 31), date(2034, 1, 1),  # inverted: start > end
            [], {}, {}, {}, {},
        )


def test_ac1_short_cycle_raises_value_error() -> None:
    """AC-1 boundary test - cycle shorter than 4 years raises ValueError.

    The 10-year Reprädikatisierung cycle minimum allows 4-year transition
    windows per spec.yaml AC-1. A 3-year cycle is therefore invalid.
    """
    _predicate_packet_assembler_module_is_importable()
    ppa_mod = _get_predicate_packet_assembler()
    assemble_predicate_packet = getattr(ppa_mod, "assemble_predicate_packet", None)
    assert callable(assemble_predicate_packet)

    with pytest.raises(ValueError):
        assemble_predicate_packet(
            date(2034, 1, 1), date(2037, 1, 1),  # only 3 years
            [], {}, {}, {}, {},
        )


# ===========================================================================
# AC-2 — validate_kurgaste_health_data enforces §23 SGB V + DSGVO Art. 9
# ===========================================================================

def test_ac2_validate_kurgaste_health_data_returns_true_for_consented_records() -> None:
    """AC-2 spec test_oracle - happy-path: all records consented + non-Spezial-Heilbad.

    Asserts that ``validate_kurgaste_health_data([{consent_dsgvo_art9: True,
    template_code: "A", muster13_id: None}])`` returns ``True`` because the
    only record is Classic (not Spezial-Heilbad, no §23 SGB V Muster 13 needed).
    """
    _kurgaste_health_data_aggregator_module_is_importable()
    khda_mod = _get_kurgaste_health_data_aggregator()

    validate_kurgaste_health_data = getattr(khda_mod, "validate_kurgaste_health_data", None)
    assert callable(validate_kurgaste_health_data), (
        "AC-2: kurgaste_health_data_aggregator must expose a callable "
        "validate_kurgaste_health_data entry point; found: "
        f"{[n for n in dir(khda_mod) if not n.startswith('_')]!r}"
    )

    # Classic Kurpaket (template A); consent granted; no muster13 needed
    records = [
        {
            "consent_dsgvo_art9": True,
            "template_code": "A",
            "muster13_id": None,
        },
    ]
    result = validate_kurgaste_health_data(records)
    assert result is True, (
        f"AC-2: validate_kurgaste_health_data must return True for consented "
        f"Classic records; got {result!r}"
    )


def test_ac2_sgb_v_missing_certificate_raises() -> None:
    """AC-2 boundary test - Spezial-Heilbad (template E) without muster13 raises.

    Asserts that ``validate_kurgaste_health_data([{consent_dsgvo_art9: True,
    template_code: "E", muster13_id: None}])`` raises
    ``kurort_engine.kurpaket_orchestrator.SGBV23CertificateMissing`` (re-used
    from SHIPPED iter-18).
    """
    _kurpaket_orchestrator_is_importable()
    _kurgaste_health_data_aggregator_module_is_importable()
    import kurort_engine.kurpaket_orchestrator as _kpo
    SGBV23CertificateMissing = _kpo.SGBV23CertificateMissing

    khda_mod = _get_kurgaste_health_data_aggregator()
    validate_kurgaste_health_data = getattr(khda_mod, "validate_kurgaste_health_data", None)
    assert callable(validate_kurgaste_health_data)

    records = [
        {
            "consent_dsgvo_art9": True,
            "template_code": "E",  # Spezial-Heilbad → §23 SGB V Muster 13 required
            "muster13_id": None,  # MISSING — must raise
        },
    ]
    with pytest.raises(SGBV23CertificateMissing):
        validate_kurgaste_health_data(records)


def test_ac2_dsgvo_art9_consent_false_raises() -> None:
    """AC-2 boundary test - consent_dsgvo_art9=False raises DSGVOArt9ValidationError.

    Asserts that ``validate_kurgaste_health_data([{consent_dsgvo_art9: False,
    template_code: "A"}])`` raises the NEW ``DSGVOArt9ValidationError`` exception
    class defined in the predicate_filing package.
    """
    _kurgaste_health_data_aggregator_module_is_importable()
    khda_mod = _get_kurgaste_health_data_aggregator()

    DSGVOArt9ValidationError = getattr(khda_mod, "DSGVOArt9ValidationError", None)
    assert DSGVOArt9ValidationError is not None, (
        "AC-2: kurgaste_health_data_aggregator must expose a DSGVOArt9ValidationError "
        f"exception class; found: {[n for n in dir(khda_mod) if not n.startswith('_')]!r}"
    )

    validate_kurgaste_health_data = getattr(khda_mod, "validate_kurgaste_health_data", None)
    assert callable(validate_kurgaste_health_data)

    records = [
        {
            "consent_dsgvo_art9": False,  # DSGVO Art. 9 consent NOT granted
            "template_code": "A",
            "muster13_id": None,
        },
    ]
    with pytest.raises(DSGVOArt9ValidationError):
        validate_kurgaste_health_data(records)


# ===========================================================================
# AC-3 — generate_heilbad_2036_narrative emits 6 anchors with lang switch
# ===========================================================================

def test_ac3_generate_heilbad_2036_narrative_emits_six_anchors_with_lang_switch() -> None:
    """AC-3 spec test_oracle - happy-path: narrative_de ≥ 300 chars + 6 anchors.

    Asserts that ``generate_heilbad_2036_narrative(kurgaste_data,
    hcmi_scope1_2_data, kurtaxe_data)`` returns a dict with required keys:
    predicate_label, narrative_de (≥ 300 chars mentioning all 6 canonical
    Kurort-vertical anchors), narrative_en (≥ 300 chars with same anchors),
    representative_period = ("2034-01-01", "2044-12-31"),
    lang = "de" (default), accessibility_label ≥ 20 chars.

    The function MUST chain-extend (NOT duplicate) the SHIPPED iter-30
    ``kurort_engine.esg.report.generate_heilbad_2036_esg_narrative``.
    """
    _esg_report_is_importable()
    _heilbad_2036_narrative_generator_module_is_importable()
    h2036_mod = _get_heilbad_2036_narrative_generator()

    generate_heilbad_2036_narrative = getattr(
        h2036_mod, "generate_heilbad_2036_narrative", None,
    )
    assert callable(generate_heilbad_2036_narrative), (
        "AC-3: heilbad_2036_narrative_generator must expose a callable "
        "generate_heilbad_2036_narrative entry point; found: "
        f"{[n for n in dir(h2036_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args -----
    kurgaste_data = {
        "total_records": 10,
        "badekurst_guests": 2,
        "consent_compliance": True,
    }
    hcmi_scope1_2_data = {
        "total_scope1_2_tco2e": __import__("decimal").Decimal("800.0"),
    }
    kurtaxe_data = {
        "band": "A",
        "kurbeitrag_eur": __import__("decimal").Decimal("2.20"),
    }

    # ----- default lang=de -----
    result_de = generate_heilbad_2036_narrative(
        kurgaste_data, hcmi_scope1_2_data, kurtaxe_data,
    )

    # return-type check
    assert isinstance(result_de, dict), (
        f"AC-3: generate_heilbad_2036_narrative must return a dict; "
        f"got {type(result_de).__name__}: {result_de!r}"
    )

    # JSON-serialisable
    serialised = json.dumps(result_de, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # structural keys
    for key in ("predicate_label", "narrative_de", "narrative_en",
                "representative_period", "lang", "accessibility_label"):
        assert key in result_de, (
            f"AC-3: missing required key '{key}'; got {sorted(result_de.keys())!r}"
        )

    # predicate_label
    assert result_de["predicate_label"] == "Heilbad Bad Orb (Hessischer Heilbäderverband)", (
        f"AC-3: predicate_label must equal 'Heilbad Bad Orb "
        f"(Hessischer Heilbäderverband)'; got {result_de['predicate_label']!r}"
    )

    # narrative_de ≥ 300 chars + 6 canonical Kurort-vertical anchors
    narrative_de = result_de["narrative_de"]
    assert isinstance(narrative_de, str), (
        f"AC-3: narrative_de must be a str; got {type(narrative_de).__name__}"
    )
    assert len(narrative_de) >= 300, (
        f"AC-3: narrative_de must be ≥ 300 chars; got {len(narrative_de)} chars"
    )
    six_anchors = [
        "Spessart",          # Spessart Bike Tage
        "R3 Kinzigtal",      # R3 Kinzigtal
        "WaldErfahren",      # WaldErfahren
        "E-Bike",            # E-Bike charging (Q5.2)
        "Toskana Therme",    # Toskana Therme partnership
        "thermal-spring",    # thermal-spring NiedrigEnergie baseline
    ]
    for anchor in six_anchors:
        assert anchor in narrative_de, (
            f"AC-3: narrative_de MUST mention '{anchor}' (canonical "
            f"Kurort-vertical anchor per AC-3 spec); narrative_de[:200]={narrative_de[:200]!r}"
        )

    # narrative_en ≥ 300 chars + same 6 anchors
    narrative_en = result_de["narrative_en"]
    assert isinstance(narrative_en, str), (
        f"AC-3: narrative_en must be a str; got {type(narrative_en).__name__}"
    )
    assert len(narrative_en) >= 300, (
        f"AC-3: narrative_en must be ≥ 300 chars; got {len(narrative_en)} chars"
    )
    for anchor in six_anchors:
        assert anchor in narrative_en, (
            f"AC-3: narrative_en MUST mention '{anchor}' (canonical "
            f"Kurort-vertical anchor per AC-3 spec); narrative_en[:200]={narrative_en[:200]!r}"
        )

    # representative_period
    assert result_de["representative_period"] == ("2034-01-01", "2044-12-31"), (
        f"AC-3: representative_period must equal ('2034-01-01', '2044-12-31'); "
        f"got {result_de['representative_period']!r}"
    )

    # default lang=de
    assert result_de["lang"] == "de", (
        f"AC-3: default lang must be 'de'; got {result_de['lang']!r}"
    )

    # accessibility_label ≥ 20 chars (WCAG 2.1 SC 4.1.3)
    accessibility_label = result_de["accessibility_label"]
    assert isinstance(accessibility_label, str), (
        f"AC-3: accessibility_label must be a str; got {type(accessibility_label).__name__}"
    )
    assert len(accessibility_label) >= 20, (
        f"AC-3: accessibility_label must be ≥ 20 chars per WCAG 2.1 SC 4.1.3; "
        f"got {len(accessibility_label)} chars: {accessibility_label!r}"
    )

    # ----- lang=en override -----
    result_en = generate_heilbad_2036_narrative(
        kurgaste_data, hcmi_scope1_2_data, kurtaxe_data, lang="en",
    )
    assert result_en["lang"] == "en", (
        f"AC-3: lang='en' override must produce lang='en'; got {result_en['lang']!r}"
    )


def test_ac3_narrative_de_300_chars_minimum() -> None:
    """AC-3 boundary test - narrative_de must be ≥ 300 chars (not just non-empty)."""
    _heilbad_2036_narrative_generator_module_is_importable()
    h2036_mod = _get_heilbad_2036_narrative_generator()
    generate_heilbad_2036_narrative = getattr(
        h2036_mod, "generate_heilbad_2036_narrative", None,
    )
    assert callable(generate_heilbad_2036_narrative)

    result = generate_heilbad_2036_narrative(
        {"total_records": 1, "badekurst_guests": 0, "consent_compliance": True},
        {"total_scope1_2_tco2e": __import__("decimal").Decimal("0")},
        {"band": "A", "kurbeitrag_eur": __import__("decimal").Decimal("2.20")},
    )
    assert len(result["narrative_de"]) >= 300, (
        f"AC-3 boundary: narrative_de must be ≥ 300 chars (BFSG-EAA anchor); "
        f"got {len(result['narrative_de'])} chars"
    )


# ===========================================================================
# AC-4 — export_predicate_filing_bfsg_aa enforces lang=de + non-affirmation
# ===========================================================================

def test_ac4_export_predicate_filing_bfsg_aa_compliance_ok_true() -> None:
    """AC-4 spec test_oracle - happy-path: compliance_ok=True + non_affirmation footer."""
    _kurkarte_wallet_is_importable()
    _predicate_filing_export_module_is_importable()
    pfe_mod = _get_predicate_filing_export()

    export_predicate_filing_bfsg_aa = getattr(
        pfe_mod, "export_predicate_filing_bfsg_aa", None,
    )
    assert callable(export_predicate_filing_bfsg_aa), (
        "AC-4: predicate_filing_export must expose a callable "
        "export_predicate_filing_bfsg_aa entry point; found: "
        f"{[n for n in dir(pfe_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args -----
    predicate_packet = {
        "metadata": {"predicate_label": "Heilbad Bad Orb (Hessischer Heilbäderverband)"},
        "kurgaste_section": {},
        "kurtaxe_section": {},
        "esg_section": {},
        "spa_section": {},
        "mobility_section": {},
    }
    narrative = {
        "predicate_label": "Heilbad Bad Orb (Hessischer Heilbäderverband)",
        "narrative_de": "Placeholder",
        "narrative_en": "Placeholder",
        "representative_period": ("2034-01-01", "2044-12-31"),
        "lang": "de",
        "accessibility_label": "Heilbad 2036 predicate-renewal filing",
    }
    accessibility_label = "Heilbad 2036 predicate-renewal filing für Bad Orb Kur GmbH"

    result = export_predicate_filing_bfsg_aa(
        predicate_packet, narrative,
        lang="de", accessibility_label=accessibility_label,
    )

    # return-type check (JSON-serialisable dict)
    assert isinstance(result, dict), (
        f"AC-4: export_predicate_filing_bfsg_aa must return a "
        f"JSON-serialisable dict; got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # structural keys
    for key in ("predicate_packet", "narrative", "lang", "accessibility_label",
                "screen_reader_contrast", "compliance_ok", "non_affirmation_footer"):
        assert key in result, (
            f"AC-4: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    # predicate_packet + narrative preserved verbatim
    assert result["predicate_packet"] == predicate_packet
    assert result["narrative"] == narrative

    # lang=de
    assert result["lang"] == "de", (
        f"AC-4: lang must equal 'de'; got {result['lang']!r}"
    )

    # accessibility_label
    assert result["accessibility_label"] == accessibility_label, (
        f"AC-4: accessibility_label must be preserved verbatim; "
        f"got {result['accessibility_label']!r}"
    )
    assert len(result["accessibility_label"]) >= 20

    # screen_reader_contrast = "4.5:1"
    assert result["screen_reader_contrast"] == "4.5:1", (
        f"AC-4: screen_reader_contrast must equal '4.5:1' (WCAG 2.1 AA); "
        f"got {result['screen_reader_contrast']!r}"
    )

    # compliance_ok=True (iff all sub-fields pass)
    assert result["compliance_ok"] is True, (
        f"AC-4: compliance_ok must be True on happy path; got {result['compliance_ok']!r}"
    )

    # non_affirmation_footer — verbatim clause per spec.yaml A-4
    non_aff = result["non_affirmation_footer"]
    assert isinstance(non_aff, str), (
        f"AC-4: non_affirmation_footer must be a str; got {type(non_aff).__name__}"
    )
    expected_clause = (
        "This ESG and Heilbad 2036 predicate filing is voluntary and is provided "
        "as ESG-readiness and predicate-renewal positioning for Bad Orb Kur GmbH; "
        "it is NOT a regulatory compliance attestation"
    )
    assert expected_clause in non_aff, (
        f"AC-4: non_affirmation_footer MUST contain the verbatim clause per "
        f"spec.yaml A-4; got non_aff={non_aff!r}"
    )


def test_ac4_lang_en_raises_bfsg_compliance_error() -> None:
    """AC-4 boundary test - lang != 'de' raises BFSGComplianceError naming 'lang'.

    Asserts that ``export_predicate_filing_bfsg_aa(..., lang="en", ...)`` raises
    ``kurort_engine.kurkarte_wallet.BFSGComplianceError`` (re-used from SHIPPED
    iter-21) with a message naming the missing 'lang' field.
    """
    _kurkarte_wallet_is_importable()
    _predicate_filing_export_module_is_importable()
    import kurort_engine.kurkarte_wallet as _kw
    BFSGComplianceError = _kw.BFSGComplianceError

    pfe_mod = _get_predicate_filing_export()
    export_predicate_filing_bfsg_aa = getattr(
        pfe_mod, "export_predicate_filing_bfsg_aa", None,
    )
    assert callable(export_predicate_filing_bfsg_aa)

    predicate_packet = {"metadata": {}}
    narrative = {"predicate_label": "X", "accessibility_label": "X"}

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_predicate_filing_bfsg_aa(
            predicate_packet, narrative,
            lang="en",  # BAD: must be "de" per BFSG-EAA
            accessibility_label="Heilbad 2036 predicate-renewal filing für Bad Orb",
        )
    # message must name the missing/invalid field
    assert "lang" in str(excinfo.value).lower(), (
        f"AC-4: BFSGComplianceError message MUST name 'lang' field for "
        f"diagnostic clarity; got message={str(excinfo.value)!r}"
    )


def test_ac4_short_accessibility_label_raises_bfsg_compliance_error() -> None:
    """AC-4 boundary test - accessibility_label < 20 chars raises BFSGComplianceError."""
    _kurkarte_wallet_is_importable()
    _predicate_filing_export_module_is_importable()
    import kurort_engine.kurkarte_wallet as _kw
    BFSGComplianceError = _kw.BFSGComplianceError

    pfe_mod = _get_predicate_filing_export()
    export_predicate_filing_bfsg_aa = getattr(
        pfe_mod, "export_predicate_filing_bfsg_aa", None,
    )
    assert callable(export_predicate_filing_bfsg_aa)

    predicate_packet = {"metadata": {}}
    narrative = {"predicate_label": "X", "accessibility_label": "X"}

    with pytest.raises(BFSGComplianceError) as excinfo:
        export_predicate_filing_bfsg_aa(
            predicate_packet, narrative,
            lang="de",
            accessibility_label="too_short",  # BAD: < 20 chars
        )
    assert "accessibility_label" in str(excinfo.value).lower(), (
        f"AC-4: BFSGComplianceError message MUST name 'accessibility_label' "
        f"field for diagnostic clarity; got message={str(excinfo.value)!r}"
    )


# ===========================================================================
# AC-5 — aggregate_kurgaste_health_data emits badekurst + consent counts
# ===========================================================================

def test_ac5_aggregate_kurgaste_health_data_emits_badekurst_and_consent_counts() -> None:
    """AC-5 spec test_oracle - happy-path aggregation.

    Asserts that ``aggregate_kurgaste_health_data(records)`` returns a dict
    with required keys:
      * total_records: int
      * badekurst_guests: int (Spezial-Heilbad template_E with muster13_id)
      * classic_guests: int (template_A/B/C/D)
      * consent_art9_count: int
      * period: tuple[str, str]
      * consent_compliance: bool
    """
    _kurgaste_health_data_aggregator_module_is_importable()
    khda_mod = _get_kurgaste_health_data_aggregator()

    aggregate_kurgaste_health_data = getattr(
        khda_mod, "aggregate_kurgaste_health_data", None,
    )
    assert callable(aggregate_kurgaste_health_data), (
        "AC-5: kurgaste_health_data_aggregator must expose a callable "
        "aggregate_kurgaste_health_data entry point; found: "
        f"{[n for n in dir(khda_mod) if not n.startswith('_')]!r}"
    )

    # ----- happy-path args -----
    records = [
        {
            "consent_dsgvo_art9": True,
            "template_code": "A",  # Classic
            "muster13_id": None,
            "arrival": date(2034, 6, 1),
            "departure": date(2034, 6, 8),
        },
        {
            "consent_dsgvo_art9": True,
            "template_code": "E",  # Spezial-Heilbad (Badekurst)
            "muster13_id": "M13-001",
            "arrival": date(2034, 7, 1),
            "departure": date(2034, 7, 22),
        },
    ]
    result = aggregate_kurgaste_health_data(records)

    # return-type check
    assert isinstance(result, dict), (
        f"AC-5: aggregate_kurgaste_health_data must return a dict; "
        f"got {type(result).__name__}: {result!r}"
    )

    serialised = json.dumps(result, default=str)
    assert isinstance(serialised, str) and len(serialised) > 0

    # structural keys
    for key in ("total_records", "badekurst_guests", "classic_guests",
                "consent_art9_count", "period", "consent_compliance"):
        assert key in result, (
            f"AC-5: missing required key '{key}'; got {sorted(result.keys())!r}"
        )

    assert result["total_records"] == 2
    assert result["badekurst_guests"] == 1, (
        f"AC-5: badekurst_guests must count Spezial-Heilbad template_E records "
        f"with muster13_id; got {result['badekurst_guests']!r}"
    )
    assert result["classic_guests"] == 1, (
        f"AC-5: classic_guests must count template_A/B/C/D records; "
        f"got {result['classic_guests']!r}"
    )
    assert result["consent_art9_count"] == 2, (
        f"AC-5: consent_art9_count must count records with consent=True; "
        f"got {result['consent_art9_count']!r}"
    )
    assert result["consent_compliance"] is True, (
        f"AC-5: consent_compliance must be True iff every record has "
        f"consent=True; got {result['consent_compliance']!r}"
    )
    assert result["period"] == ("2034-06-01", "2034-07-22"), (
        f"AC-5: period must be ('2034-06-01', '2034-07-22') (first arrival + "
        f"last departure); got {result['period']!r}"
    )


def test_ac5_missing_consent_flag_raises() -> None:
    """AC-5 boundary test - missing consent_dsgvo_art9 field raises DSGVOArt9ValidationError."""
    _kurgaste_health_data_aggregator_module_is_importable()
    khda_mod = _get_kurgaste_health_data_aggregator()

    DSGVOArt9ValidationError = getattr(khda_mod, "DSGVOArt9ValidationError", None)
    assert DSGVOArt9ValidationError is not None

    aggregate_kurgaste_health_data = getattr(
        khda_mod, "aggregate_kurgaste_health_data", None,
    )
    assert callable(aggregate_kurgaste_health_data)

    records = [
        {
            # consent_dsgvo_art9 field MISSING entirely
            "template_code": "A",
            "muster13_id": None,
        },
    ]
    with pytest.raises(DSGVOArt9ValidationError):
        aggregate_kurgaste_health_data(records)