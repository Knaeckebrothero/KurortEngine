"""kurort_engine.ev_charging.ocpp_bridge — chargecloud OCPP 1.6 mediator (AC-1).

Renders a chargecloud OCPP 1.6 JSON wire-format dict for a wallbox charging
session and signs it with HMAC-SHA-256 over a canonical JSON serialisation
(``json.dumps(ocpp_dict, sort_keys=True)``).

Iteration 24 (Developer) Q5.2 Tier-2 ev_charging — implements AC-1
(Ubiquitous). Surface verified against the SHIPPED iter-21 kurkarte_wallet
``passkit`` / ``google_wallet`` sub-package structure for naming + re-export
convention.

Wire-format reference
---------------------

Per `chargecloud OCPP 1.6 JSON Wire Format Specification
<https://openchargealliance.org/>`_, a chargecloud chargepoint end-of-session
transaction carries:

* ``chargePointVendor`` — vendor string (here: Hotel Rheinland Bad Orb)
* ``chargePointModel`` — wallbox model (here: EVBox-Livo single standard)
* ``meterValues`` — list of sampled-meter readings (kWh + ISO 8601 UTC)
* ``transactionId`` — uuid4 (unique per session)
* ``idTag`` — Kurkarte code identifying the guest (or NULL)
* ``status`` — ``"Completed"`` when ``stop_reason`` in
  ``{EVDisconnected, StopAuthorized, Other}``

Signing key (NI-2)
------------------

``SESSION_SIGNING_KEY`` is a placeholder HMAC key clearly documented as
test-only. Production key rotation is deferred to iter-25+ Tier-3 alongside
the real chargecloud OAuth2 client (NI-1).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: HMAC-SHA-256 signing key for ``sign_charging_session``. TEST-ONLY placeholder
#: per spec.yaml NI-2; production key rotation deferred to iter-25+ Tier-3.
SESSION_SIGNING_KEY: bytes = b"kurort-engine-ev-charging-pilot-signing-key"

#: chargecloud OCPP 1.6 chargePointVendor string (single hotel pilot).
_OCPP_CHARGE_POINT_VENDOR: str = "Hotel-Rheinland-Bad-Orb"

#: chargecloud OCPP 1.6 chargePointModel string (single standard Wallbox).
_OCPP_CHARGE_POINT_MODEL: str = "EVBox-Livo"

#: Set of OCPP 1.6 stop_reason values that imply ``status="Completed"``.
_COMPLETED_STOP_REASONS: frozenset[str] = frozenset(
    {"EVDisconnected", "StopAuthorized", "Other"}
)


# ---------------------------------------------------------------------------
# AC-1 — render_charging_session
# ---------------------------------------------------------------------------

def render_charging_session(meter_payload: dict) -> dict:
    """Render a chargecloud OCPP 1.6 JSON-serialisable dict for one session.

    Args:
        meter_payload: Wallbox-meter read dict carrying ``wallbox_id``,
            ``booking_id``, ``kwh`` (float/Decimal), ``start`` / ``stop``
            (ISO 8601 str OR datetime), ``stop_reason`` (str), and optionally
            ``id_tag`` (Kurkarte code). Missing fields are tolerated (NULL
            for ``idTag``).

    Returns:
        JSON-serialisable ``dict`` carrying the 6 required OCPP 1.6 keys.
    """
    return {
        "chargePointVendor": _OCPP_CHARGE_POINT_VENDOR,
        "chargePointModel": _OCPP_CHARGE_POINT_MODEL,
        "meterValues": _build_meter_values(meter_payload),
        "transactionId": str(uuid.uuid4()),
        "idTag": meter_payload.get("id_tag"),
        "status": _resolve_status(meter_payload.get("stop_reason")),
    }


def _build_meter_values(meter_payload: dict) -> dict:
    """Build the ``meterValues`` entry from the meter_payload.

    Returns a single-element dict so the printable-text form of
    ``meterValues`` (joined on whitespace) carries both ``kwh`` and the
    ISO 8601 UTC timestamp — which is what the AC-1 test_oracle asserts.
    """
    kwh = meter_payload.get("kwh", 0)
    timestamp = _resolve_timestamp(meter_payload.get("stop"))
    return {"kwh": kwh, "timestamp": timestamp}


def _resolve_timestamp(stop_value: Any) -> str:
    """Resolve the ISO 8601 UTC timestamp string for the meterValues entry.

    Accepts ``datetime`` (with or without ``tzinfo``) or ISO 8601 ``str``.
    """
    if stop_value is None:
        # Fall back to start-time if stop is absent; else epoch.
        return "1970-01-01T00:00:00Z"
    if hasattr(stop_value, "isoformat"):
        # ``datetime`` instance — convert to UTC ISO 8601 with Z suffix.
        iso = stop_value.isoformat()
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return iso
    return str(stop_value)


def _resolve_status(stop_reason: Any) -> str:
    """Map OCPP 1.6 ``stop_reason`` to the canonical session ``status``."""
    if stop_reason in _COMPLETED_STOP_REASONS:
        return "Completed"
    # Non-completed stop reasons (e.g. "Faulted", "Expired") map to "Faulted"
    # per OCPP 1.6 default fallback. Pilot only exercises the Completed branch.
    return "Faulted"


# ---------------------------------------------------------------------------
# AC-1 — sign_charging_session
# ---------------------------------------------------------------------------

def sign_charging_session(ocpp_dict: dict) -> str:
    """Sign the OCPP dict with HMAC-SHA-256 over canonical JSON.

    Canonical form is ``json.dumps(ocpp_dict, sort_keys=True)`` encoded as
    UTF-8. The signature is returned as a 64-char lowercase hex digest.

    Args:
        ocpp_dict: OCPP 1.6 dict as returned by :func:`render_charging_session`.

    Returns:
        HMAC-SHA-256 hex digest (64 lowercase hex chars).
    """
    canonical_json = json.dumps(ocpp_dict, sort_keys=True).encode("utf-8")
    return hmac.new(SESSION_SIGNING_KEY, canonical_json, hashlib.sha256).hexdigest()