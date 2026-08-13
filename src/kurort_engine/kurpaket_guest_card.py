"""Kurpaket digital Gästekarte — QR + Heilbad badge + L4-004 12-column reuse."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

# Re-use the L4-004 12-column Kurtaxe remittance CSV adapter (AC-12).
from kurort_engine.heilbad_badge import render_badge
from kurort_engine.reporting import (  # noqa: F401  AC-12 reuse
    AC4_HEADER_COLUMNS,
    generate_monthly_remittance_csv,
)


@dataclass(frozen=True, kw_only=True)
class KurpaketGuestCard:
    booking_id: str
    guest_name: str
    template_code: str
    valid_from: date
    valid_until: date
    qr_payload: str
    heilbad_badge: str
    schema: tuple[str, ...] = AC4_HEADER_COLUMNS


def issue_guest_card(booking: dict[str, Any]) -> KurpaketGuestCard:
    """Issue a digital Gästekarte for ``booking``."""
    booking_id = str(booking.get("booking_id", ""))
    guest_name = str(booking.get("guest_name", ""))
    template_code = str(booking.get("template_code", "")).upper()
    arrival = booking.get("arrival")
    departure = booking.get("departure")
    nights = int(booking.get("nights", 0))
    today = booking.get("today") or arrival or date.today()

    qr_payload = (
        f"GAESTEKARTE|{booking_id}|{guest_name}|template={template_code}"
        f"|valid_from={arrival.isoformat() if arrival else ''}"
        f"|valid_until={departure.isoformat() if departure else ''}"
        f"|nights={nights}"
    )
    badge_text = render_badge(today) if isinstance(today, date) else ""
    valid_from = arrival if isinstance(arrival, date) else date.today()
    valid_until = departure if isinstance(departure, date) else (
        date.fromordinal(valid_from.toordinal() + nights)
    )
    return KurpaketGuestCard(
        booking_id=booking_id, guest_name=guest_name,
        template_code=template_code, valid_from=valid_from,
        valid_until=valid_until, qr_payload=qr_payload,
        heilbad_badge=badge_text, schema=AC4_HEADER_COLUMNS,
    )


# Duck-typed aliases.
issue = issue_guest_card
render = issue_guest_card
create = issue_guest_card