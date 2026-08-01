# Repro 002: extract_2026_satzung_schema silently drops Beglaubigung clauses whose clause_text
# is not a double-quoted scalar (silently loses real-world Satzung content).
#
# Run: pytest output/repros/002_beglaubigung_silent_drop_unescaped_clauses.py -v
# Expected: this test should pass after the bug is fixed.
#
# Bug: the regex at kurort_engine.predicate_filing.2026_validate.extract_2026_satzung_schema
# line 82-88 requires the literal literal pattern:
#     r'  -\s*clause_id:\s*\"?([^\"\n]+)\"?\n'
#     r'\s*clause_text:\s*\"([^\"]+)\"\n'
# i.e. clause_text: must be a double-quoted string. The synthetic test source bundled with the
# shipped tests uses double quotes (per `repo/tests/test_predicate_filing_2026.py:249-281`),
# which masks the bug. Real Bad Orb Kurbeitragssatzungen do NOT quote clause_text — they emit
# bare German-language prose (cf. the actual SatelliteText snippet in the spec.yaml). When a
# real Satzung PDF is parsed to the synthetic-format intermediate (per AC-1's "shall extract
# the full attestation schema"), every Beglaubigung clause is silently dropped, and the
# attestation is generated with empty beglaubigung_clauses = `beglaubigung_sealed=False`
# downstream (per `apply_2026_attestation_template` line 130-132), failing the AC-3 contract.
"""Repro 002 — Beglaubigung clause regex silently drops unquoted clause_text."""

from __future__ import annotations

import pytest

from kurort_engine.predicate_filing import extract_2026_satzung_schema


def test_repro_002a_single_unquoted_german_clause_extracted() -> None:
    """AC-1 contract: Beglaubigung clauses MUST be extracted with all 5 fields.

    Real 2026 Satzung clauses are bare text (no quote marks) — the parser
    MUST accept this form. The shipped regex (with literal '\"...'\"' on
    clause_text) rejects it.
    """
    src = """
Beglaubigung:
  - clause_id: BG-2026-001
    clause_text: Der Beitragsgläubiger (Hotel Rheinland) hat die ordnungsgemäße Erhebung des Kurbeitrags zu bestätigen.
    signature_required: true
    notarization_required: false
    effective_date: 2026-07-01
"""
    result = extract_2026_satzung_schema(src)
    clauses = result["beglaubigung_clauses"]
    assert isinstance(clauses, list), f"beglaubigung_clauses must be a list; got {type(clauses).__name__}"
    assert len(clauses) == 1, (
        f"AC-1: must extract the 1 unquoted Beglaubigung clause "
        f"(canonical Bad Orb 2026 form); got {len(clauses)} clauses "
        f"(silent drop). The regex at "
        f"kurort_engine.predicate_filing.2026_validate.extract_2026_satzung_schema:82-88 "
        f"requires literal \"clause_text: \\\"...\\\"\" form which real Satzung "
        f"clause text does not use."
    )
    clause = clauses[0]
    for key in ("clause_id", "clause_text", "signature_required",
                "notarization_required", "effective_date"):
        assert key in clause, f"missing key '{key}' in extracted clause {clause!r}"
    assert clause["clause_id"] == "BG-2026-001"
    assert clause["signature_required"] is True
    assert clause["notarization_required"] is False
    assert clause["effective_date"] == "2026-07-01"


def test_repro_002b_two_unquoted_clauses_extracted() -> None:
    """Two unquoted clauses — both should be preserved, not just the first."""
    src = """
Beglaubigung:
  - clause_id: BG-2026-001
    clause_text: Der Beitragsgläubiger hat die ordnungsgemäße Erhebung des Kurbeitrags zu bestätigen.
    signature_required: true
    notarization_required: false
    effective_date: 2026-07-01
  - clause_id: BG-2026-002
    clause_text: Die Beglaubigung der Meldescheine erfolgt durch den Beitragsgläubiger mit Unterschrift und Datum.
    signature_required: true
    notarization_required: true
    effective_date: 2026-07-01
"""
    result = extract_2026_satzung_schema(src)
    clauses = result["beglaubigung_clauses"]
    assert len(clauses) == 2, (
        f"AC-1: must extract ALL 2 unquoted Beglaubigung clauses; "
        f"got {len(clauses)} clauses. The regex silently drops the entire "
        f"Beglaubigung block if any clause does not match the literal quoted form."
    )
    ids = {c.get("clause_id") for c in clauses}
    assert ids == {"BG-2026-001", "BG-2026-002"}, (
        f"Expected clauses BG-2026-001 + BG-2026-002; got {ids!r}"
    )
