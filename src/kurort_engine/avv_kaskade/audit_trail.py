"""kurort_engine.avv_kaskade.audit_trail — NIS2 §38 BSIG read-only consumer.

Iter-28 (Developer) — Phase 3 Tactical Red stub.

Anti-drift (binding contract mitigation 4): this module RE-EXPORTS names from
``kurort_engine.kurgaste_retention.auto_cascade`` (iter-38 SHIPPED). It does
NOT modify the 6 SHAs. The read-only surface is preserved verbatim.
"""
from __future__ import annotations

# Re-export names from the SHIPPED iter-38 kurgaste_retention.auto_cascade
# (Pattern C chain-extension). The auto_cascade module exposes:
#   - forget_guest(guest_id) -> dict (the canonical 5-step cascade)
#   - run_cascade_with_retry(guest_id, retry_max=2) -> dict
# These names anchor the NIS2 §38 BSIG audit trail semantics for avv_kaskade.
from kurort_engine.kurgaste_retention.auto_cascade import (  # noqa: E402,F401
    forget_guest,
    run_cascade_with_retry,
)


class AuditTrailEntry:
    """NIS2 §38 BSIG audit trail entry (read-only consumer).

    Phase 3 RED stub: empty container. The GREEN-phase implementation
    populates the audit-trail fields per AC-5.
    """

    def __init__(self) -> None:
        self.tom_evidence_chain_hash: str | None = None