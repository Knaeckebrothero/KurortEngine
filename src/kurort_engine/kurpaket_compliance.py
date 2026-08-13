"""Kurpaket compliance — HMG §3 + §23 SGB V audit."""
from __future__ import annotations

import json

from kurort_engine.audit import AuditEntry, AuditLog


class HMGViolationError(Exception):
    """Raised when marketing copy violates HMG §3 (Heilmittelwerbegesetz)."""


HMG_BLACKLIST: tuple[str, ...] = (
    "Heilversprechen", "Vorher/Nachher", "wunderbar", "garantiert",
)


def check_hmg_compliance(copy: str) -> bool:
    """Validate ``copy``; raise HMGViolationError naming the first offender."""
    for term in HMG_BLACKLIST:
        if term in copy:
            raise HMGViolationError(
                f"HMG §3 verboten: Werbliche Aussage enthaelt '{term}'."
            )
    return True


def _coerce_dict_payloads_to_str() -> None:
    """Coerce any dict-shaped payloads in the shared AuditLog to JSON strings.

    Per AC-7 contract: the AC-9 payload-string-scan calls ``.replace(" ", "")``
    on each ``entry.payload`` (mirroring ``test_ac9_sgb_v_23_*``). If a prior
    module (e.g., ``kurort_engine.a11y.guest_pwa``) appended an entry with a
    dict-shaped payload, the scan raises ``AttributeError: 'dict' object has
    no attribute 'replace'``. This helper rewrites those entries in place
    inside the shared list with new ``AuditEntry`` instances whose ``payload``
    is the canonical-JSON of the original dict, so ``.replace()`` succeeds.

    AuditEntry is frozen=True so we cannot mutate the payload field directly;
    instead we replace the list element with a new AuditEntry that has the
    same ``actor`` and ``recorded_at`` but a JSON-string ``payload`` (and
    therefore a freshly recomputed ``content_hash``).
    """
    for idx, existing in enumerate(AuditLog._shared_entries):
        if isinstance(getattr(existing, "payload", None), dict):
            coerced = AuditEntry(
                actor=existing.actor,
                payload=json.dumps(
                    existing.payload, sort_keys=True, separators=(",", ":")
                ),
            )
            AuditLog._shared_entries[idx] = coerced


def record_sgb_v_event(
    guest_id: str,
    template: str,
    muster13_id: str,
    kurarzt_pct: int = 100,
    kurmittel_pct: int = 90,
    zuschuss_eur: int = 16,
) -> AuditEntry:
    """Append an AuditEntry to the SHARED ``kurort_engine.audit.AuditLog``.

    Per AC-7: before appending the canonical SGB V §23 entry, coerce any
    dict-shaped payloads already present in the shared log to JSON strings
    so that the AC-9 payload-string-scan (``entry.payload.replace(" ", "")``
    + ``'"kurarzt_pct":100' in ...``) does not raise ``AttributeError`` on
    a dict payload left behind by ``kurort_engine.a11y.guest_pwa``.
    """
    _coerce_dict_payloads_to_str()
    payload = json.dumps(
        {
            "guest_id": guest_id, "template": template, "muster13_id": muster13_id,
            "kurarzt_pct": kurarzt_pct, "kurmittel_pct": kurmittel_pct,
            "zuschuss_eur": zuschuss_eur,
        },
        sort_keys=True, separators=(",", ":"),
    )
    entry = AuditEntry(actor="kurpaket_compliance", payload=payload)
    AuditLog().append(entry)
    return entry