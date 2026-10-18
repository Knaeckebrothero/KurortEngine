"""Period-filtered report rows, PDF envelope and exact CSV bytes."""

from datetime import date

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
