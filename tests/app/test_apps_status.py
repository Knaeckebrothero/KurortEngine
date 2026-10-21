"""Schedule and alert boundaries, with explicit clocks and no database."""

from datetime import UTC, date, datetime

from kurort_app.apps.models import AppRecord
from kurort_app.apps.registry import AppRegistry

TODAY = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 10, tzinfo=UTC)


def record(id, collection, **data):
    return AppRecord(
        id=id,
        collection=collection,
        app_slug="geraetecheck",
        data=data,
        deleted_at=None,
        out_of_range=False,
        created_at=NOW,
    )


def test_schedules_day_variable_interval_active_and_hours(app_definitions):
    from kurort_app.apps.status import schedules

    app = AppRegistry().valid["geraetecheck"]
    target = record(1, "geraete", name="Küche", aktiv=True, intervall=3)
    inactive = record(2, "geraete", name="Still", aktiv=False)
    result = schedules(app, [target, inactive], today=TODAY, now=NOW)
    assert len(result) == 1 and result[0].status == "überfällig"
    assert result[0].note == "noch nie erfasst"
    reading = record(3, "messungen", geraet=1, gemessen_am="2026-10-13T05:30:00+00:00")
    due = schedules(app, [target, reading], today=TODAY, now=NOW)[0]
    assert (due.status, due.note) == ("fällig", "fällig am 14.10.2026")
    reading.data["gemessen_am"] = "2026-10-12T05:30:00+00:00"
    due = schedules(app, [target, reading], today=TODAY, now=NOW)[0]
    assert (due.status, due.note) == ("überfällig", "fällig seit 13.10.2026")
    s = app.schedules[0]
    s.every_days, s.every_days_field = None, "intervall"
    assert schedules(app, [target, reading], today=TODAY, now=NOW)[0].status == "erledigt"
    s.every_days_field, s.every_hours = None, 4
    assert schedules(app, [target, reading], today=TODAY, now=NOW)[0].status == "überfällig"
    reading.data["gemessen_am"] = "2026-10-14T08:00:00+00:00"
    assert schedules(app, [target, reading], today=TODAY, now=NOW)[0].status == "erledigt"
    target.deleted_at = NOW
    assert schedules(app, [target, reading], today=TODAY, now=NOW) == []


def test_alert_window_expiry_silence_and_soft_delete(app_definitions):
    from kurort_app.apps.status import alerts

    app = AppRegistry().valid["geraetecheck"]
    target = record(1, "geraete", pruefung_bis="2026-10-20")
    alert = alerts(app, [target], today=TODAY)[0]
    assert (alert.status, alert.note) == ("läuft ab", "Prüfung gültig bis 20.10.2026")
    target.data["pruefung_bis"] = "2026-10-13"
    assert alerts(app, [target], today=TODAY)[0].status == "abgelaufen"
    target.data["pruefung_bis"] = "2027-01-01"
    assert alerts(app, [target], today=TODAY) == []
    target.data.update(pruefung_bis="2026-10-13", ausgemustert=True)
    assert alerts(app, [target], today=TODAY) == []
    target.data["ausgemustert"] = False
    target.deleted_at = NOW
    assert alerts(app, [target], today=TODAY) == []
