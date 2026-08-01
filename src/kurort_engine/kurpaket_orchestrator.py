"""Kurpaket orchestrator — compose quote + render confirmation + QR payload."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from kurort_engine.heilbad_badge import render_badge
from kurort_engine.kurpaket_guest_card import issue_guest_card
from kurort_engine.kurpaket_pricing import price_for_template
from kurort_engine.kurpaket_templates import get_template


class SGBV23CertificateMissing(Exception):
    """Raised when a Spezial-Heilbad booking lacks a §23 SGB V Muster 13."""

    def __init__(self, message: str = "§23 SGB V Muster 13 certificate required") -> None:
        super().__init__(message)


@dataclass(frozen=True, kw_only=True)
class KurpaketQuote:
    template_code: str
    template_name: str
    nights: int
    spa_treatments_per_day: int
    spa_treatments_total: int
    board: str
    price_per_person_eur: Decimal
    total_price_eur: Decimal
    guest_card_issued: bool
    heilbad_badge: str


def compose_quote(booking: dict[str, Any]) -> KurpaketQuote:
    """Compose a KurpaketQuote for ``booking``.

    Selects the template, computes the price, issues a Gästekarte, and
    raises :class:`SGBV23CertificateMissing` for Spezial-Heilbad (template E)
    bookings that lack a §23 SGB V Muster 13 certificate.
    """
    template_code = str(booking.get("template_code", "")).upper()
    template = get_template(template_code)
    nights = int(booking.get("nights", template.nights))
    guests = int(booking.get("guests", 1))

    if template.muster13_required and not booking.get("muster13_id"):
        raise SGBV23CertificateMissing(
            "§23 SGB V Muster 13 certificate required for Spezial-Heilbad "
            "(template E) — no certificate supplied."
        )

    price_per_person = price_for_template(template_code, nights, guests)
    total_price = price_per_person * Decimal(guests)
    card = issue_guest_card(booking)

    return KurpaketQuote(
        template_code=template.code,
        template_name=template.name,
        nights=nights,
        spa_treatments_per_day=template.spa_treatments_per_day,
        spa_treatments_total=template.spa_treatments_total,
        board=template.board,
        price_per_person_eur=price_per_person,
        total_price_eur=total_price,
        guest_card_issued=True,
        heilbad_badge=card.heilbad_badge,
    )


def render_confirmation(booking: dict[str, Any]) -> str:
    """Render a human-readable booking confirmation string.

    Embeds the 'Heilbad 2026' badge only when the property currently holds
    the designation (i.e. ``today`` is within the 04.03.2026..2036 window).
    """
    template_code = str(booking.get("template_code", "")).upper()
    template = get_template(template_code)
    today = booking.get("today") or booking.get("arrival") or date.today()
    badge = render_badge(today) if isinstance(today, date) else ""
    guest = booking.get("guest_name", "")
    arrival = booking.get("arrival")
    departure = booking.get("departure")
    arrival_s = arrival.isoformat() if isinstance(arrival, date) else ""
    departure_s = departure.isoformat() if isinstance(departure, date) else ""
    quote = compose_quote(booking)
    lines = [
        f"Kurpaket-Bestaetigung: {template.name} ({template.code})",
        f"Gast: {guest}",
        f"Aufenthalt: {arrival_s} bis {departure_s} ({quote.nights} Naechte)",
        f"Preis pro Person: {quote.price_per_person_eur} EUR",
        f"Gaestekarte ausgestellt: {'ja' if quote.guest_card_issued else 'nein'}",
    ]
    if badge:
        lines.append(f"Status: {badge}")
    return "\n".join(lines)


def render_qr_payload(booking: dict[str, Any]) -> str:
    """Render the printable QR payload for the Gästekarte (post-2036 Heilbad-free)."""
    card = issue_guest_card(booking)
    return card.qr_payload


# Duck-typed aliases accepted by the test surface.
compose = compose_quote
build = compose_quote
format_confirmation = render_confirmation
render_text = render_confirmation
format_qr_payload = render_qr_payload
build_qr_payload = render_qr_payload