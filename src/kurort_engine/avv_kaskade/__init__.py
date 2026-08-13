"""kurort_engine.avv_kaskade — Art. 28 DSGVO cascade-audit module.

Iter-28 (Developer) — Phase 3 Tactical Red stub. Pattern C chain-extension
on the SHIPPED kurgaste_retention / predicate_filing / kurkarte_wallet
surfaces (0 SHAs touched, 6 SHAs preserved verbatim).

This package implements the in-app DSGVO Art. 28 (Auftragsverarbeitung)
cascade-audit surface so Hotel Rheinland Bad Orb can produce the Art. 28
cascade audit chain in 30 seconds, not 30 days. The 7 AC surface per
``repo/spec/avv_kaskade/spec.yaml``:

  AC-1   register_processor happy path (avv_hash = sha256(avv_pdf_bytes))
  AC-1.1 register_processor expired-avv rejection (ValueError)
  AC-2   run_geeignetheitspruefung report (ISO 27001 coverage, TOM index)
  AC-2.1 vendor_non_cooperation flag in report gaps list
  AC-3   attest_chain("dsk-kp13") packet shape (5 top-level keys)
  AC-4   export_audit_packet 3-state PDF (BayLDA / LfDI-BW / HBDI-HE)
  AC-5   build_tom_evidence_index NIS2 §38 BSIG BSI Grundschutz 2026

AC-4 is deferred to the BFSG-AA reviewer pool per binding contract
mitigation 1 (see ``spec.lock.md`` STALE_PENDING_FLAG); the deferred-AC-4
marker is recorded in ``archive/phase_3_retrospective_90cbbdd4.md``.

Public API (re-exported in ``__all__``)
---------------------------------------

* :class:`Processor` — Art. 28(1) processor registration record
* :class:`SubProcessor` — sub-processor under an Art. 28(2) processor
* :func:`register_processor` — append a Processor to the registry (AC-1/1.1)
* :class:`GeeignetheitspruefungReport` — Art. 28(1) Geeignetheitspruefung
* :func:`run_geeignetheitspruefung` — produce a report for a processor (AC-2/2.1)
* :func:`attest_chain` — DSK-Kurzpapier Nr. 13 attestor (AC-3)
* :func:`export_audit_packet` — 3-state audit packet PDF emitter (AC-4)
* :class:`AuditTrailEntry` — NIS2 §38 BSIG audit trail entry (read-only consumer)
* :class:`TomEvidence` — TOM evidence record (AC-5)
* :func:`build_tom_evidence_index` — NIS2 §38 BSIG BSI Grundschutz 2026 TOM
  evidence index (AC-5)
* :func:`main` — CLI entry point (AC-4 surface)

Iter-28 Phase 3 RED NOTE: this ``__init__.py`` re-exports **stub** symbols.
Each stub is ``None`` / empty-container so ``import`` succeeds and tests
fail with ``AssertionError`` (per pinned memory [2]: no ImportError in RED).
The GREEN phase replaces each stub with the real implementation.
"""
from __future__ import annotations

from kurort_engine.avv_kaskade.attestor import attest_chain  # noqa: E402,F401

# Stub re-exports (Phase 3 RED). Each stub returns None / empty container
# so `from kurort_engine.avv_kaskade import X` succeeds (no ImportError).
# The test_oracle for each AC then asserts a post-condition that fails
# with AssertionError until the GREEN-phase implementation lands.
from kurort_engine.avv_kaskade.audit_trail import (  # noqa: E402,F401
    AuditTrailEntry,
)
from kurort_engine.avv_kaskade.cli import main  # noqa: E402,F401
from kurort_engine.avv_kaskade.geeignetheitspruefung import (  # noqa: E402,F401
    GeeignetheitspruefungReport,
    run_geeignetheitspruefung,
)
from kurort_engine.avv_kaskade.processor import (  # noqa: E402,F401
    Processor,
    register_processor,
)
from kurort_engine.avv_kaskade.reporter import (  # noqa: E402,F401
    export_audit_packet,
)
from kurort_engine.avv_kaskade.sub_processor import SubProcessor  # noqa: E402,F401
from kurort_engine.avv_kaskade.tom_evidence import (  # noqa: E402,F401
    TomEvidence,
    build_tom_evidence_index,
)

__all__ = [
    "Processor",
    "SubProcessor",
    "register_processor",
    "GeeignetheitspruefungReport",
    "run_geeignetheitspruefung",
    "attest_chain",
    "export_audit_packet",
    "AuditTrailEntry",
    "TomEvidence",
    "build_tom_evidence_index",
    "main",
]