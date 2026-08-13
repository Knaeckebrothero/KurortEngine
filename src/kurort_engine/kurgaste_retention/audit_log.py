"""kurort_engine.kurgaste_retention.audit_log — Art. 30 VVT append-only audit log.

Iter-38 (Developer) — Pattern C GREENFIELD chain-extension (0 SHAs touched,
7 SHIPs preserved verbatim).

Per spec.yaml AC-5 (Event-driven):
    When cascade completes for `guest_id=G`, the system shall write an
    Art. 30 VVT (Verzeichnis Verarbeitungstätigkeiten) audit entry;
    the function shall be exposed as
    `write_art30_audit_entry(cascade_result: dict) -> AuditEntry` in
    `kurort_engine.kurgaste_retention.audit_log` returning a
    JSON-serializable dict containing the 8 required keys (audit_id +
    timestamp_utc + verarbeitungstätigkeit + betroffene_person +
    verantwortlicher + aufbewahrungsfrist + rechtsgrundlage +
    audit_log_hash). The audit log SHALL be append-only (no update or
    delete APIs exposed).

Anti-drift discipline: this module exposes ONLY `write_art30_audit_entry` +
the `AuditEntry` dataclass. No `update`, `delete`, `modify`, `revoke`,
`amend` APIs (per AC-5 forbidden-pattern scan). The dataclass is
`frozen=True` + `kw_only=True` for immutability.

ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ` (canonical SHIPPED convention).
UUID4 hex 8-char format: `uuid.uuid4().hex[:8]` for the audit_id suffix.
SHA-256 hex digest: 64-char lowercase hex over canonical JSON
(sort_keys=True, separators=(",", ":")).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

# Verantwortlicher per AC-5 verbatim
_VERANTWORTLICHER = "Hotel Rheinland Bad Orb GmbH"

# Verarbeitungstätigkeit per AC-5 verbatim
_VERARBEITUNGSTÄTIGKEIT = "Löschung gemäß DSGVO Art. 17"

# Aufbewahrungsfrist per AC-5 verbatim
_AUFBEWAHRUNGSFRIST = "Art. 30 VVT — 3 Jahre Log-Aufbewahrung"

# Rechtsgrundlage per AC-5 verbatim
_RECHTSGRUNDLAGE = "DSGVO Art. 17 (1)"


@dataclass(frozen=True, kw_only=True)
class AuditEntry:
    """Immutable Art. 30 VVT audit-log entry (frozen + kw_only).

    Fields are positional-or-keyword frozen; mutation raises
    `dataclasses.FrozenInstanceError`. The `audit_log_hash` field is
    computed in `__post_init__` from the canonical JSON of the entry
    (sort_keys=True, separators=(",", ":")). This is the SAME
    canonical-JSON-SHA pattern as iter-33 `kurort_engine.audit.AuditEntry`
    (frozen=True dataclass with SHA-256 content_hash via __post_init__).
    """

    audit_id: str
    timestamp_utc: str
    verarbeitungstätigkeit: str
    betroffene_person: str
    verantwortlicher: str
    aufbewahrungsfrist: str
    rechtsgrundlage: str
    audit_log_hash: str = field(init=False, default="")

    def __post_init__(self) -> None:
        # Compute audit_log_hash via canonical JSON SHA-256.
        # We override the dataclass default via object.__setattr__ because
        # the dataclass is frozen=True (mutating self.audit_log_hash would
        # raise FrozenInstanceError otherwise).
        envelope = {
            "audit_id": self.audit_id,
            "timestamp_utc": self.timestamp_utc,
            "verarbeitungstätigkeit": self.verarbeitungstätigkeit,
            "betroffene_person": self.betroffene_person,
            "verantwortlicher": self.verantwortlicher,
            "aufbewahrungsfrist": self.aufbewahrungsfrist,
            "rechtsgrundlage": self.rechtsgrundlage,
        }
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        object.__setattr__(self, "audit_log_hash", digest)


def _now_iso8601_utc() -> str:
    """Return current UTC time as `YYYY-MM-DDTHH:MM:SSZ` ISO 8601 string."""
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_art30_audit_entry(cascade_result: dict[str, Any]) -> dict[str, Any]:
    """Write an Art. 30 VVT audit entry for a completed cascade (AC-5).

    Append-only: this function ONLY emits new entries; no update/delete
    APIs are exposed (per AC-5 forbidden-pattern scan).

    Returns the AuditEntry as a JSON-serializable dict. The returned
    dict's `audit_log_hash` is computed in `AuditEntry.__post_init__`
    from the canonical JSON of the entry (SHA-256 hex).
    """
    if not isinstance(cascade_result, dict):
        raise TypeError(
            f"cascade_result must be a dict; got {type(cascade_result).__name__}"
        )

    guest_id = cascade_result.get("guest_id", "")
    if not isinstance(guest_id, str):
        raise ValueError(
            "AC-5: cascade_result.guest_id must be a str; "
            f"got {type(guest_id).__name__}: {guest_id!r}"
        )

    audit_id = f"a30-{uuid.uuid4().hex[:8]}"
    timestamp_utc = _now_iso8601_utc()

    entry = AuditEntry(
        audit_id=audit_id,
        timestamp_utc=timestamp_utc,
        verarbeitungstätigkeit=_VERARBEITUNGSTÄTIGKEIT,
        betroffene_person=guest_id,
        verantwortlicher=_VERANTWORTLICHER,
        aufbewahrungsfrist=_AUFBEWAHRUNGSFRIST,
        rechtsgrundlage=_RECHTSGRUNDLAGE,
    )
    # Return as JSON-serializable dict.
    return {
        "audit_id": entry.audit_id,
        "timestamp_utc": entry.timestamp_utc,
        "verarbeitungstätigkeit": entry.verarbeitungstätigkeit,
        "betroffene_person": entry.betroffene_person,
        "verantwortlicher": entry.verantwortlicher,
        "aufbewahrungsfrist": entry.aufbewahrungsfrist,
        "rechtsgrundlage": entry.rechtsgrundlage,
        "audit_log_hash": entry.audit_log_hash,
    }