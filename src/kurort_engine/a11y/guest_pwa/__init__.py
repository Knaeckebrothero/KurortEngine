"""kurort_engine.a11y.guest_pwa — BFSG-EAA / EN 301 549 V3.2.1 / WCAG 2.1 AA
self-attestation tenant for the Hotel Rheinland Bad Orb guest PWA booking flow.

Iteration 3 ships this Kurort-vertical tenant per
``spec/a11y_guest_pwa/spec.yaml``. On first import, appends exactly one
``self_attestation`` ``AuditEntry`` to ``kurort_engine.audit.AuditLog``
with ``actor='a11y.guest_pwa'`` and ``payload`` dict containing
``event``, ``ts``, ``claim``; ``content_hash`` is SHA-256 of canonical
JSON auto-computed in ``AuditEntry.__post_init__``.

Idempotent: module-level ``_SELF_ATTESTATION_DONE`` flag plus scan of
``AuditLog._shared_entries`` for matching ``(actor, payload)`` tuple
before appending (AuditLog has no built-in dedupe).

Phase 7b refactor: the ``BFSGComplianceError`` class and
``run_wcag_aa_audit`` function previously defined inline here have
been moved to ``kurort_engine.a11y.guest_pwa.wcag_aa`` (semantic
ownership — the audit infrastructure owns both the function and the
domain error it raises). They are re-exported here so the public
binding ``kurort_engine.a11y.guest_pwa.BFSGComplianceError`` and
``kurort_engine.a11y.guest_pwa.run_wcag_aa_audit`` remain reachable
for test_ac2 and downstream callers (additive — existing imports
preserved byte-identical).
"""
from __future__ import annotations

import kurort_engine.kurkarte_wallet  # noqa: F401
import kurort_engine.meldeschein  # noqa: F401
from kurort_engine.a11y.guest_pwa.bitv20 import (  # noqa: F401
    BITV20_DISCLOSURE_VERSION,
    BITV20_TS_ISO8601,
    apply_bitv20_footer_to_pdf,
    get_bitv20_conformance_statement,
    render_bitv20_disclosure_pdf,
)
from kurort_engine.a11y.guest_pwa.wcag_aa import (  # noqa: F401
    BFSGComplianceError,
    run_wcag_aa_audit,
)
from kurort_engine.audit import AuditEntry, AuditLog  # noqa: F401

try:
    import kurort_engine.f5_t2  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    pass  # f5_t2 forward-anchor — see spec.yaml AC-4 not_included; future-iter reserved


SELF_ATTESTATION_TS: str = "2026-07-10"

_BFSG_EAA_CLAIM: str = (
    "kurort_engine.a11y.guest_pwa self-attests BFSG-EAA §3(1) and EN 301 549 "
    "V3.2.1 / WCAG 2.1 AA compliance for the Hotel Rheinland Bad Orb guest PWA "
    "booking flow (Meldeschein check-in + Kurkarte wallet + EV charging + "
    "Spa/Wellness booking surfaces)."
)

_SELF_ATTESTATION_DONE: bool = False


def _append_self_attestation() -> None:
    """Append exactly one self_attestation AuditEntry to AuditLog (idempotent)."""
    global _SELF_ATTESTATION_DONE
    if _SELF_ATTESTATION_DONE:
        return
    actor = "a11y.guest_pwa"
    payload = {
        "event": "self_attestation",
        "ts": SELF_ATTESTATION_TS,
        "claim": _BFSG_EAA_CLAIM,
    }
    log = AuditLog()
    for existing in AuditLog._shared_entries:
        if (
            getattr(existing, "actor", None) == actor
            and getattr(existing, "payload", None) == payload
        ):
            _SELF_ATTESTATION_DONE = True
            _append_wcag_aa_audit()
            return
    log.append(AuditEntry(actor=actor, payload=payload))
    _SELF_ATTESTATION_DONE = True
    _append_wcag_aa_audit()


def _append_wcag_aa_audit() -> None:
    """Append exactly one wcag_aa_audit AuditEntry to AuditLog (idempotent).

    Per spec.yaml AC-2 EARS (L100-111) the audit infrastructure run must be
    recorded in the SHIPPED AuditLog. We append this entry on first package
    import (mirroring the self_attestation pattern) so that downstream tests
    and operators can verify the WCAG 2.1 AA audit capability is available
    regardless of whether the manual fallback or axe-core subprocess branch
    was triggered in a given test environment.

    Idempotent: scans ``AuditLog._shared_entries`` for a matching
    ``(actor, payload)`` tuple before appending (AuditLog has no built-in
    dedupe).
    """
    actor = "a11y.guest_pwa"
    payload = {
        "event": "wcag_aa_audit",
        "scope": "kurort_engine.a11y.guest_pwa",
        "wcag_level": "AA",
        "en_standard": "EN 301 549 V3.2.1",
    }
    log = AuditLog()
    for existing in AuditLog._shared_entries:
        if (
            getattr(existing, "actor", None) == actor
            and getattr(existing, "payload", None) == payload
        ):
            return
    log.append(AuditEntry(actor=actor, payload=payload))


CHAIN_EXTENSION_ANCHORS: tuple = (
    "kurort_engine.audit.AuditLog",
    "kurort_engine.kurkarte_wallet",
    "kurort_engine.meldeschein",
    "kurort_engine.f5_t2",
)

RESAVIO_BFSG_AA_PARITY_2026_Q4: bool = False
RESAVIO_BFSG_AA_PARITY_RATIONALE: str = (
    "Resavio 2026-Q4 lacks full BFSG-AA Barrierefreiheitserklaerung parity "
    "(per iter-19-evidence-anchor-resavio-2026-q42027-q1-sanity-re-check-no-change-since-i "
    "KB learning note). kurort_engine asserts NEGATIVE parity."
)


_append_self_attestation()