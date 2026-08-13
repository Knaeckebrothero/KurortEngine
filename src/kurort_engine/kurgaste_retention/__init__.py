"""kurort_engine.kurgaste_retention — DSGVO Art. 17 in-app self-service cascade.

Iter-38 (Developer) — Pattern C GREENFIELD package (0 SHAs touched, 7 SHIPs
preserved verbatim).

Modules:
  - audit_log.py (AC-5) — Art. 30 VVT append-only audit log
  - art17_exceptions.py (AC-6) — Art. 17(3) HGB §257 override
  - art9_health_data.py (AC-8) — Art. 9 health-data consent/legal-basis
  - auto_cascade.py (AC-1..AC-4, AC-7) — 5-step atomic cascade orchestrator

Per spec.yaml AC-9 (Ubiquitous):
    The 9 NEW kurgaste_retention symbols MUST all be importable via
    `from kurort_engine.kurgaste_retention import forget_guest,
    auto_cascade, emit_forget_guest_event,
    cascade_anonymize_spa_entries, redact_invoice_for_cascade,
    write_art30_audit_entry, run_cascade_with_retry,
    require_art_173_override_reason, assert_consent_or_legal_basis`.

Re-exports all 9 symbols via the canonical submodule-import pattern.
"""
from __future__ import annotations

# Art. 9 health-data consent/legal-basis (AC-8)
from kurort_engine.kurgaste_retention.art9_health_data import (
    assert_consent_or_legal_basis,
)

# Art. 17(3) HGB §257 override (AC-6)
from kurort_engine.kurgaste_retention.art17_exceptions import (
    require_art_173_override_reason,
)

# Audit log (AC-5)
from kurort_engine.kurgaste_retention.audit_log import write_art30_audit_entry

# 5-step atomic cascade orchestrator (AC-1..AC-4, AC-7)
from kurort_engine.kurgaste_retention.auto_cascade import (
    auto_cascade,
    cascade_anonymize_spa_entries,
    emit_forget_guest_event,
    forget_guest,
    redact_invoice_for_cascade,
    run_cascade_with_retry,
)

__all__ = [
    # AC-1
    "forget_guest",
    "auto_cascade",
    # AC-2
    "redact_invoice_for_cascade",
    # AC-3
    "cascade_anonymize_spa_entries",
    # AC-4
    "emit_forget_guest_event",
    # AC-5
    "write_art30_audit_entry",
    # AC-6
    "require_art_173_override_reason",
    # AC-7
    "run_cascade_with_retry",
    # AC-8
    "assert_consent_or_legal_basis",
]