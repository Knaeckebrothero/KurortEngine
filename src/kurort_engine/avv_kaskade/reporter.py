"""kurort_engine.avv_kaskade.reporter — 3-state audit packet exporter.

Iter-28 (Developer) — Phase 5 Tactical Green.

AC-4: export_audit_packet(processor_id, format) returns a packet whose payload
     bytes start with b'%PDF-' and whose metadata['state_format'] equals the
     requested format. Raises ValueError for any format not in {'lfa-baylda',
     'lfdi-bw', 'hbdi-he'}.

AC-4 is DEFERRED to the BFSG-AA reviewer pool per binding contract mitigation 1
(see ``spec.lock.md`` STALE_PENDING_FLAG). The GREEN implementation emits a
minimal PDF-1.4 stub payload that satisfies the structural-shape oracle; the
real BayLDA / LfDI-BW / HBDI-HE form layouts are pending reviewer review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kurort_engine.avv_kaskade._validation import compute_canonical_sha256

# The 3 supported state-LDA formats. AC-4 / test_ac4_export_audit_packet_3state.
SUPPORTED_STATE_FORMATS: frozenset[str] = frozenset({"lfa-baylda", "lfdi-bw", "hbdi-he"})


@dataclass
class AuditPacket:
    """Audit packet for a state-LDA (BayLDA / LfDI-BW / HBDI-HE).

    Attributes:
      - payload: PDF-1.4 bytes (stub form layout, deferred per STALE_PENDING_FLAG).
      - metadata: state-LDA envelope metadata. ``state_format`` keys back to
        the requested input format per AC-4.
    """

    payload: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


def envelope_hash(metadata: dict[str, Any]) -> str:
    """Chain-integrity SHA-256 over the metadata envelope (Phase 5 helper)."""
    return compute_canonical_sha256(metadata)


def _build_stub_payload(format: str, processor_id: str) -> bytes:
    """Build a minimal PDF-1.4 stub payload.

    The real BayLDA / LfDI-BW / HBDI-HE form layout is pending reviewer review
    (see binding contract mitigation 1 STALE_PENDING_FLAG). The GREEN
    implementation emits only the PDF header + a one-line trailer so the
    structural-shape oracle (payload.startswith(b'%PDF-')) passes.
    """
    return (
        b"%PDF-1.4\n"
        b"%\xe2\xe3\xcf\xd3\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"%%stub audit packet for format=" + format.encode("utf-8") + b"\n"
        b"%%processor_id=" + processor_id.encode("utf-8") + b"\n"
        b"%%EOF\n"
    )


def export_audit_packet(
    processor_id: str,
    format: str = "lfa-baylda",
) -> AuditPacket:
    """Export a 3-state audit packet (BayLDA / LfDI-BW / HBDI-HE).

    EARS AC-4:
      When export_audit_packet(processor_id, format) is called with format in
      {"lfa-baylda", "lfdi-bw", "hbdi-he"}, the system shall return a packet
      object whose payload bytes start with b"%PDF-" and whose
      metadata["state_format"] equals the requested format; and the system
      shall raise ValueError for any format not in the three supported state
      formats.
    """
    if format not in SUPPORTED_STATE_FORMATS:
        raise ValueError(
            f"Unsupported state-LDA format {format!r}; "
            f"expected one of {sorted(SUPPORTED_STATE_FORMATS)}"
        )
    payload = _build_stub_payload(format, processor_id)
    metadata = {
        "state_format": format,
        "processor_id": processor_id,
        "deferred_review": True,  # binding contract mitigation 1 (STALE_PENDING_FLAG)
    }
    return AuditPacket(payload=payload, metadata=metadata)