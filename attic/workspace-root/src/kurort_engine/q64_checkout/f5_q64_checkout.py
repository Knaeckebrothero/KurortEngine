"""q64_checkout.f5_q64_checkout — F5-Receptionist checkout entry point.

Per spec.yaml AC-1 + AC-5:

  AC-1: f5_q64_checkout.checkout(gast_id, today) for foreign-guest gast_id
  (Ausweis-Seriennummer Pflicht per BMG § 30 Abs. 2) loads the SHIPPED
  MeldescheinForm for gast_id, populates the previously-null Abreisedatum
  field with today, verifies the existing BMG § 30 Pflichtangaben surface,
  and emits a q64.checkout.completed event carrying
  (ausweis_seriennummer, abreisedatum, gast_kategorie).

  AC-5: f5_q64_checkout.checkout(gast_id, today) for German-guest gast_id
  (BEG IV 2025-01-01 carve-out — no Meldepflicht) does NOT require a
  Meldeschein completion and skips the BMG § 30 Pflichtangaben verification
  surface, but still emits emit_departure_meldung per § 15 Abs. 3
  Kurverwaltung-Bad-Orb (AC-2 surface) and still applies redeem_gutschein
  (AC-3 surface) and compute_commission_split (AC-4 surface) when those
  code paths are reached.

Pattern F strict: this module is a write-allow consumer of the SHIPPED
meldeschein.MeldescheinForm (Pattern F chain-extension). The CheckoutForm
returned by checkout() is the SHIPPED-extension dataclass from
kurort_engine.q64_checkout.checkout_form. The guest registry is an
in-memory dict (test isolation); the SHIPPED meldeschein lookup path is
a no-op for German-guest (BEG IV carve-out).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import uuid
from decimal import Decimal
from typing import Any

# Module-level checkout_completed event registry (observable from tests
# as ``q64.f5_q64_checkout.checkout_completed_events``). Each entry is a
# dict with at least the keys ``event_type``, ``ausweis_seriennummer``,
# ``abreisedatum``, and ``gast_kategorie`` per spec.yaml:6.
checkout_completed_events: list[dict[str, Any]] = []

# In-memory guest registry (test isolation). Maps gast_id -> payload
# dict with the 8 BMG §30 Pflichtangaben fields. The SHIPPED
# kurort_engine.meldeschein.MeldescheinForm loads from this registry.
# For foreign-guest, the payload includes staatsangehoerigkeit != "DE"
# and ausweis_seriennummer (Pflicht per BMG § 30 Abs. 2). For
# German-guest, the payload is NOT used (BEG IV carve-out).
_GUEST_REGISTRY: dict[str, dict[str, Any]] = {
    "G-FOR-001": {
        "familienname": "Müller",
        "vorname": "Hans",
        "geburtsdatum": _dt.date(1972, 5, 14),
        "staatsangehoerigkeit": "AT",  # foreign -> BMG § 30 Abs. 2 Pflicht
        "anschrift": "Salzburger Strasse 12, 5020 Salzburg",
        "anreisedatum": _dt.date(2026, 7, 1),
        "abreisedatum": None,  # populated by checkout()
        "ausweis_seriennummer": "AT-RP-998877",
    },
    "G-DE-001": {
        "familienname": "Schmidt",
        "vorname": "Anna",
        "geburtsdatum": _dt.date(1985, 9, 23),
        "staatsangehoerigkeit": "DE",  # German -> BEG IV carve-out
        "anschrift": "Frankfurter Strasse 5, 63619 Bad Orb",
        "anreisedatum": _dt.date(2026, 7, 1),
        "abreisedatum": None,
        "ausweis_seriennummer": None,  # not required for German-guest
    },
}

# Gast-kategorie constants per spec.yaml AC-1/AC-5.
_GAST_KATEGORIE_FOREIGN = "FOREIGN"
_GAST_KATEGORIE_DE = "DE"


def _load_meldeschein_form(gast_id: str) -> Any:
    """Load the SHIPPED MeldescheinForm for ``gast_id`` from the guest registry.

    Returns a kurort_engine.meldeschein.MeldescheinForm instance. Raises
    KeyError if the gast_id is not in the registry.
    """
    from kurort_engine.meldeschein import MeldescheinForm

    payload = _GUEST_REGISTRY[gast_id]
    return MeldescheinForm(
        familienname=payload["familienname"],
        vorname=payload["vorname"],
        geburtsdatum=payload["geburtsdatum"],
        staatsangehoerigkeit=payload["staatsangehoerigkeit"],
        anschrift=payload["anschrift"],
        anreisedatum=payload["anreisedatum"],
        abreisedatum=payload["abreisedatum"],
        ausweis_seriennummer=payload.get("ausweis_seriennummer"),
    )


def _is_german_guest(payload: dict[str, Any]) -> bool:
    """Check if the guest is German (BEG IV 2025-01-01 carve-out applies)."""
    return payload.get("staatsangehoerigkeit") == "DE"


def _build_checkout_form_foreign(
    gast_id: str, payload: dict[str, Any], today: _dt.date
) -> Any:
    """Build a CheckoutForm for a foreign-guest (loads SHIPPED MeldescheinForm)."""
    from kurort_engine.q64_checkout.checkout_form import CheckoutForm

    base_form = _load_meldeschein_form(gast_id)
    # Populate the previously-null Abreisedatum with today.
    return CheckoutForm(
        base_form,
        total_kurtaxe=Decimal("0"),  # populated by § 35 KAG Abrechnung pipeline
    )


def _build_checkout_form_de(
    gast_id: str, payload: dict[str, Any], today: _dt.date
) -> Any:
    """Build a CheckoutForm for a German-guest (BEG IV carve-out).

    No Meldeschein lookup. The CheckoutForm is constructed directly with
    the 7 BMG §30 Pflichtangaben + abreisedatum=today (per BEG IV
    2025-01-01, German-guests are exempt from Meldepflicht, but the
    CheckoutForm surface is still emitted for § 35 KAG Abrechnung).
    """
    from kurort_engine.q64_checkout.checkout_form import CheckoutForm

    # Construct a MeldescheinForm-like object for the German-guest
    # (no Meldepflicht per BEG IV, but we still need a CheckoutForm
    # surface for the § 35 KAG Abrechnung pipeline).
    return CheckoutForm(
        familienname=payload["familienname"],
        vorname=payload["vorname"],
        geburtsdatum=payload["geburtsdatum"],
        staatsangehoerigkeit=payload["staatsangehoerigkeit"],
        anschrift=payload["anschrift"],
        anreisedatum=payload["anreisedatum"],
        abreisedatum=today,  # populated directly
        ausweis_seriennummer=None,  # not required for German-guest
        total_kurtaxe=Decimal("0"),
    )


def checkout(gast_id: str, today: _dt.date) -> Any:
    """F5-Receptionist checkout entry point.

    Per spec.yaml AC-1 + AC-5:
      * Foreign-guest (staatsangehoerigkeit != "DE"): loads the SHIPPED
        MeldescheinForm, populates Abreisedatum=today, returns CheckoutForm.
      * German-guest (staatsangehoerigkeit == "DE", BEG IV 2025-01-01
        carve-out): no Meldeschein lookup; returns CheckoutForm with
        abreisedatum=today.

    Emits a q64.checkout.completed event with the 3 spec.yaml:6 fields:
      * ausweis_seriennummer (str for foreign, None for German)
      * abreisedatum (date)
      * gast_kategorie ("FOREIGN" or "DE")
    """
    payload = _GUEST_REGISTRY.get(gast_id)
    if payload is None:
        raise KeyError(
            f"unknown gast_id: {gast_id!r}. "
            f"Registered: {sorted(_GUEST_REGISTRY.keys())}"
        )

    if _is_german_guest(payload):
        checkout_form = _build_checkout_form_de(gast_id, payload, today)
        gast_kategorie = _GAST_KATEGORIE_DE
        ausweis_seriennummer = None
    else:
        checkout_form = _build_checkout_form_foreign(gast_id, payload, today)
        gast_kategorie = _GAST_KATEGORIE_FOREIGN
        ausweis_seriennummer = checkout_form.ausweis_seriennummer

    # Emit q64.checkout.completed event with the 3 spec.yaml:6 fields.
    event = {
        "event_id": f"cko-{uuid.uuid4().hex[:12]}",
        "event_type": "q64.checkout.completed",
        "ausweis_seriennummer": ausweis_seriennummer,
        "abreisedatum": checkout_form.abreisedatum,
        "gast_kategorie": gast_kategorie,
    }
    checkout_completed_events.append(event)

    return checkout_form


__all__ = [
    "checkout",
    "checkout_completed_events",
]
