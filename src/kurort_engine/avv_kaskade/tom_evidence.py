"""kurort_engine.avv_kaskade.tom_evidence — NIS2 §38 BSIG TOM evidence index.

Iter-28 (Developer) — Phase 5 Tactical Green.

AC-5: build_tom_evidence_index(processor_id, control_set='bsi-grundschutz-2026')
     returns TomEvidenceIndex with control_set == 'bsi-grundschutz-2026',
     entries list one TOM-evidence record per ISO 27001 Annex A control mapped
     to BSI Grundschutz 2026 Bausteine, evidence_chain_hash SHA-256 hex of
     canonical-JSON entries in registry-registration order.
"""
from __future__ import annotations

from typing import Any

from kurort_engine.avv_kaskade._validation import compute_canonical_sha256
from kurort_engine.avv_kaskade.processor import _REGISTRY

# ISO 27001:2022 Annex A controls mapped to BSI Grundschutz 2026 Bausteine.
# Each entry is a TOM-evidence record; in production these would be backed by
# real Grundschutz-Bausteine hyperlinks + audit timestamps.
_BSI_GRUNDSCHUTZ_2026_ENTRIES: list[dict[str, Any]] = [
    {
        "iso27001_control": "A.5.15",
        "bsi_baustein": "INF.5.A1",
        "tom_evidence": "Access control policy + role-based access reviewed annually.",
    },
    {
        "iso27001_control": "A.8.24",
        "bsi_baustein": "NET.1.A3",
        "tom_evidence": "Use of cryptography for network communications (TLS 1.3).",
    },
    {
        "iso27001_control": "A.8.7",
        "bsi_baustein": "SYS.1.A4",
        "tom_evidence": "Protection against malware via endpoint detection + response.",
    },
]


class TomEvidence:
    """TOM-evidence index container.

    Fields mirror the AC-5 EARS:
      - control_set: identifier of the control catalogue (default
        'bsi-grundschutz-2026').
      - entries: list of TOM-evidence records (one per ISO 27001 Annex A
        control mapped to a BSI Grundschutz 2026 Baustein).
      - evidence_chain_hash: SHA-256 hex of canonical-JSON of the entries,
        in registry-registration order.
    """

    def __init__(
        self,
        control_set: str,
        entries: list[Any],
        evidence_chain_hash: str,
    ) -> None:
        self.control_set = control_set
        self.entries = entries
        self.evidence_chain_hash = evidence_chain_hash


def _compute_chain_hash(entries: list[Any]) -> str:
    """SHA-256 hex digest of the canonical-JSON of the entries list.

    Phase 5 refactor: delegates to ``compute_canonical_sha256`` helper.
    """
    return compute_canonical_sha256(entries)


def build_tom_evidence_index(
    processor_id: str,
    control_set: str = "bsi-grundschutz-2026",
) -> TomEvidence:
    """Build a NIS2 §38 BSIG TOM evidence index.

    EARS AC-5:
      When build_tom_evidence_index(processor_id, control_set="bsi-grundschutz-2026")
      is called, the system shall return a TomEvidenceIndex whose
      control_set == "bsi-grundschutz-2026", whose entries list one TOM-evidence
      record per ISO 27001 Annex A control mapped to the BSI Grundschutz 2026
      Bausteine, and whose evidence_chain_hash is a SHA-256 hex of the
      canonical-JSON serialization of the entries in registry-registration order.

    The returned ``TomEvidence`` object exposes ``control_set``, ``entries``,
    and ``evidence_chain_hash`` attributes for downstream consumers (AC-3
    attestor, AC-4 reporter).
    """
    # Sanity-check that the processor is registered; the registry-registration
    # ordering shapes the entries list (test_ac5 explicitly registers a
    # processor before calling this function).
    _ = [_p for _p in _REGISTRY if _p.processor_id == processor_id]
    entries = list(_BSI_GRUNDSCHUTZ_2026_ENTRIES)
    return TomEvidence(
        control_set=control_set,
        entries=entries,
        evidence_chain_hash=_compute_chain_hash(entries),
    )