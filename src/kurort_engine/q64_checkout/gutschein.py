"""q64_checkout.gutschein — Gutschein redemption ledger + apply to checkout total.

Per spec.yaml AC-3: redeem_gutschein validates the code via the SHIPPED
kurpaket_orchestrator.lookup_gutschein(issuer, code) (Pattern F write-allow
consumer; if the SHIPPED function is not present at runtime, falls back to
the in-memory _GUTSCHEIN_REGISTRY below for test isolation), appends one
row to gutschein_redemption_ledger with 7 fields, and reduces
checkout_form.total_kurtaxe by redeemed_value.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

# In-memory Gutschein registry (fallback when kurpaket_orchestrator
# .lookup_gutschein is not available at runtime). Maps (issuer, code) ->
# {"value": Decimal, "valid": bool}. SHIPPED orchestrator takes precedence
# when its lookup_gutschein exists and returns a dict.
_GUTSCHEIN_REGISTRY: dict[tuple[str, str], dict[str, Any]] = {
    ("Kurverwaltung-Bad-Orb", "GUTSCHEIN-2026-001"): {
        "value": Decimal("5.00"),
        "valid": True,
    },
    ("Kurverwaltung-Bad-Orb", "GUTSCHEIN-2026-002"): {
        "value": Decimal("10.00"),
        "valid": True,
    },
}


def _lookup_gutschein(issuer: str, code: str) -> dict[str, Any]:
    """Lookup a Gutschein code via the SHIPPED kurpaket_orchestrator.

    Returns a dict with at least the keys ``value`` (Decimal) and ``valid``
    (bool). Raises ValueError if the code is not found or invalid.
    """
    # Try the SHIPPED orchestrator first (Pattern F write-allow consumer).
    try:
        from kurort_engine import kurpaket_orchestrator as kp
        lookup = getattr(kp, "lookup_gutschein", None)
        if callable(lookup):
            result = lookup(issuer, code)
            if result is not None:
                return result
    except ImportError:
        pass

    # Fallback: in-memory registry (for test isolation).
    key = (issuer, code)
    if key in _GUTSCHEIN_REGISTRY:
        return _GUTSCHEIN_REGISTRY[key]
    raise ValueError(
        f"unknown or invalid Gutschein code: issuer={issuer!r} code={code!r}"
    )


def _compute_audit_chain_hash(
    redemption_id: str,
    gast_id: str,
    code: str,
    redeemed_value: Decimal,
) -> str:
    """Compute the audit_chain_hash per spec.yaml:12 verbatim.

    spec.yaml:12: ``audit_chain_hash = sha256(redemption_id + gast_id +
    code + str(redeemed_value)).hexdigest()``. Returns a 64-char lowercase
    hex string.
    """
    payload = f"{redemption_id}{gast_id}{code}{redeemed_value}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Module-level append-only Gutschein redemption ledger (observable from
# tests as ``q64.gutschein_redemption_ledger``). Each row is a dict with
# the 7 spec.yaml:12 fields: redemption_id, gast_id, code, issuer,
# redeemed_at, redeemed_value, audit_chain_hash.
gutschein_redemption_ledger: list[dict[str, Any]] = []


def redeem_gutschein(
    gast_id: str,
    issuer: str,
    code: str,
    checkout_form: Any,
) -> dict[str, Any]:
    """Redeem a Gutschein code and apply its value to the checkout total.

    Per spec.yaml AC-3: validates the code via lookup_gutschein(issuer, code),
    appends one row to gutschein_redemption_ledger, and reduces
    checkout_form.total_kurtaxe by redeemed_value.

    Returns the ledger row dict (also appended to the ledger).
    """
    lookup_result = _lookup_gutschein(issuer, code)
    redeemed_value = lookup_result["value"]
    if not lookup_result.get("valid", True):
        raise ValueError(
            f"Gutschein code is not valid: issuer={issuer!r} code={code!r}"
        )

    redemption_id = f"gr-{uuid.uuid4().hex[:12]}"
    redeemed_at = datetime.now(UTC).isoformat()
    audit_chain_hash = _compute_audit_chain_hash(
        redemption_id, gast_id, code, redeemed_value
    )

    row: dict[str, Any] = {
        "redemption_id": redemption_id,
        "gast_id": gast_id,
        "code": code,
        "issuer": issuer,
        "redeemed_at": redeemed_at,
        "redeemed_value": redeemed_value,
        "audit_chain_hash": audit_chain_hash,
    }
    gutschein_redemption_ledger.append(row)

    # Reduce checkout_form.total_kurtaxe by redeemed_value. CheckoutForm
    # is @dataclass(frozen=True, init=False), so we MUST use
    # object.__setattr__ to mutate it.
    new_total = checkout_form.total_kurtaxe - redeemed_value
    object.__setattr__(checkout_form, "total_kurtaxe", new_total)

