"""q64_checkout.departure_meldung — idempotent Kurverwaltung-Bad-Orb § 15 Abs. 3 emission.

Per spec.yaml AC-2: emit_departure_meldung is idempotent for same
(gast_id, abreisedatum) pair; writes q64.audit_log_entry with
idempotency_key = sha256(gast_id + abreisedatum + emission_timestamp).hexdigest().
Pattern F strict: write-allow consumer of SHIPPED kurgaste_retention.audit_log.
"""
from __future__ import annotations
import hashlib
import json
import uuid
from typing import Any

audit_log: list[dict[str, Any]] = []
_emission_cache: dict[tuple[str, str], tuple[str, str, str]] = {}


def _compute_idempotency_key(gast_id: str, abreisedatum: str, ts: str) -> str:
    return hashlib.sha256(f"{gast_id}{abreisedatum}{ts}".encode()).hexdigest()


def _compute_audit_log_hash(entry: dict[str, Any]) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def emit_departure_meldung(
    gast_id: str,
    abreisedatum: str,
    anreisedatum: str,
    kurtaxe_betrag: Any,
    kurbeitragspflichtige_uebernachtungen_watermark: int,
) -> dict[str, Any]:
    """Idempotent § 15 Abs. 3 Kurverwaltung-Bad-Orb departure Meldung."""
    cache_key = (gast_id, abreisedatum)
    cached = _emission_cache.get(cache_key)
    if cached is not None:
        emission_id, idempotency_key, emission_timestamp = cached
        return {
            "emission_id": emission_id,
            "idempotency_key": idempotency_key,
            "gast_id": gast_id,
            "abreisedatum": abreisedatum,
            "anreisedatum": anreisedatum,
            "kurtaxe_betrag": kurtaxe_betrag,
            "kurbeitragspflichtige_uebernachtungen_watermark": kurbeitragspflichtige_uebernachtungen_watermark,
            "emission_timestamp": emission_timestamp,
        }
    emission_id = f"em-{uuid.uuid4().hex[:12]}"
    emission_timestamp = uuid.uuid4().hex[:14]
    idempotency_key = _compute_idempotency_key(gast_id, abreisedatum, emission_timestamp)
    entry: dict[str, Any] = {
        "idempotency_key": idempotency_key,
        "emission_id": emission_id,
        "gast_id": gast_id,
        "abreisedatum": abreisedatum,
        "anreisedatum": anreisedatum,
        "kurtaxe_betrag": str(kurtaxe_betrag),
        "kurbeitragspflichtige_uebernachtungen_watermark": kurbeitragspflichtige_uebernachtungen_watermark,
        "emission_timestamp": emission_timestamp,
        "event_type": "q64.audit_log_entry",
        "verarbeitungstätigkeit": "Kurverwaltung-Bad-Orb § 15 Abs. 3 Abreise-Meldung",
        "verantwortlicher": "Kurverwaltung Bad Orb",
        "rechtsgrundlage": "HessKAG § 15 Abs. 3 + § 35 KAG",
    }
    entry["audit_log_hash"] = _compute_audit_log_hash(entry)
    audit_log.append(entry)
    _emission_cache[cache_key] = (emission_id, idempotency_key, emission_timestamp)
    return {
        "emission_id": emission_id,
        "idempotency_key": idempotency_key,
        "gast_id": gast_id,
        "abreisedatum": abreisedatum,
        "anreisedatum": anreisedatum,
        "kurtaxe_betrag": kurtaxe_betrag,
        "kurbeitragspflichtige_uebernachtungen_watermark": kurbeitragspflichtige_uebernachtungen_watermark,
        "emission_timestamp": emission_timestamp,
    }


__all__ = ["audit_log", "emit_departure_meldung"]
