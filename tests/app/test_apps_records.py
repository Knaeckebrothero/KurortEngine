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
    assert exc.value.errors["massnahme"] == 'Bei einer Abweichung ist „Maßnahme" Pflicht.'
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
