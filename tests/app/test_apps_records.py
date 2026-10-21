"""Typed record storage and HTTP behaviour of the generic CRUD surface."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from kurort_app.apps.models import AppRecord
from kurort_app.apps.registry import AppRegistry
from kurort_app.models import AuditEvent, Room


@pytest.fixture
def definition(app_definitions):
    return AppRegistry().valid["geraetecheck"]


def test_store_formats_ranges_versions_and_delete(db, definition):
    from kurort_app.apps import store, values

    db.add(Room(number="101", category="Test", floor=1, max_occupancy=1, nightly_rate=0))
    db.flush()
    device = store.create(
        db,
        definition,
        "geraete",
        {"name": "Küche", "soll_min": "0", "soll_max": "7", "aktiv": True},
        actor="m.schmidt",
    )
    data = {
        "geraet": str(device.id),
        "temperatur": "8,5",
        "gemessen_am": "2026-10-14T07:30",
        "massnahme": "Nachgekühlt",
        "zeit": "07:30",
        "anzahl": "2",
        "kontrolliert": "on",
        "zustand": "gut",
        "merkmale": ["innen", "aussen"],
        "zimmer": "101",
        "tag": "2026-10-14",
        "mitarbeiter": "m.schmidt",
    }
    reading = store.create(db, definition, "messungen", data, actor="m.schmidt")
    assert reading.data == {
        "geraet": device.id,
        "temperatur": "8.5",
        "gemessen_am": "2026-10-14T05:30:00+00:00",
        "massnahme": "Nachgekühlt",
        "zeit": "07:30",
        "anzahl": 2,
        "kontrolliert": True,
        "zustand": "gut",
        "merkmale": ["innen", "aussen"],
        "zimmer": "101",
        "tag": "2026-10-14",
        "mitarbeiter": "m.schmidt",
    }
    assert values.typed(
        definition.collection("messungen").field("temperatur"), reading.data["temperatur"]
    ) == Decimal("8.5")
    assert reading.out_of_range
    store.update(db, definition, device, {"name": "Küche", "soll_max": "20"}, actor="t.weber")
    assert reading.out_of_range  # historic judgement unchanged
    reading.data = {**reading.data, "legacy": "bewahren"}
    definition.version = 2
    store.update(db, definition, reading, {**data, "temperatur": "6,0"}, actor="t.weber")
    assert reading.data["legacy"] == "bewahren"
    assert reading.updated_by == "t.weber" and reading.updated_at
    assert reading.definition_version == 2 and not reading.out_of_range
    event = db.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "app_record.updated", AuditEvent.entity_id == str(reading.id)
        )
    ).one()
    assert event.payload["changes"]["temperatur"] == ["8.5", "6.0"]
    store.delete(db, definition, reading, actor="t.weber")
    assert reading.deleted_at and reading.deleted_by == "t.weber"
    assert store.records(db, definition, "messungen") == []
    assert db.scalars(select(AuditEvent).where(AuditEvent.action == "app_record.deleted")).one()


@pytest.mark.parametrize(
    "collection,data,key,phrase",
    [
        ("geraete", {}, "name", "Pflicht"),
        ("geraete", {"name": "x" * 81}, "name", "80"),
        (
            "messungen",
            {"geraet": 999, "temperatur": "5", "gemessen_am": "2026-10-14T07:30"},
            "geraet",
            "nicht vorhanden",
        ),
        ("messungen", {"temperatur": "101"}, "temperatur", "100"),
        ("messungen", {"temperatur": "NaN"}, "temperatur", "Zahl"),
        ("messungen", {"zustand": "unknown"}, "zustand", "Auswahl"),
        ("messungen", {"zimmer": "999"}, "zimmer", "nicht vorhanden"),
    ],
)
def test_validation_never_writes(db, definition, collection, data, key, phrase):
    from kurort_app.apps import store

    with pytest.raises(store.RecordValidationError) as exc:
        store.create(db, definition, collection, data)
    assert phrase in exc.value.errors[key]
    assert not db.scalars(select(AppRecord)).all()


def test_corrective_action_block_range_and_open_bound(db, definition):
    from kurort_app.apps import store

    device = store.create(
        db, definition, "geraete", {"name": "Küche", "soll_min": "0", "soll_max": "7"}
    )
    data = {"geraet": device.id, "temperatur": "8.5", "gemessen_am": "2026-10-14T07:30"}
    with pytest.raises(store.RecordValidationError) as exc:
        store.create(db, definition, "messungen", data)
    assert exc.value.errors["massnahme"] == "Bei einer Abweichung ist „Maßnahme“ Pflicht."
    assert exc.value.errors["temperatur"] == (
        "8,5 °C liegt über der Obergrenze 7,0 °C – bitte „Maßnahme“ eintragen."
    )
    low = {**data, "temperatur": "-1"}
    with pytest.raises(store.RecordValidationError) as exc:
        store.create(db, definition, "messungen", low)
    assert exc.value.errors["temperatur"].startswith("-1,0 °C liegt unter der Untergrenze 0,0 °C")
    field = definition.collection("messungen").field("temperatur")
    field.range.severity = "block"
    with pytest.raises(store.RecordValidationError) as exc:
        store.create(db, definition, "messungen", data)
    assert "0,0 bis 7,0 °C" in exc.value.errors["temperatur"]
    store.update(db, definition, device, {"name": "Küche", "soll_min": "0"})
    assert not store.create(db, definition, "messungen", data).out_of_range


def test_typed_query_order_search_period_and_pagination(db, definition):
    from kurort_app.apps import store

    device = store.create(db, definition, "geraete", {"name": "Küche"})
    coll = definition.collection("messungen")
    coll.order_by = "-temperatur"
    for i in range(53):
        store.create(
            db,
            definition,
            "messungen",
            {
                "geraet": device.id,
                "temperatur": str(i),
                "gemessen_am": "2026-10-14T07:30",
                "massnahme": "Küche",
            },
        )
    result = store.query(
        db, definition, coll.key, von="2026-10-14", bis="2026-10-14", q="KÜCHE", page=1
    )
    assert len(result) == 50 and result[0].data["temperatur"] == "52"
    assert len(store.query(db, definition, coll.key, page=2)) == 3
    assert store.query(db, definition, coll.key, bis="2026-10-13") == []


def test_defaults_are_business_local_and_query_overrides(definition):
    from kurort_app.apps import values

    now = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)
    filled = values.defaults(
        definition.collection("geraete"), "m.schmidt", today=datetime(2026, 10, 14).date(), now=now
    )
    assert filled["pruefung_bis"] == "2026-10-17"
    filled = values.defaults(
        definition.collection("messungen"),
        "m.schmidt",
        today=datetime(2026, 10, 14).date(),
        now=now,
    )
    assert filled["mitarbeiter"] == "m.schmidt"
    assert filled["gemessen_am"] == "2026-10-14T11:30"


@pytest.fixture
def http_app(app_definitions, client, db):
    from kurort_app.apps.installations import install

    app = client.app.state.apps.valid["geraetecheck"]
    install(db, app)
    db.add(Room(number="101", category="Test", floor=1, max_occupancy=1, nightly_rate=0))
    db.commit()
    return client, app


def test_http_all_types_edit_legacy_backrefs_defaults_and_delete(db, http_app):
    import re

    client, app = http_app
    device_response = client.post(
        "/apps/geraetecheck/geraete/neu",
        data={
            "name": "Küche",
            "aktiv": "true",
            "soll_min": "0",
            "soll_max": "7",
            "pruefung_bis": "2026-10-17",
        },
        follow_redirects=False,
    )
    assert device_response.status_code == 303
    device = db.scalars(select(AppRecord).where(AppRecord.collection == "geraete")).one()
    prefilled = client.get(f"/apps/geraetecheck/messungen/neu?geraet={device.id}").text
    assert re.search(rf'<option value="{device.id}"[^>]*selected', prefilled)
    assert re.search(r'name="gemessen_am"[^>]*value="2026-10-14T', prefilled)
    assert re.search(r'name="mitarbeiter"[^>]*value="rezeption"', prefilled)
    assert 'value="2026-10-17"' in client.get("/apps/geraetecheck/geraete/neu").text
    data = {
        "geraet": str(device.id),
        "gemessen_am": "2026-10-14T07:30",
        "temperatur": "8,5",
        "massnahme": "Tür geschlossen",
        "mitarbeiter": "Maria",
        "tag": "2026-10-14",
        "zeit": "07:30",
        "anzahl": "2",
        "kontrolliert": "true",
        "zustand": "gut",
        "merkmale": ["innen", "aussen"],
        "zimmer": "101",
    }
    response = client.post("/apps/geraetecheck/messungen/neu", data=data, follow_redirects=False)
    assert response.status_code == 303
    assert "Abweichung" in response.headers["location"]
    row = db.scalars(select(AppRecord).where(AppRecord.collection == "messungen")).one()
    assert row.data == {
        **data,
        "geraet": device.id,
        "temperatur": "8.5",
        "gemessen_am": "2026-10-14T05:30:00+00:00",
        "anzahl": 2,
        "kontrolliert": True,
    }
    detail = client.get(f"/apps/geraetecheck/messungen/{row.id}")
    assert detail.status_code == 200 and "8,5 °C" in detail.text and "Abweichung" in detail.text
    backrefs = client.get(f"/apps/geraetecheck/geraete/{device.id}").text
    assert "Verknüpfte Einträge" in backrefs and f"/messungen/{row.id}" in backrefs
    row.data = {**row.data, "entfernt": "Bleibt"}
    db.commit()
    assert (
        "Weitere Felder (ältere Version)"
        in client.get(f"/apps/geraetecheck/messungen/{row.id}").text
    )
    app.version = 2
    edited = client.post(
        f"/apps/geraetecheck/messungen/{row.id}/bearbeiten",
        data={**data, "temperatur": "6,0"},
        follow_redirects=False,
    )
    assert edited.status_code == 303
    db.refresh(row)
    assert (
        row.data["entfernt"] == "Bleibt"
        and row.updated_by == "rezeption"
        and row.definition_version == 2
    )
    event = db.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "app_record.updated", AuditEvent.entity_id == str(row.id)
        )
    ).one()
    assert event.payload["changes"]["temperatur"] == ["8.5", "6.0"]
    assert (
        client.post(
            f"/apps/geraetecheck/messungen/{row.id}/loeschen", follow_redirects=False
        ).status_code
        == 303
    )
    assert client.get(f"/apps/geraetecheck/messungen/{row.id}").status_code == 404
    assert f'/messungen/{row.id}"' not in client.get("/apps/geraetecheck/messungen").text
    assert f'/messungen/{row.id}"' not in client.get(f"/apps/geraetecheck/geraete/{device.id}").text
    assert (
        b"T\xc3\xbcr geschlossen"
        not in client.get(
            "/apps/geraetecheck/messungen/export.csv?von=2026-10-01&bis=2026-10-31"
        ).content
    )
    assert db.scalars(select(AuditEvent).where(AuditEvent.action == "app_record.deleted")).one()


@pytest.mark.parametrize(
    "collection,data,phrase",
    [
        ("geraete", {}, "Name ist Pflicht."),
        ("geraete", {"name": "x" * 81}, "höchstens 80"),
        ("messungen", {"temperatur": "101"}, "höchstens 100"),
        ("messungen", {"zustand": "???"}, "gültige Auswahl"),
        ("messungen", {"geraet": "9999"}, "Eintrag nicht vorhanden"),
        ("messungen", {"zimmer": "9999"}, "Zimmer nicht vorhanden"),
    ],
)
def test_http_invalid_retains_values_and_never_writes(db, http_app, collection, data, phrase):
    client, _ = http_app
    response = client.post(f"/apps/geraetecheck/{collection}/neu", data=data)
    assert response.status_code == 422
    assert phrase in response.text and "Bitte prüfen" in response.text
    assert not db.scalars(select(AppRecord)).all()


def test_http_warn_block_open_limits_and_htmx_filters(db, http_app):
    from kurort_app.apps import store

    client, app = http_app
    device = store.create(
        db, app, "geraete", {"name": "Küche", "soll_min": "0", "soll_max": "7", "aktiv": True}
    )
    db.commit()
    data = {"geraet": str(device.id), "gemessen_am": "2026-10-14T07:30", "temperatur": "8,5"}
    failed = client.post("/apps/geraetecheck/messungen/neu", data=data)
    assert failed.status_code == 422 and "Bei einer Abweichung ist „Maßnahme" in failed.text
    assert 'value="8,5"' in failed.text
    app.collection("messungen").field("temperatur").range.severity = "block"
    failed = client.post(
        "/apps/geraetecheck/messungen/neu", data={**data, "massnahme": "Korrektur"}
    )
    assert failed.status_code == 422 and "0,0 bis 7,0 °C" in failed.text
    app.collection("messungen").field("temperatur").range.severity = "warn"
    assert (
        client.post(
            "/apps/geraetecheck/messungen/neu",
            data={**data, "massnahme": "Korrektur"},
            follow_redirects=False,
        ).status_code
        == 303
    )
    page = client.get(
        "/apps/geraetecheck/messungen?q=KORREKTUR&von=2026-10-14&bis=2026-10-14&abweichungen=1",
        headers={"HX-Request": "true"},
    )
    assert page.status_code == 200 and "Abweichung" in page.text and "<html" not in page.text
    assert (
        "Korrektur"
        not in client.get(
            "/apps/geraetecheck/messungen?bis=2026-10-13", headers={"HX-Request": "true"}
        ).text
    )
    store.update(db, app, device, {"name": "Küche", "soll_min": "0"})
    db.commit()
    assert (
        client.post(
            "/apps/geraetecheck/messungen/neu", data=data, follow_redirects=False
        ).status_code
        == 303
    )


def test_http_pagination_typed_orders_and_status_panels(db, http_app):
    import re

    from kurort_app.apps import store

    client, app = http_app
    device = store.create(
        db, app, "geraete", {"name": "Küche", "aktiv": True, "pruefung_bis": "2026-10-17"}
    )
    for i in range(53):
        store.create(
            db,
            app,
            "messungen",
            {
                "geraet": device.id,
                "gemessen_am": f"2026-10-13T{(i // 60):02}:{i % 60:02}",
                "temperatur": str(i),
            },
        )
    db.commit()

    def ids(url):
        response = client.get(url, headers={"HX-Request": "true"})
        assert response.status_code == 200 and "<html" not in response.text
        return re.findall(
            r'class="app-record-title" href="[^\"]+/(\d+)"', response.text
        ), response.text

    app.collection("messungen").order_by = "-temperatur"
    first, text = ids("/apps/geraetecheck/messungen")
    assert len(first) == 50 and first[0] == "54" and "Weitere anzeigen" in text
    second, _ = ids("/apps/geraetecheck/messungen?page=2")
    assert len(second) == 3 and not set(first) & set(second)
    app.collection("messungen").order_by = "-gemessen_am"
    assert ids("/apps/geraetecheck/messungen")[0][0] == "54"
    home = client.get("/apps/geraetecheck").text
    assert "Fällig" in home and "Jetzt erfassen" in home and f"geraet={device.id}" in home
    assert "Warnungen" in home and "läuft ab" in home
    assert "läuft ab" in client.get("/apps/geraetecheck/geraete").text
    store.delete(db, app, device)
    db.commit()
    home = client.get("/apps/geraetecheck").text
    assert "Jetzt erfassen" not in home and "Warnungen" not in home


def test_http_record_actor_is_logged_in_username(db, app_definitions, oidc_client, idp):
    from kurort_app.apps import store
    from kurort_app.apps.installations import install
    from tests.app.auth_helpers import login

    app = oidc_client.app.state.apps.valid["geraetecheck"]
    install(db, app)
    row = store.create(db, app, "geraete", {"name": "Küche"})
    db.commit()
    login(oidc_client)
    response = oidc_client.post(
        "/apps/geraetecheck/messungen/neu",
        data={"geraet": str(row.id), "temperatur": "3,5", "gemessen_am": "2026-10-14T07:30"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    reading = db.scalars(select(AppRecord).where(AppRecord.collection == "messungen")).one()
    assert reading.created_by == "m.schmidt"
    event = db.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "app_record.created", AuditEvent.entity_id == str(reading.id)
        )
    ).one()
    assert event.actor == "m.schmidt"


def test_search_matches_what_the_list_shows(db, definition):
    from kurort_app.apps import store

    device = store.create(db, definition, "geraete", {"name": "Tiefkühler Küche"})
    other = store.create(db, definition, "geraete", {"name": "Keller"})
    reading = store.create(
        db,
        definition,
        "messungen",
        {
            "geraet": device.id,
            "gemessen_am": "2026-10-14T07:30",
            "temperatur": "9,5",
            "zustand": "gut",
            "mitarbeiter": "j.becker",
        },
    )
    store.create(
        db,
        definition,
        "messungen",
        {"geraet": other.id, "gemessen_am": "2026-10-14T08:00", "temperatur": "4"},
    )

    def found(q):
        return [r.id for r in store.query(db, definition, "messungen", q=q)]

    for q in ("tiefkühler", "9,5 °C", "9.5", "Gut", "J. Becker", "j.becker", "14.10.2026 07:30 "):
        assert found(q) == [reading.id], q
    assert found("nirgends") == []


def test_history_changes_read_like_the_detail_view(db, http_app):
    from kurort_app.apps import store

    client, app = http_app
    kitchen = store.create(db, app, "geraete", {"name": "Küche", "soll_min": "0", "soll_max": "7"})
    cellar = store.create(db, app, "geraete", {"name": "Keller"})
    data = {
        "geraet": kitchen.id,
        "gemessen_am": "2026-10-14T07:30",
        "temperatur": "8,5",
        "massnahme": "Tür geschlossen",
        "mitarbeiter": "m.schmidt",
    }
    reading = store.create(db, app, "messungen", data, actor="m.schmidt")
    reading.data = {**reading.data, "legacy": "alt"}
    store.update(
        db,
        app,
        reading,
        {**data, "geraet": cellar.id, "temperatur": "6", "massnahme": "", "kontrolliert": "on"},
        actor="t.weber",
    )
    event = db.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "app_record.updated", AuditEvent.entity_id == str(reading.id)
        )
    ).one()
    assert store.changes(db, app, event.payload) == [
        ("Gerät", "Küche", "Keller"),
        ("Temperatur", "8,5 °C", "6,0 °C"),
        ("Maßnahme", "Tür geschlossen", "–"),
        ("Kontrolliert", "–", "ja"),
    ]
    legacy = {"collection": "messungen", "changes": {"alt": [None, "x"]}}
    assert store.changes(db, app, legacy) == [("alt", "–", "x")]
    deviation = store.create(db, app, "messungen", data, actor="m.schmidt")
    db.commit()
    page = client.get(f"/apps/geraetecheck/messungen/{reading.id}").text
    assert "Küche → Keller" in page and "8,5 °C → 6,0 °C" in page and "Tür geschlossen → –" in page
    assert "null" not in page and "app-audit-payload" not in page
    assert "<dd>M. Schmidt</dd>" in page and "<dd>T. Weber</dd>" in page
    assert "Sollbereich" not in page
    page = client.get(f"/apps/geraetecheck/messungen/{deviation.id}").text
    assert "Abweichung" in page and "Sollbereich Temperatur: 0,0 bis 7,0 °C" in page
    assert "Gerät:</span> Küche" in page  # a new entry lists its values without arrows


def test_form_messages_name_field_once_and_limits_carry_the_unit(db, http_app):
    client, _ = http_app
    page = client.post("/apps/geraetecheck/geraete/neu", data={}).text
    assert "Name ist Pflicht." in page and "Name: Name ist Pflicht." not in page
    page = client.post("/apps/geraetecheck/messungen/neu", data={"temperatur": "101"}).text
    assert "Temperatur: Wert darf höchstens 100,0 °C sein." in page
