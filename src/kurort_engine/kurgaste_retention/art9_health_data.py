"""kurort_engine.kurgaste_retention.art9_health_data — Art. 9 health-data audit-flag.

Iter-38 (Developer) — Pattern C GREENFIELD chain-extension (0 SHAs touched,
7 SHIPs preserved verbatim).

Per spec.yaml AC-8 (Event-driven):
    When health-data is referenced in cascade for `guest_id=G` (Art. 9
    special category — e.g., Badekur prescription, spa therapy record),
    the system shall require explicit consent OR legal-basis AND emit
    audit-flag per Art. 30; the function shall be exposed as
    `assert_consent_or_legal_basis(consent_record: dict, legal_basis: str)
    -> Art9AuditFlag` in
    `kurort_engine.kurgaste_retention.art9_health_data` returning a
    JSON-serializable dict containing `audit_id: str` ("a9-<uuid8>"
    format), `guest_id: str`, `consent_present: bool`, `legal_basis: str`
    (one of 4 allowed values), `audit_flag_emitted_at: str` (ISO 8601
    UTC), `audit_flag_hash: str` (SHA-256 hex). The function SHALL raise
    `ValueError` if consent is absent AND legal_basis is not in the
    allowed set.

Per D8 Risk-2 DISMISSED-with-mitigation: this AC ensures explicit
consent OR valid legal-basis is required before any Art. 9 special
category data is processed.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

# Allowed legal_basis values per spec.yaml AC-8 verbatim (4 values)
_ALLOWED_LEGAL_BASIS: frozenset[str] = frozenset(
    {
        "dsgvo_art_9_2_a_explicit_consent",
        "dsgvo_art_9_2_b_employment_law",
        "dsgvo_art_9_2_g_public_health",
        "dsgvo_art_9_2_h_medical_diagnosis",
    }
)


def _now_iso8601_utc() -> str:
    """Return current UTC time as `YYYY-MM-DDTHH:MM:SSZ` ISO 8601 string."""
    import datetime as _dt
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def assert_consent_or_legal_basis(
    consent_record: dict[str, Any],
    legal_basis: str,
) -> dict[str, Any]:
    """Assert Art. 9 health-data consent OR legal-basis (AC-8).

    Accepts a `consent_record` dict (must contain at least `guest_id` +
    `consent_captured: bool`) and a `legal_basis` string. If consent is
    absent AND legal_basis is not in the allowed set, raises ValueError.

    Returns an Art9AuditFlag dict per spec.yaml AC-8 (audit_id +
    guest_id + consent_present + legal_basis + audit_flag_emitted_at +
    audit_flag_hash). The audit_flag_hash is computed via SHA-256 over
    canonical JSON of the audit-flag envelope (sort_keys=True,
    separators=(",", ":")).
    """
    if not isinstance(consent_record, dict):
        raise TypeError(
            f"consent_record must be a dict; got {type(consent_record).__name__}"
        )
    if not isinstance(legal_basis, str):
        raise TypeError(
            f"legal_basis must be a str; got {type(legal_basis).__name__}"
        )

    guest_id = consent_record.get("guest_id", "")
    if not isinstance(guest_id, str):
        raise ValueError(
            "AC-8: consent_record.guest_id must be a str; "
            f"got {type(guest_id).__name__}: {guest_id!r}"
        )

    consent_captured = consent_record.get("consent_captured", False)
    if not isinstance(consent_captured, bool):
        # Coerce truthy/falsy non-bool values; but be strict for the spec contract.
        raise ValueError(
            "AC-8: consent_record.consent_captured must be a bool; "
            f"got {type(consent_captured).__name__}: {consent_captured!r}"
        )

    consent_present = consent_captured
    legal_basis_valid = legal_basis in _ALLOWED_LEGAL_BASIS

    if not consent_present and not legal_basis_valid:
        raise ValueError(
            "AC-8: BOTH consent_present=False AND legal_basis="
            f"{legal_basis!r} (not in allowed set). Explicit consent "
            "OR a valid legal_basis is REQUIRED to process Art. 9 "
            "special-category health data. Allowed legal_basis values: "
            f"{sorted(_ALLOWED_LEGAL_BASIS)!r}"
        )

    audit_id = f"a9-{uuid.uuid4().hex[:8]}"
    audit_flag_emitted_at = _now_iso8601_utc()

    # Build envelope for SHA-256 (canonical JSON, sort_keys=True,
    # separators=(",", ":"))
    envelope = {
        "audit_id": audit_id,
        "guest_id": guest_id,
        "consent_present": consent_present,
        "legal_basis": legal_basis if legal_basis_valid else "",
        "audit_flag_emitted_at": audit_flag_emitted_at,
    }
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    audit_flag_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "audit_id": audit_id,
        "guest_id": guest_id,
        "consent_present": consent_present,
        "legal_basis": legal_basis,
        "audit_flag_emitted_at": audit_flag_emitted_at,
        "audit_flag_hash": audit_flag_hash,
    }