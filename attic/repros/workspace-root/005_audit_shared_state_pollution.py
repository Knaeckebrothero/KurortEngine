"""Repro 005 — AuditLog shared-state pollution + dict-payload preservation (AC-6).

AC-6 contract (per `repo/spec/p1_predicate_filing_2026_fix_axis/spec.yaml`
AC-6 PROTECTED block — sha256: ca797ada3ba35922257c540ff86214bc83a516f370ca
f809d0a91f7dc2e0032d, 7852 B): AuditLog accepts dict payloads from
``record_sgb_v_event`` without breaking iteration; AuditLog's entries snapshot
returns dict-payload entries with the dict PRESERVED (not coerced to a
pre-canonicalised JSON string).

This test verifies two coupled properties of the AC-6 contract:

1. ``record_sgb_v_event`` passes its payload to ``AuditEntry`` as a ``dict``
   (NOT a pre-canonicalised JSON string). The current implementation calls
   ``json.dumps({...}, sort_keys=True, separators=(",", ":"))`` which yields
   a ``str`` — this is the AC-6 violation.
2. A subsequent dict-payload entry (simulating
   ``kurort_engine.a11y.guest_pwa`` self-attestation pollution) is preserved
   in iteration without filtering, pre-emption, or coercion to ``str``.

Run (RED verification):
    PYTHONPATH=src .venv/bin/python -m pytest \\
        output/repros/005_audit_shared_state_pollution.py::test_repro_005a \\
        -x -v --override-ini="addopts=--tb=short"

Expected (RED, before Phase 3 GREEN fix):
    The test FAILS with AssertionError on the ``isinstance(payload, dict)``
    line because the current ``record_sgb_v_event`` wraps its payload via
    ``json.dumps(...)`` (a ``str``), not the dict directly.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_shared_audit_log() -> None:
    """Reset ``AuditLog._shared_entries`` before AND after each test.

    The shared list is mutated by ``record_sgb_v_event`` AND by import-time
    side effects in ``kurort_engine.a11y.guest_pwa``. Without this fixture
    the test would either observe pre-existing entries from prior tests
    (pollution) or leak its own appends into subsequent tests. This fixture
    is autouse-only for THIS repro file; other repro files are unaffected.
    """
    from kurort_engine.audit import AuditLog
    AuditLog._shared_entries.clear()
    try:
        yield
    finally:
        AuditLog._shared_entries.clear()


def test_repro_005a() -> None:
    """AC-6 contract: record_sgb_v_event payload is a dict, not a JSON str.

    Asserts that calling ``kurpaket_compliance.record_sgb_v_event(...)``
    appends an ``AuditEntry`` whose ``payload`` field is a Python ``dict``
    containing the AC-9 fields (``guest_id``, ``template``, ``muster13_id``,
    ``kurarzt_pct``, ``kurmittel_pct``, ``zuschuss_eur``) — exactly the shape
    that ``kurort_engine.a11y.guest_pwa`` self-attestation ALSO uses.

    This couples to the AC-9 contract and supports ``test_ac9_*`` which
    would otherwise raise ``AttributeError`` on ``dict.replace(...)`` when
    iterating a heterogeneous-shared stream.
    """
    from kurort_engine.audit import AuditLog
    from kurort_engine.kurpaket_compliance import record_sgb_v_event

    entry = record_sgb_v_event(
        guest_id="G-001",
        template="bad_orb_2026_v1",
        muster13_id="M13-AMBULANT-VORSORGE",
    )

    # Iteration snapshot must include this entry.
    snapshot = list(AuditLog())
    assert len(snapshot) >= 1, (
        f"AuditLog should have at least 1 entry (the one just appended); "
        f"got {len(snapshot)}"
    )

    last = snapshot[-1]
    assert last is entry, (
        "AuditLog iteration should include the entry returned by "
        "record_sgb_v_event as the most-recently-appended entry."
    )

    # ---- AC-6 invariant: payload MUST be a dict, not a JSON string ----
    assert isinstance(last.payload, dict), (
        "AC-6 violation: record_sgb_v_event's AuditEntry.payload must be a "
        "dict (so that downstream iteration code sees the same shape "
        "kurort_engine.a11y.guest_pwa self-attestation emits). Currently "
        "record_sgb_v_event wraps the dict via "
        "json.dumps({...}, sort_keys=True, separators=(',', ':')) which "
        "yields a str. "
        f"Got payload type={type(last.payload).__name__}, "
        f"value (truncated)={str(last.payload)[:120]!r}."
    )

    # ---- AC-6 invariant: dict must contain the AC-9 contract fields ----
    expected_keys = {
        "guest_id",
        "template",
        "muster13_id",
        "kurarzt_pct",
        "kurmittel_pct",
        "zuschuss_eur",
    }
    assert set(last.payload.keys()) >= expected_keys, (
        f"AC-6: dict payload must expose AC-9 fields; got keys="
        f"{sorted(last.payload.keys())!r}, expected at least "
        f"{sorted(expected_keys)!r}."
    )
    assert last.payload["guest_id"] == "G-001", (
        f"AC-6: payload['guest_id'] must round-trip exactly; got "
        f"{last.payload['guest_id']!r}"
    )
    assert last.payload["template"] == "bad_orb_2026_v1", (
        f"AC-6: payload['template'] must round-trip exactly; got "
        f"{last.payload['template']!r}"
    )
    assert last.payload["muster13_id"] == "M13-AMBULANT-VORSORGE", (
        f"AC-6: payload['muster13_id'] must round-trip exactly; got "
        f"{last.payload['muster13_id']!r}"
    )
