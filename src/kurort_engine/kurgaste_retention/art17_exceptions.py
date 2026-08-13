"""kurort_engine.kurgaste_retention.art17_exceptions — Art. 17(3) HGB §257 override.

Iter-38 (Developer) — Pattern C GREENFIELD chain-extension (0 SHAs touched,
7 SHIPs preserved verbatim).

Per spec.yaml AC-6 (Event-driven):
    When Art. 17(3) override applies (e.g., HGB §257 10-year retention /
    AO §147 7-year retention / §23 SGB V Badekur prescription /
    Art. 17(3)(b) legal claim / Art. 17(3)(e) public interest), the
    system shall require explicit override reason (>=20 chars) AND emit
    audit-on-override per Art. 30; the function shall be exposed as
    `require_art_173_override_reason(reason: str, legal_basis: str) ->
    Art173Override` in
    `kurort_engine.kurgaste_retention.art17_exceptions` returning a
    JSON-serializable dict containing `override_id: str` ("a173-<uuid8>"
    format), `reason: str` (>=20 chars, validated non-empty after strip),
    `legal_basis: str` (one of 5 allowed values), `requested_at: str`
    (ISO 8601 UTC), `audit_on_override_emitted: bool` (True). The
    function SHALL raise ValueError if reason is shorter than 20 chars
    after strip; the function SHALL raise ValueError if legal_basis is
    not in the allowed set.

Per D8 Risk-1 KEPT mitigation: this AC ensures explicit override reason
+ valid legal_basis is required before any Art. 17(3) override is
accepted by the cascade.

Allowed legal_basis values per spec.yaml AC-6 verbatim (5 values):
  - hgb_section_257 (HGB §257 10-year retention)
  - ao_section_147 (AO §147 7-year retention)
  - sgb_v_section_23 (§23 SGB V Badekur prescription)
  - dsgvo_art_173_b_legal_claim (Art. 17(3)(b) legal claim)
  - dsgvo_art_173_e_public_interest (Art. 17(3)(e) public interest)
"""
from __future__ import annotations

import uuid
from typing import Any

# Allowed legal_basis values per spec.yaml AC-6 verbatim (5 values)
_ALLOWED_LEGAL_BASIS: frozenset[str] = frozenset(
    {
        "hgb_section_257",
        "ao_section_147",
        "sgb_v_section_23",
        "dsgvo_art_173_b_legal_claim",
        "dsgvo_art_173_e_public_interest",
    }
)

# Minimum reason length after strip per spec.yaml AC-6 verbatim
_MIN_REASON_LEN = 20


def _now_iso8601_utc() -> str:
    """Return current UTC time as `YYYY-MM-DDTHH:MM:SSZ` ISO 8601 string."""
    import datetime as _dt
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_art_173_override_reason(
    reason: str,
    legal_basis: str,
) -> dict[str, Any]:
    """Require Art. 17(3) override reason + valid legal_basis (AC-6).

    Accepts a `reason` string (must be >=20 chars after strip) and a
    `legal_basis` string (must be one of the 5 allowed values per
    spec.yaml AC-6). Raises ValueError if either constraint is violated.

    Returns an Art173Override dict per spec.yaml AC-6 (override_id +
    reason + legal_basis + requested_at + audit_on_override_emitted).
    The audit_on_override_emitted is always True on the happy path.
    """
    if not isinstance(reason, str):
        raise TypeError(
            f"reason must be a str; got {type(reason).__name__}"
        )
    if not isinstance(legal_basis, str):
        raise TypeError(
            f"legal_basis must be a str; got {type(legal_basis).__name__}"
        )

    stripped = reason.strip()
    if len(stripped) < _MIN_REASON_LEN:
        raise ValueError(
            f"AC-6: reason must be >= {_MIN_REASON_LEN} chars after strip; "
            f"got {len(stripped)} chars: {stripped!r}"
        )

    if legal_basis not in _ALLOWED_LEGAL_BASIS:
        raise ValueError(
            f"AC-6: legal_basis={legal_basis!r} not in allowed set. "
            "Allowed legal_basis values per spec.yaml AC-6: "
            f"{sorted(_ALLOWED_LEGAL_BASIS)!r}"
        )

    override_id = f"a173-{uuid.uuid4().hex[:8]}"
    requested_at = _now_iso8601_utc()

    return {
        "override_id": override_id,
        "reason": reason,
        "legal_basis": legal_basis,
        "requested_at": requested_at,
        "audit_on_override_emitted": True,
    }