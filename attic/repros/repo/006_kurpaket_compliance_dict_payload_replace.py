"""Repro 006 — kurpaket_compliance dict-payload .replace() (AC-7).

AC-7 contract (per repo/spec/p1_predicate_filing_2026_fix_axis/spec.yaml
AC-7 PROTECTED block, lines 194-217): Where
``kurpaket_compliance.record_sgb_v_event`` (the AC-9 code path) operates
on the shared ``AuditLog`` and that log contains a dict-payload entry
(e.g., from ``kurort_engine.a11y.guest_pwa`` self-attestation), the
kurpaket_compliance code path shall coerce the dict payload to a JSON
string (via ``json.dumps``) BEFORE any ``.replace()`` call on the payload
runs, so that downstream iteration completes without ``AttributeError``
on the dict payload.

This test exercises the AC-7 invariant end-to-end:

1. Seeds the shared ``AuditLog`` with a dict-payload ``AuditEntry``
   whose ``payload`` is a Python ``dict`` (the same shape
   ``kurort_engine.a11y.guest_pwa.wcag_aa`` writes at L89 of that file —
   4 keys: ``event``, ``scope``, ``attested``, ``schema``).
2. Calls ``kurpaket_compliance.record_sgb_v_event(...)`` to append a
   valid SGB V §23 entry (the AC-9 entry point).
3. Runs the AC-9 payload-string-scan logic inline (mirrors
   ``test_ac9_sgb_v_23_audit_event_written_to_kurort_audit_log`` at
   ``repo/tests/test_kurpaket_compliance.py`` L207-217) — specifically
   the ``payload_str.replace(" ", "")`` call that crashes when
   ``payload`` is a dict (``dict`` has no ``.replace()`` method).
4. Translates any caught ``AttributeError`` into a descriptive
   ``AssertionError`` naming the AC-7 invariant violated.

RED verification (target, before Phase 3 GREEN):

    PYTHONPATH=src .venv/bin/python -m pytest \\
        repo/output/repros/006_kurpaket_compliance_dict_payload_replace.py::test_repro_006a \\
        -x -v --override-ini="addopts=--tb=short"

Expected RED outcome:

    FAILED ... AssertionError: AC-7 violation: the AC-9 payload-string-scan
    raised AttributeError on a dict payload ('a11y.guest_pwa' producer
    shape). The kurpaket_compliance code-path must coerce dict payloads to
    str via json.dumps BEFORE calling .replace() ...

GREEN (post Phase 3 fix in ``repo/src/kurort_engine/kurpaket_compliance.py``,
~3-5 LOC surgical): ``record_sgb_v_event`` (or a co-located helper) coerces
dict-shaped payloads to JSON strings before any ``.replace()`` runs; the
inline scan completes without ``AttributeError``; the SGB V entry is
detected and the test passes.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_shared_audit_log() -> None:
    """Reset ``AuditLog._shared_entries`` before AND after this test.

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


def test_repro_006a() -> None:
    """AC-7 contract: dict-payload entries survive the AC-9 scan.

    Seeds a dict-payload ``AuditEntry`` (the ``a11y.guest_pwa`` producer
    shape, see ``repo/src/kurort_engine/a11y/guest_pwa/wcag_aa.py:89``),
    calls ``record_sgb_v_event`` (the AC-9 entry point in
    ``kurpaket_compliance``), then runs the AC-9 payload-string-scan
    inline. Asserts that the scan completes without ``AttributeError``
    on the dict payload AND that the SGB V entry (kurarzt_pct=100) is
    detected.
    """
    from kurort_engine.audit import AuditEntry, AuditLog
    from kurort_engine.kurpaket_compliance import record_sgb_v_event

    # ---- Step 1: seed dict-payload entry (a11y.guest_pwa producer shape) ----
    dict_payload_entry = AuditEntry(
        actor="a11y.guest_pwa",
        payload={
            "event": "wcag_aa_audit",
            "scope": "kurort_engine.a11y.guest_pwa",
            "attested": True,
            "schema": "BFSG-EAA-1.0",
        },
    )
    AuditLog().append(dict_payload_entry)

    # ---- Step 2: invoke the AC-9 entry point (SGB V §23 audit event) ----
    sgb_v_entry = record_sgb_v_event(
        guest_id="G-AC7-001",
        template="bad_orb_2026_v1",
        muster13_id="M13-AMBULANT-VORSORGE",
    )

    # ---- Step 3: run the AC-9 payload-string-scan (mirrors test_ac9_*) ----
    # This is the scan that crashes when payload is a dict because
    # ``dict`` has no ``.replace()`` method. The AC-7 fix is to coerce
    # dict -> str via json.dumps BEFORE any .replace() call.
    matching: list[AuditEntry] = []
    scan_error: AttributeError | None = None
    try:
        for entry in AuditLog():
            # entry.payload may be str (canonical) OR dict (a11y pollution);
            # the AC-9 scan pattern unconditionally calls .replace() on it.
            payload_str = getattr(entry, "payload", "") or ""
            payload_str_compact = payload_str.replace(" ", "")
            if '"kurarzt_pct":100' in payload_str_compact:
                matching.append(entry)
    except AttributeError as exc:
        scan_error = exc

    # ---- Step 4: AC-7 invariant — scan must NOT raise AttributeError ----
    assert scan_error is None, (
        "AC-7 violation: the AC-9 payload-string-scan raised AttributeError "
        "on a dict payload (the 'a11y.guest_pwa' producer shape from "
        "kurort_engine.a11y.guest_pwa.wcag_aa at L89). The "
        "kurpaket_compliance code-path must coerce dict payloads to str via "
        "json.dumps BEFORE calling .replace() — dict has no .replace() "
        f"method. Got: {type(scan_error).__name__}: {scan_error!r}. "
        "Seeded dict-payload actor='a11y.guest_pwa' payload keys="
        f"{sorted(dict_payload_entry.payload.keys())!r}. "
        "All AuditLog entry payloads (after record_sgb_v_event ran): "
        f"{[type(getattr(e, 'payload', None)).__name__ for e in AuditLog()]!r}."
    )

    # ---- AC-9 invariant (post AC-7 fix): SGB V entry must be detectable ----
    assert matching, (
        "AC-7/AC-9: after the scan completes without AttributeError, the "
        "AC-9 SGB V entry (kurarzt_pct=100) must be detected in the shared "
        "AuditLog. matching="
        f"{[getattr(e, 'actor', '?') for e in matching]!r}, "
        "all entries' actor values="
        f"{[getattr(e, 'actor', '?') for e in AuditLog()]!r}."
    )
    assert sgb_v_entry in matching, (
        "AC-7/AC-9: the just-recorded SGB V entry must be in the matching set "
        "(it carries kurarzt_pct=100). matching actor values="
        f"{[getattr(e, 'actor', '?') for e in matching]!r}, "
        f"sgb_v_entry actor={getattr(sgb_v_entry, 'actor', '?')!r}."
    )
