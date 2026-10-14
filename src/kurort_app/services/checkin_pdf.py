"""Printable Meldeschein (A4 PDF) for a validated engine ``MeldescheinForm``.

``kurort_engine.meldeschein.render`` still emits a Stage-2 placeholder (a
``%PDF`` header followed by comment lines, which no viewer can open), so the
web app lays out the real document with reportlab here. The data on it is
exactly the engine-validated form.
"""

from __future__ import annotations

import io
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from kurort_engine.meldeschein import MeldescheinForm

HOTEL_TZ = ZoneInfo("Europe/Berlin")


def _local(value: datetime) -> datetime:
    return value.astimezone(HOTEL_TZ) if value.tzinfo else value


RHINE = HexColor("#075D73")
INK = HexColor("#172329")
MUTED = HexColor("#52636B")
RULE = HexColor("#C8D1D5")
TINT = HexColor("#EAF7F9")

# Standard PDF fonts are WinAnsi-encoded; map the few Central-European
# letters NFKD cannot decompose so names never print as missing glyphs.
_FALLBACK = str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O"})


def _pdf_text(value: str) -> str:
    out = []
    for ch in value.translate(_FALLBACK):
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = "".join(
                c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)
            )
            out.append(base if base and base.isascii() else "?")
    return "".join(out)


def _field(c: Canvas, x: float, y: float, w: float, label: str, value: str) -> None:
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawString(x, y + 5.2 * mm, label.upper())
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(INK)
    c.drawString(x, y + 0.6 * mm, _pdf_text(value) or "–")
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(x, y - 1.2 * mm, x + w, y - 1.2 * mm)


def render_meldeschein_pdf(
    form: MeldescheinForm,
    *,
    form_id: str,
    hotel_name: str,
    hotel_city: str,
    reservation_code: str,
    room: str,
    co_travellers: list[str],
    generated_at: datetime,
) -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    width, height = A4
    left, right = 20 * mm, width - 20 * mm
    content_w = right - left
    c.setTitle(f"Meldeschein {form.vorname} {form.familienname}")
    c.setAuthor(hotel_name)
    c.setSubject("Besonderer Meldeschein für Beherbergungsstätten (§§ 29, 30 BMG)")

    # Header band
    c.setFillColor(RHINE)
    c.rect(0, height - 34 * mm, width, 34 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 17)
    c.drawString(left, height - 16 * mm, _pdf_text(f"{hotel_name} · {hotel_city}"))
    c.setFont("Helvetica", 10)
    c.drawString(
        left, height - 23 * mm, "Besonderer Meldeschein für Beherbergungsstätten · §§ 29, 30 BMG"
    )
    c.setFont("Helvetica", 8.5)
    c.drawRightString(right, height - 16 * mm, f"Formular {form_id}")
    c.drawRightString(right, height - 23 * mm, f"Reservierung {reservation_code}")

    y = height - 50 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Angaben zur Person")
    y -= 12 * mm
    half = (content_w - 8 * mm) / 2
    _field(c, left, y, half, "Familienname", form.familienname)
    _field(c, left + half + 8 * mm, y, half, "Vorname", form.vorname)
    y -= 13 * mm
    _field(c, left, y, half, "Geburtsdatum", f"{form.geburtsdatum:%d.%m.%Y}")
    _field(c, left + half + 8 * mm, y, half, "Staatsangehörigkeit", form.staatsangehoerigkeit)
    y -= 13 * mm
    _field(c, left, y, content_w, "Anschrift (Wohnort)", form.anschrift)
    y -= 13 * mm
    _field(
        c,
        left,
        y,
        half,
        "Ausweis-/Passnummer (§ 30 Abs. 2 BMG)",
        form.ausweis_seriennummer or "nicht erforderlich",
    )

    y -= 17 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Aufenthalt")
    y -= 12 * mm
    third = (content_w - 16 * mm) / 3
    _field(c, left, y, third, "Anreise", f"{form.anreisedatum:%d.%m.%Y}")
    _field(c, left + third + 8 * mm, y, third, "Abreise", f"{form.abreisedatum:%d.%m.%Y}")
    nights = (form.abreisedatum - form.anreisedatum).days
    _field(c, left + 2 * (third + 8 * mm), y, third, "Nächte", str(nights))
    y -= 13 * mm
    _field(c, left, y, content_w, "Zimmer", room)
    y -= 13 * mm
    _field(
        c,
        left,
        y,
        content_w,
        "Mitreisende (Ehegatte, Lebenspartner, minderjährige Kinder)",
        ", ".join(co_travellers) if co_travellers else "keine",
    )

    # Notice box
    y -= 20 * mm
    c.setFillColor(TINT)
    c.roundRect(left, y - 4 * mm, content_w, 16 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.5)
    c.drawString(
        left + 4 * mm,
        y + 6 * mm,
        "Die Angaben werden nach § 30 Abs. 4 BMG ein Jahr aufbewahrt und danach gelöscht.",
    )
    c.drawString(
        left + 4 * mm,
        y + 1 * mm,
        _pdf_text(
            f"Der Meldeschein dient zugleich der Erhebung des Kurbeitrags der Stadt {hotel_city}."
        ),
    )

    # Signature
    y -= 32 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(left, y, left + 80 * mm, y)
    c.line(right - 60 * mm, y, right, y)
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(left, y - 4.5 * mm, "Unterschrift der beherbergten Person")
    c.drawString(right - 60 * mm, y - 4.5 * mm, "Ort, Datum")
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    c.drawString(
        right - 60 * mm, y + 2 * mm, _pdf_text(f"{hotel_city}, {form.anreisedatum:%d.%m.%Y}")
    )

    # Footer
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawString(
        left,
        14 * mm,
        _pdf_text(f"Erzeugt {_local(generated_at):%d.%m.%Y %H:%M} Uhr · KurortEngine · {form_id}"),
    )
    c.drawRightString(right, 14 * mm, "PDF erzeugt · gilt erst mit Unterschrift")
    c.showPage()
    c.save()
    return buf.getvalue()
