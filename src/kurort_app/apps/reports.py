"""Period-filtered reports with exact German CSV and portable WinAnsi PDFs."""

import csv
import io
import unicodedata
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from kurort_app.apps import store
from kurort_app.config import HOTEL_TZ, get_settings
from kurort_app.web import staff_name

_FALLBACK = str.maketrans(
    {"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O", "\u2212": "-", "\u2009": " "}
)


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


def build_rows(session, app, section, start, end, *, unit=False):
    collection = app.collection(section.collection)
    result = []
    for row in store.query(session, app, collection, von=start, bis=end):
        cells = [
            store.display(session, app, collection.field(key), row.data.get(key), unit=unit)
            for key in section.columns
        ]
        cells = ["" if value == "–" else value for value in cells]
        result.append([*cells, "ja" if row.out_of_range else "nein"])
    return result


def csv_export(session, app, collection, start, end, *, columns=None):
    from kurort_app.apps.schema import ReportSection

    collection = app.collection(collection) if isinstance(collection, str) else collection
    columns = columns or [field.key for field in collection.fields]
    section = ReportSection(collection=collection.key, columns=columns)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
    writer.writerow([*[collection.field(key).label for key in columns], "Abweichung"])
    writer.writerows(build_rows(session, app, section, start, end))
    return stream.getvalue().encode("utf-8-sig")


def _column_widths(rows, total, font="Helvetica", size=10, padding=14):
    """Widths sized by content (BodyText is Helvetica 10): no column narrower than its
    longest word; then the columns closest to fitting their longest line on one line get
    it, and long text takes the rest."""

    def width(text):
        return stringWidth(text, font, size) + padding

    columns = list(zip(*rows, strict=True))
    widths = [max(width(word) for cell in col for word in cell.split() or [""]) for col in columns]
    widths = [min(w, total / len(columns)) for w in widths]
    if sum(widths) >= total:
        return [w * total / sum(widths) for w in widths]
    wish = [max(width(cell) for cell in col) for col in columns]
    budget = total - sum(widths)
    for i in sorted(range(len(widths)), key=lambda i: wish[i] - widths[i]):
        extra = min(wish[i] - widths[i], budget)
        widths[i] += extra
        budget -= extra
    return [w + budget * w / sum(widths) for w in widths]


class _NumberedCanvas(Canvas):
    """Draws "Seite X von Y" once the page count is known."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for state in self._pages:
            self.__dict__.update(state)
            self.setFont("Helvetica", 8)
            self.drawRightString(
                self._pagesize[0] - 32, 18, f"Seite {self._pageNumber} von {len(self._pages)}"
            )
            super().showPage()
        super().save()


def pdf_export(session, app, report, start, end, username):
    settings = get_settings()
    size = landscape(A4) if any(len(s.columns) > 5 for s in report.sections) else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=size,
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32,
        title=report.title,
        author=settings.hotel_name,
    )
    styles = getSampleStyleSheet()

    def paragraph(text, style="BodyText"):
        return Paragraph(escape(_pdf_text(str(text))), styles[style])

    story = [
        paragraph(settings.hotel_name, "Title"),
        paragraph(report.title, "Heading1"),
        paragraph(f"{start:%d.%m.%Y} bis {end:%d.%m.%Y}"),
        paragraph(
            f"Erstellt am {datetime.now(UTC).astimezone(HOTEL_TZ):%d.%m.%Y %H:%M} "
            f"von {staff_name(username)}"
        ),
        Spacer(1, 16),
    ]
    for section in report.sections:
        collection = app.collection(section.collection)
        story.append(paragraph(collection.title, "Heading2"))
        headings = [*[collection.field(key).label for key in section.columns], "Abweichung"]
        rows = [
            [*row[:-1], "Abweichung" if row[-1] == "ja" else "–"]
            for row in build_rows(session, app, section, start, end, unit=True)
        ]
        texts = [[_pdf_text(str(cell)) for cell in row] for row in [headings, *rows]]
        table = Table(
            [[paragraph(cell) for cell in row] for row in texts],
            repeatRows=1,
            colWidths=_column_widths(texts, doc.width),
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F3F4")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#C8D1D5")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.extend([table, Spacer(1, 16)])
    story.extend(
        [
            Spacer(1, 24),
            paragraph("Unterschrift Verantwortliche/r: ________________________"),
            Spacer(1, 12),
            paragraph("Datum: ________________________"),
        ]
    )
    doc.build(story, canvasmaker=_NumberedCanvas)
    return buf.getvalue()
