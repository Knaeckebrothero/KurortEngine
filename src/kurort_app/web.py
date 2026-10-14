"""Shared Jinja2 environment and German display helpers for all routers."""

from __future__ import annotations

import hashlib
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
    "erzeugt": "PDF erzeugt · nicht unterschrieben",
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


def _context(request: Request) -> dict[str, Any]:
    settings = get_settings()
    return {
        "hotel_name": settings.hotel_name,
        "hotel_city": settings.hotel_city,
        "business_date": today(),
        "nav_path": request.url.path,
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
