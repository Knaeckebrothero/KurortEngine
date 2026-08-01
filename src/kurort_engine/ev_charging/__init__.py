"""kurort_engine.ev_charging — Q5.2 E-Bike/E-Auto charging (Tier-2).

This package extends ``kurort_engine`` with a chargecloud OCPP 1.6 mediator
+ wallbox meter read + BMF 2026-01 Wallbox-Abrechnung-compliant invoice
line item + Kurkarte-tagged reservation match. Iteration 24 (Developer) —
chosen by Critic verdict (iter-23) from iter-22 Scholar Proposal 002.

Modules
-------

* :mod:`ocpp_bridge` — chargecloud OCPP 1.6 wire-format renderer + HMAC
  signer (AC-1)
* :mod:`meter` — wallbox meter read producing a :class:`MeterReading`
  dataclass (AC-2)
* :mod:`invoice_line_item` — BMF 2026-01 Wallbox-Abrechnung-compliant
  folio line item with §14 UStG Pflichtangaben + 19 % USt (AC-3, Phase 7)
* :mod:`reservation_match` — Kurkarte-tagged booking → wallbox session
  pairing via the check-in / checkout window (AC-4, Phase 7)

Cross-cutting BFSG-AA + WCAG 2.1 AA compliance is enforced via
:class:`BFSGComplianceError` (AC-5, Phase 9).

Public API (re-exported)
------------------------

* :func:`render_charging_session` — chargecloud OCPP 1.6 dict renderer (AC-1)
* :func:`sign_charging_session` — HMAC-SHA-256 hex signer (AC-1)
* :data:`SESSION_SIGNING_KEY` — placeholder HMAC key (test-only, NI-2)
* :func:`read_session` — wallbox meter read (AC-2)
* :class:`MeterReading` — meter read dataclass (AC-2)
* :class:`BFSGComplianceError` — raised on BFSG-AA / WCAG 2.1 AA violation
  (AC-5)

Pre-engagement credentials (NI-2)
---------------------------------

* chargecloud API client (REST over OAuth2 to ``api.chargecloud.de``) — DEFERRED
  to iter-25+ Tier-3; pilot uses local rendering + signing only.
* Apple Developer PassKit cert + Google Wallet API JWT signing key — placeholder
  HMAC signing key ``kurort-engine-ev-charging-pilot-signing-key`` used in tests
  (test-mode only); production key rotation deferred to iter-25+ Tier-3.

Single-standard Wallbox pilot (NI-3)
------------------------------------

1× E-Bike (Garage) + 1× E-Auto (Tiefgarage), single ``EVBox-Livo`` Wallbox
reference surface (``chargePointModel="EVBox-Livo"``).
"""
from __future__ import annotations

from kurort_engine.ev_charging.invoice_line_item import (
    InvoiceLineItem,
    append_to_folio,
)
from kurort_engine.ev_charging.meter import MeterReading, read_session
from kurort_engine.ev_charging.ocpp_bridge import (
    SESSION_SIGNING_KEY,
    render_charging_session,
    sign_charging_session,
)
from kurort_engine.ev_charging.reservation_match import ReservationMatch, match
from kurort_engine.kurkarte_wallet import lookup_apple_pass  # noqa: E402,F401


class BFSGComplianceError(ValueError):
    """Raised when an ev_charging serialisation violates BFSG-AA or WCAG 2.1 AA.

    Per AC-5 (Unwanted-behavior): if an invoice line item is rendered THEN the
    line item JSON MUST reference ``lang="de"`` on text fields AND ``label``
    (accessibilityLabel) for non-text fields (BFSG-AA + WCAG 2.1 AA guidance —
    screen-reader text contrast ≥ 4.5:1, font sizing ≥ 12pt). The exception
    message names the missing field for diagnostic clarity.

    Stub class in iter-24 Phase 5; fully wired in Phase 9 (AC-5 green).
    """


__all__ = [
    "BFSGComplianceError",
    "InvoiceLineItem",
    "MeterReading",
    "ReservationMatch",
    "SESSION_SIGNING_KEY",
    "append_to_folio",
    "lookup_apple_pass",
    "match",
    "read_session",
    "render_charging_session",
    "sign_charging_session",
]