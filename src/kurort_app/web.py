"""Shared Jinja2 environment and German display helpers for all routers."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from kurort_app.config import get_settings, today

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
HOTEL_TZ = ZoneInfo("Europe/Berlin")


def _static_version() -> str:
    """Cache-buster for /static URLs: changes whenever any asset changes."""
    digest = hashlib.sha1(usedforsecurity=False)
    for path in sorted(STATIC_DIR.rglob("*")):
        if path.is_file():
            digest.update(f"{path.name}:{path.stat().st_mtime_ns}".encode())
    return digest.hexdigest()[:10]


STATIC_VERSION = _static_version()

WEEKDAYS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
WEEKDAYS_LONG = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONTHS = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)

STATUS_LABELS = {
    "reserved": "Reserviert",
    "checked_in": "Im Haus",
    "checked_out": "Abgereist",
    "cancelled": "Storniert",
    "no_show": "No-Show",
}
PAYMENT_STATE_LABELS = {"bezahlt": "Bezahlt", "offen": "Offen", "guthaben": "Guthaben"}
CHANNEL_LABELS = {
    "direct": "Direkt",
    "phone": "Telefon",
    "email": "E-Mail",
    "booking.com": "Booking.com",
    "walk-in": "Walk-in",
}
EXEMPTION_LABELS = {
    "geschaeftsreisender": "Geschäftsreise",
    "schwerbehindert_100": "Schwerbehindert (GdB 100)",
}
MELDESCHEIN_LABELS = {
    "offen": "Meldeschein offen",
    "gedruckt": "In AVS gedruckt · Unterschrift fehlt",
    "unterschrieben": "Meldeschein unterschrieben",
}


def fmt_date(value: date | None, style: str = "short") -> str:
    """``short`` → 14.10.2026, ``day`` → Mi 14.10., ``long`` → Mittwoch, 14. Oktober 2026."""
    if value is None:
        return "–"
    if isinstance(value, datetime):
        value = _local(value).date()
    if style == "day":
        return f"{WEEKDAYS[value.weekday()]} {value:%d.%m.}"
    if style == "long":
        return (
            f"{WEEKDAYS_LONG[value.weekday()]}, {value.day}. {MONTHS[value.month - 1]} {value.year}"
        )
    return f"{value:%d.%m.%Y}"


def _local(value: datetime) -> datetime:
    """Timestamps are stored in UTC; staff read them in the hotel's time zone."""
    return value.astimezone(HOTEL_TZ) if value.tzinfo else value


def fmt_time(value: time | datetime | None) -> str:
    if value is None:
        return "–"
    if isinstance(value, datetime):
        value = _local(value)
    return f"{value:%H:%M}"


def fmt_money(value: Decimal | float | int | None) -> str:
    """German currency format: 1.234,50 €."""
    if value is None:
        return "–"
    text = f"{Decimal(value):,.2f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".") + " €"


def redirect_with_notice(url: str, text: str, kind: str = "success") -> RedirectResponse:
    """303 back to a page that shows ``text`` as a flash notice."""
    sep = "&" if "?" in url else "?"
    return RedirectResponse(
        f"{url}{sep}{urlencode({'notice': text, 'notice_kind': kind})}", status_code=303
    )


@dataclass(frozen=True)
class NavItem:
    """One sidebar link. ``icon`` is the inner markup of a 24×24 stroke SVG."""

    href: str
    label: str
    icon: str
    group: str  # one of NAV_GROUPS
    roles: tuple[str, ...] = ("rezeption", "leitung")  # who sees the link (login on)
    match: str | None = None  # path prefix that marks the link active; default href


NAV_GROUPS = ("Heute", "Planung", "Apps", "Verwaltung")

# Static sidebar, in display order within each group. A feature adds its link
# with one NAV.append(...) in its own module; links that depend on the
# database (installed apps) come from a function appended to NAV_PROVIDERS.
NAV: list[NavItem] = [
    NavItem(
        "/",
        "Übersicht",
        '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
        "Heute",
    ),
    NavItem(
        "/anreisen",
        "Anreisen",
        '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="M10 17l5-5-5-5"/>'
        '<path d="M15 12H3"/>',
        "Heute",
    ),
    NavItem(
        "/abreisen",
        "Abreisen",
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/>'
        '<path d="M21 12H9"/>',
        "Heute",
    ),
    NavItem(
        "/im-haus",
        "Im Haus",
        '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/>'
        '<path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
        "Heute",
    ),
    NavItem(
        "/reservierungen",
        "Reservierungen",
        '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
        "Planung",
    ),
    NavItem(
        "/zimmerplan",
        "Zimmerplan",
        '<rect x="3" y="4" width="18" height="17" rx="2"/>'
        '<path d="M3 9h18M8 2v4M16 2v4M7 13h4M13 17h4"/>',
        "Planung",
    ),
]
NAV_PROVIDERS: list[Callable[[Request], list[NavItem]]] = []


def nav_groups(request: Request) -> list[tuple[str, list[NavItem]]]:
    """The sidebar the current user may see, as (group, links) in NAV_GROUPS order."""
    user = getattr(request.state, "user", None)
    items = list(NAV)
    for provider in NAV_PROVIDERS:
        items.extend(provider(request))
    if user is not None:
        items = [i for i in items if set(i.roles) & set(user.roles)]
    groups = [(g, [i for i in items if i.group == g]) for g in NAV_GROUPS]
    return [(g, links) for g, links in groups if links]


def _context(request: Request) -> dict[str, Any]:
    settings = get_settings()
    return {
        "hotel_name": settings.hotel_name,
        "hotel_city": settings.hotel_city,
        "business_date": today(),
        "nav_path": request.url.path,
        "nav_groups": nav_groups(request),
        "static_version": STATIC_VERSION,
        "current_user": getattr(request.state, "user", None),
        "auth_enabled": getattr(request.state, "auth_enabled", False),
        # Post/redirect/get notices: redirect to ...?notice=<text>&notice_kind=success|warning|danger
        "flash": (
            {
                "text": request.query_params["notice"],
                "kind": request.query_params.get("notice_kind", "success"),
            }
            if request.query_params.get("notice")
            else None
        ),
    }


templates = Jinja2Templates(directory=str(TEMPLATES_DIR), context_processors=[_context])
templates.env.filters.update(
    date=fmt_date,
    time=fmt_time,
    money=fmt_money,
    status_label=lambda s: STATUS_LABELS.get(s, s),
    channel_label=lambda s: CHANNEL_LABELS.get(s, s),
    exemption_label=lambda s: EXEMPTION_LABELS.get(s, s) if s else "–",
    meldeschein_label=lambda s: MELDESCHEIN_LABELS.get(s, s),
)


SLOT_LABELS = {"vormittag": "Vormittag", "nachmittag": "Nachmittag", "ganztags": "Ganztags"}
SPACE_STATUS_LABELS = {
    "angefragt": "Angefragt",
    "bestaetigt": "Bestätigt",
    "storniert": "Storniert",
}
templates.env.filters.update(
    slot_label=lambda s: SLOT_LABELS.get(s, s),
    space_status_label=lambda s: SPACE_STATUS_LABELS.get(s, s),
)


EMAIL_STATUS_LABELS = {
    "queued": "Versand ausstehend",
    "sent": "gesendet",
    "failed": "fehlgeschlagen",
    "logged": "protokolliert – nicht versendet",
}
LATE_STATUS_LABELS = {
    "vorbereitet": "Vorbereitet",
    "angereist": "Meldeschein ausstehend",
    "abgeschlossen": "Abgeschlossen",
    "abgebrochen": "Abgebrochen",
    "nicht_angereist": "Nicht angereist",
}
templates.env.filters.update(
    email_status_label=lambda s: EMAIL_STATUS_LABELS.get(s, s),
    late_status_label=lambda s: LATE_STATUS_LABELS.get(s, s),
)
