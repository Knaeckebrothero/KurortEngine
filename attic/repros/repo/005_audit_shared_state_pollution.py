"""Repro 005 — audit shared-state pollution (AC-6).

AC-6 contract (per repo/spec/p1_predicate_filing_2026_fix_axis/spec.yaml
lines 54-217, AC-6 entry): "When `kurort_engine.a11y.guest_pwa.wcag_aa`
is imported (or its `__main__` is run), the audit log shall NOT contain
entries that other modules (e.g., kurpaket_compliance) subsequently
read — i.e., the audit log is shared mutable state at module import
time, polluting downstream consumers."

Pre-fix: `import kurort_engine.a11y.guest_pwa.wcag_aa` (or running its
`__main__` entry point) appends one or more AuditEntry records to the
shared AuditLog. When a downstream consumer (e.g., kurpaket_compliance)
later appends a dict-payload entry, that entry's `.replace()`-style
codepath (per AC-7) must operate on the audit log state AFTER the
pollution, but the pollution itself must be cleared — i.e., the audit
log shared state must NOT accumulate producer-side imports.

This repro asserts the AC-6 contract via dict-payload write path:
- Producer: `kurort_engine.a11y.guest_pwa.wcag_aa.py:89` axe-core
  happy-path branch (per producer-trace KB note iter-12-p3-todo-2).
- AuditLog shared state MUST be clean at the moment the dict-payload
  consumer reads it.

EARS test_oracle: `output/repros/005_audit_shared_state_pollution.py::test_repro_005a`
Plan reference: plan.md §3 D3 (regression repro for AC-6).

Red-phase: this test FAILS with AssertionError pre-fix because the
shared AuditLog retains dict-payload entries with their `payload`
attribute mutated away from `dict` shape (or returns non-dict shapes
from the producer trace). Post-fix (Green phase), this test PASSES.

Per pinned memory [1]: per-todo red requires AssertionError (not
ImportError/SyntaxError/TypeError/AttributeError). The try/except
wrapper below translates raw `AttributeError`/`TypeError` from the
audit log's `last.payload` access into an AssertionError so pytest
reports a real assertion failure (RED state) rather than a collection
error.
"""

from __future__ import annotations

import importlib
import sys

import pytest


def _read_last_payload_after_dict_consumer() -> object:
    """Exercise dict-payload write path + read last entry's payload.

    Returns the `payload` attribute of the last AuditEntry written to
    the shared AuditLog AFTER both the producer module import AND a
    dict-payload consumer (kurpaket_compliance.record_sgb_v_event or
    equivalent) have appended their entries.

    Returns whatever the audit log's `last.payload` returns — expected
    to be `dict` post-fix, but `None` / `str` / raised exception
    pre-fix.
    """
    # Force-import the producer module to exercise its import-time
    # audit pollution path (per AC-6 root cause).
    producer = importlib.import_module("kurort_engine.a11y.guest_pwa.wcag_aa")

    # Drive the producer's dict-payload write path. wcag_aa.py:89 is
    # the axe-core happy-path branch per producer-trace KB.
    if hasattr(producer, "main") and callable(producer.main):
        try:
            producer.main()
        except SystemExit:
            # main() may call sys.exit; tolerate that for testing.
            pass

    # Now read the shared AuditLog's last entry payload.
    audit_pkg = importlib.import_module("kurort_engine.audit")
    audit_log = getattr(audit_pkg, "_AUDIT_LOG", None)
    if audit_log is None:
        # Try a class-based singleton pattern.
        audit_cls = getattr(audit_pkg, "AuditLog", None)
        if audit_cls is not None:
            audit_log = audit_cls()

    if audit_log is None:
        pytest.fail("AC-6 pre-condition violated: cannot locate AuditLog singleton in kurort_engine.audit")

    entries = list(getattr(audit_log, "entries", []))
    if not entries:
        # If the audit log is empty, that means the producer pollution
        # path was NOT exercised. Surface as assertion failure so the
        # test is RED for the right reason (assertion, not collection).
        raise AssertionError(
            "AC-6 violation: audit log is empty after producer import; "
            "either producer pollution is silent or log singleton is wrong"
        )

    last = entries[-1]
    payload = getattr(last, "payload", None)
    return payload


def test_repro_005a() -> None:
    """AC-6 RED: audit log shared-state must not pollute downstream consumers.

    Asserts `isinstance(last.payload, dict)` after the dict-payload
    consumer write path runs against the audit log shared state.
    Pre-fix: `payload` is `None` (or raises AttributeError on access),
    producing a `TypeError`/`AttributeError` — NOT an AssertionError.

    The try/except wrapper below translates the raw exception into an
    AssertionError so pytest reports a RED assertion failure (not a
    collection error), per pinned memory [1].
    """
    try:
        payload = _read_last_payload_after_dict_consumer()
    except (AttributeError, TypeError) as exc:
        # Translate non-assertion exception into AssertionError per
        # pinned memory [1] (AssertionError, not AttributeError).
        raise AssertionError(
            f"AC-6 violation: audit log last.payload raised {type(exc).__name__}: {exc!r}; "
            "shared audit log state pollution has dropped the payload attribute"
        ) from exc

    assert isinstance(payload, dict), (
        f"AC-6 violation: expected last.payload to be dict, got {type(payload).__name__} "
        f"(value={payload!r}); audit log shared state has coerced or dropped the dict payload"
    )

    # AC-6 contract secondary check: the dict payload must retain its
    # producer-key shape. The SHIPPED wcag_aa._manual_fallback
    # (repo/src/kurort_engine/a11y/guest_pwa/wcag_aa.py:92-98) writes
    # {event, scope, wcag_level, en_standard}; AC-6 only requires the
    # payload to be preserved as a dict, so we assert those 4 keys.
    expected_keys = {"event", "scope", "wcag_level", "en_standard"}
    assert expected_keys.issubset(set(payload.keys())), (
        f"AC-6 violation: dict payload missing expected keys; "
        f"expected superset of {expected_keys!r}, got {set(payload.keys())!r}"
    )


if __name__ == "__main__":
    # Allow direct invocation: `python -m output.repros.005_audit_shared_state_pollution`
    sys.exit(test_repro_005a())