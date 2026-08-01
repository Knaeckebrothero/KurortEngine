# Repro 001: apply_2026_attestation_template drops trailing zero for float-typed adult rate
# Run: pytest output/repros/001_adult_rate_float_precision_loss.py -v
# Expected: this test should pass after the bug is fixed.
#
# Bug: Per AC-3 contract, adult_rate_applied MUST equal the string "2.50" with
# 100% precision. The implementation calls `str(rate)` where `rate` is a float.
# Python's `str(2.5)` produces "2.5" (NOT "2.50"), silently dropping the trailing
# zero. The actual canonical Kurbeitragssatzung 01.07.2026 rate "2,50 EUR"
# cannot be reliably reconstructed when downstream consumers do
# `Decimal(result['adult_rate_applied'])`.
#
# Contract source: spec.yaml PROTECTED block (AC-3); test_ac3_adult_rate asserts
# `str(adult_rate_applied) == "2.50"`. The shipped YAML profile file uses a
# quoted string ("2.50") which masks the bug for the shipped profile — but
# any caller passing an unquoted float, or any profile parsed from a non-quoted
# YAML source (which is the natural way to type a literal "2,50 EUR"), trips
# the bug.
"""Repro 001 — adult_rate_applied precision loss on float-typed rate."""

from __future__ import annotations

import pytest

from kurort_engine.predicate_filing import apply_2026_attestation_template


def test_repro_001_adult_rate_float_precision_loss() -> None:
    """AC-3 contract: adult_rate_applied MUST equal "2.50" with 100% precision.

    When a profile is constructed with the canonical rate as a Python float
    (2.50 — which is the natural representation in code), `str(rate)` in
    `_find_adult_rate_eur` returns "2.5", losing the trailing zero.
    """
    # Mimic a profile that the natural code path would produce if the YAML
    # rate is unquoted (rate_eur: 2.50) OR if the caller built the profile
    # in Python with `2.50` (the Bad Orb 2026 Satzung rate is canonically
    # written "2,50 EUR").
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
                "clause_text": "Beglaubigung clause.",
                "signature_required": True,
                "notarization_required": False,
                "effective_date": "2026-07-01",
            },
        ],
        # The natural code path: rate typed as Python float.
        "bands": [{"name": "adult", "rate_eur": 2.50}],
        "preserves_iter33_fields": True,
    }

    result = apply_2026_attestation_template(profile, {})

    actual = result["adult_rate_applied"]
    # AC-3 contract: "2.50" with 100% precision.
    assert actual == "2.50", (
        f"BUG: adult_rate_applied must equal '2.50' (100% precision per AC-3); "
        f"got {actual!r} (type={type(actual).__name__}). "
        f"`str(float(2.50))` is '2.5' in Python — the implementation calls "
        f"`str(rate)` in `_find_adult_rate_eur` (kurort_engine.predicate_filing"
        f".2026_attestation:67-73) which silently drops the trailing zero."
    )


def test_repro_001b_adult_rate_via_yaml_unquoted_path() -> None:
    """Second repro: YAML unquoted rate_eur: 2.50 parses to float 2.5.

    PyYAML's default behaviour for unquoted scalars like `2.50` is to parse
    them as floats. `str(2.5) == "2.5"`. So even if a future profile drop
    drops the double quotes, the AC-3 contract breaks.
    """
    import yaml

    yaml_text = """
bands:
  - name: adult
    rate_eur: 2.50
"""
    profile_fragment = yaml.safe_load(yaml_text)
    parsed_rate = profile_fragment["bands"][0]["rate_eur"]
    assert isinstance(parsed_rate, float), (
        f"Sanity: PyYAML parses unquoted 2.50 as float; got "
        f"{type(parsed_rate).__name__}: {parsed_rate!r}"
    )

    # Now confirm the implementation emits "2.5" not "2.50".
    profile = {
        "bundesland": "hessen",
        "kurort": "bad_orb",
        "predicate": "heilbad",
        "satzung_date": "2026-07-01",
        "attestation_template_id": "bad_orb_2026_v1",
        "predicate_label": "Heilbad Bad Orb",
        "beglaubigung_clauses": [],
        "bands": profile_fragment["bands"],
        "preserves_iter33_fields": True,
    }
    result = apply_2026_attestation_template(profile, {})
    actual = result["adult_rate_applied"]
    assert actual == "2.50", (
        f"BUG: even with the YAML unquoted path (which any downstream YAML "
        f"editor will produce from raw text), adult_rate_applied is "
        f"{actual!r}, not '2.50'. The contract requires '2.50' with 100% "
        f"precision (AC-3)."
    )
