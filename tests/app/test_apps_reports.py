"""Period-filtered report rows, PDF envelope and exact CSV bytes."""

import re
from datetime import date

import pytest

from kurort_app.apps.registry import AppRegistry


def test_pdf_rows_and_exact_german_csv(db, app_definitions):
    from kurort_app.apps import reports, store

    app = AppRegistry().valid["geraetecheck"]
    device = store.create(db, app, "geraete", {"name": "Küche"})
    data = {
        "geraet": device.id,
        "gemessen_am": "2026-10-14T07:30",
        "temperatur": "3,5",
        "mitarbeiter": "Maria",
    }
    reading = store.create(db, app, "messungen", data)
    store.create(db, app, "messungen", {**data, "gemessen_am": "2026-09-14T07:30"})
    start, end = date(2026, 10, 1), date(2026, 10, 14)
    report = app.reports[0]
    rows = reports.build_rows(db, app, report.sections[0], start, end)
    assert len(rows) == 1 and "14.10.2026 07:30" in rows[0]
    expected = "\ufeffZeitpunkt;Gerät;Temperatur;Mitarbeiter;Maßnahme;Abweichung\r\n14.10.2026 07:30;Küche;3,5;Maria;;nein\r\n".encode()
    assert (
        reports.csv_export(db, app, "messungen", start, end, columns=report.sections[0].columns)
        == expected
    )
    pdf = reports.pdf_export(db, app, report, start, end, "m.schmidt")
    assert pdf.startswith(b"%PDF-")
    store.delete(db, app, reading)
    assert reports.build_rows(db, app, report.sections[0], start, end) == []
    assert (
        reports.csv_export(
            db, app, "messungen", start, end, columns=report.sections[0].columns
        ).count(b"\r\n")
        == 1
    )


def test_http_pdf_and_csv_envelopes_and_report_page(db, app_definitions, client):
    from kurort_app.apps import store
    from kurort_app.apps.installations import install

    app = client.app.state.apps.valid["geraetecheck"]
    install(db, app)
    device = store.create(db, app, "geraete", {"name": "Küche"})
    store.create(
        db,
        app,
        "messungen",
        {
            "geraet": device.id,
            "gemessen_am": "2026-10-14T07:30",
            "temperatur": "3,5",
            "mitarbeiter": "Maria",
        },
    )
    db.commit()
    assert "Vormonat" in client.get("/apps/geraetecheck/bericht").text
    pdf = client.get("/apps/geraetecheck/bericht.pdf?bericht=monat&von=2026-10-01&bis=2026-10-14")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert "geraetecheck-monat-2026-10-01-2026-10-14.pdf" in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF-")
    csv = client.get(
        "/apps/geraetecheck/messungen/export.csv?bericht=monat&von=2026-10-01&bis=2026-10-14"
    )
    assert (
        csv.content
        == "\ufeffZeitpunkt;Gerät;Temperatur;Mitarbeiter;Maßnahme;Abweichung\r\n14.10.2026 07:30;Küche;3,5;Maria;;nein\r\n".encode()
    )


def _pdf_streams(pdf):
    """The page content streams (reportlab writes them ASCII85 + Flate encoded)."""
    import base64
    import zlib

    texts = []
    for raw in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        raw = raw.strip()
        try:
            raw = base64.a85decode(raw, adobe=True) if raw.endswith(b"~>") else raw
            texts.append(zlib.decompress(raw).decode("latin-1"))
        except (ValueError, zlib.error):
            continue
    return "\n".join(texts)


def test_pdf_text_units_page_numbers_and_column_widths(db, app_definitions):
    from reportlab.pdfbase.pdfmetrics import stringWidth

    from kurort_app.apps import reports, store

    assert reports._pdf_text("Abtauvorgang, nach 1 Std. −19,0 °C") == (
        "Abtauvorgang, nach 1 Std. -19,0 °C"
    )
    app = AppRegistry().valid["geraetecheck"]
    device = store.create(db, app, "geraete", {"name": "Getränkekühlschrank Bar"})
    for day in range(1, 31):
        store.create(
            db,
            app,
            "messungen",
            {
                "geraet": device.id,
                "gemessen_am": f"2026-10-{day:02}T07:30",
                "temperatur": "-3,5",
                "mitarbeiter": "j.becker",
            },
        )
    report = app.reports[0]
    rows = reports.build_rows(db, app, report.sections[0], date(2026, 10, 1), date(2026, 10, 31))
    assert rows[0][2] == "-3,5" and rows[0][3] == "J. Becker"
    with_units = reports.build_rows(
        db, app, report.sections[0], date(2026, 10, 1), date(2026, 10, 31), unit=True
    )
    assert with_units[0][2] == "-3,5 °C"
    text = _pdf_streams(
        reports.pdf_export(db, app, report, date(2026, 10, 1), date(2026, 10, 31), "j.becker")
    )
    assert "von J. Becker" in text and "-3,5 \\260C" in text
    pages = re.findall(r"Seite (\d+) von (\d+)", text)
    assert len(pages) > 1 and pages == [(str(i), str(len(pages))) for i in range(1, len(pages) + 1)]
    widths = reports._column_widths(
        [["Gerät", "Temperatur"], ["Getränkekühlschrank Bar", "4,5 °C"]], 200
    )
    assert sum(widths) == pytest.approx(200)
    assert widths[0] >= stringWidth("Getränkekühlschrank Bar", "Helvetica", 10) + 12
    narrow = reports._column_widths([["Getränkekühlschrank", "x"]], 60)
    assert sum(narrow) == pytest.approx(
        60
    )  # too narrow for every word: scaled, never wider than the page
    # One long unbroken value must not squeeze the other columns to nothing.
    serial = reports._column_widths([["x" * 120, "Kurzer Text", "4,5 °C"]], 300)
    assert min(serial) >= stringWidth("Kurzer", "Helvetica", 10)


def test_report_page_period_errors_and_downloads_follow_the_form(db, app_definitions, client):
    from kurort_app.apps.installations import install

    install(db, client.app.state.apps.valid["geraetecheck"])
    db.commit()
    page = client.get("/apps/geraetecheck/bericht?bericht=monat&von=2026-10-14&bis=2026-10-01")
    assert page.status_code == 422 and "<html" in page.text
    assert "Das Ende liegt vor dem Beginn." in page.text and "PDF herunterladen" not in page.text
    assert 'value="2026-10-14"' in page.text and 'value="2026-10-01"' in page.text
    for url in (
        "/apps/geraetecheck/bericht.pdf?bericht=monat&von=2026-10-14&bis=2026-10-01",
        "/apps/geraetecheck/messungen/export.csv?bericht=monat&von=kaputt&bis=2026-10-01",
    ):
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/apps/geraetecheck/bericht?bericht=monat")
        followed = client.get(url)
        assert followed.status_code == 422 and "Bitte" in followed.text
    page = client.get("/apps/geraetecheck/bericht?bericht=monat&von=2026-10-01&bis=2026-10-14")
    assert page.status_code == 200
    assert 'form="app-report-form" formaction="/apps/geraetecheck/bericht.pdf"' in page.text
    assert 'formaction="/apps/geraetecheck/messungen/export.csv"' in page.text
