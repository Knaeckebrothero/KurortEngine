"""F7: the kitchen app exercises the shared declarative app platform."""

import re
from datetime import timedelta

from kurort_app.apps import store
from kurort_app.apps.models import AppInstallation
from kurort_app.apps.registry import AppRegistry
from kurort_app.seed import seed_demo_data
from tests.app.conftest import BUSINESS_DATE as D


def section(html, name):
    return re.search(rf'<section[^>]*aria-labelledby="app-{name}-title".*?</section>', html, re.S)[
        0
    ]


def named(db, collection, name):
    return next(
        row
        for row in store.records(db, AppRegistry().valid["haccp"], collection)
        if row.data.get("name", row.data.get("produkt")) == name
    )


def test_ac1_definition_catalogue_and_repeatable_reset(client, db):
    from kurort_app.cli import main

    assert main(["apps", "validate"]) == 0
    app = client.app.state.apps.valid["haccp"]
    assert app.title == "HACCP" and app.icon == "thermometer"
    assert [c.key for c in app.collections] == [
        "geraete",
        "messungen",
        "wareneingang",
        "offene_produkte",
        "stationen",
        "reinigungen",
    ]
    snapshot = None
    for _ in range(2):
        db.expunge_all()
        seed_demo_data(db, reset=True, anchor=D)
        installation = db.get(AppInstallation, "haccp")
        assert installation is not None and installation.enabled
        rows = store.records(db, app)
        current = [(r.collection, r.data, r.created_by, r.created_at) for r in rows]
        if snapshot is not None:
            assert current == snapshot
        snapshot = current
        assert len(store.records(db, app, "geraete")) == 5
        assert len(store.records(db, app, "stationen")) == 5
        assert len(store.records(db, app, "messungen")) == 140
        assert len(store.records(db, app, "reinigungen")) == 112
        assert len(store.records(db, app, "wareneingang")) == 8
        assert len(store.records(db, app, "offene_produkte")) == 6
        assert {r.created_by for r in rows} == {"j.becker", "m.schmidt"}
        assert all(r.data["mitarbeiter"] == r.created_by for r in rows if "mitarbeiter" in r.data)
        for row in rows:
            at = row.data.get("gemessen_am", row.data.get("erledigt_am"))
            if at:
                assert row.created_at.isoformat() == at
    assert "HACCP" in client.get("/apps").text


def test_ac2_seed_due_devices_and_stations(client, seeded):
    response = client.get("/apps/haccp")
    assert response.status_code == 200
    due = section(response.text, "due")
    items = re.findall(r'<li class="app-task">.*?</li>', due, re.S)
    expected = {
        "Tiefkühler Küche": "überfällig",
        "Kühlschrank Frühstücksbuffet": "fällig",
        "Getränkekühlschrank Bar": "fällig",
        "Warmhaltung Rührei": "fällig",
        "Eierstation": "überfällig",
        "Kaffeemaschine": "fällig",
        "Teestation": "fällig",
        "Buffet": "fällig",
    }
    assert len(items) == len(expected)
    for name, state in expected.items():
        item = next(item for item in items if f"<h3>{name}</h3>" in item)
        assert f">{state}</span>" in item and "Jetzt erfassen" in item
    assert "<h3>Kühlschrank Küche</h3>" not in due
    assert "Kühlschränke innen" not in due
    assert (
        response.text.index("Fällig")
        < response.text.index("Warnungen")
        < response.text.index("Abweichungen")
    )
    assert "Stammdaten" in response.text


def test_ac3_seed_alerts_and_seven_day_deviations(client, seeded):
    html = client.get("/apps/haccp").text
    warnings = section(html, "alerts")
    assert "Milch" in warnings and ">abgelaufen</span>" in warnings
    assert "Sahne" in warnings and ">läuft ab</span>" in warnings
    assert warnings.count('<li class="app-task">') == 2
    app = AppRegistry().valid["haccp"]
    done = [r for r in store.records(seeded, app, "offene_produkte") if r.data["erledigt"]]
    assert len(done) == 2
    assert all(r.data["produkt"] not in warnings for r in done)
    deviations = section(html, "deviations")
    rows = [r for r in store.records(seeded, app, "messungen") if r.out_of_range]
    assert len(rows) == 2
    recent = next(
        r
        for r in rows
        if store.record_date(app.collection("messungen"), r) == D - timedelta(days=3)
    )
    old = next(
        r
        for r in rows
        if store.record_date(app.collection("messungen"), r) == D - timedelta(days=9)
    )
    assert f'/messungen/{recent.id}"' in deviations
    assert "Tiefkühler Küche" in deviations and f'/messungen/{old.id}"' not in deviations
    assert "Getränkekühlschrank Bar" not in deviations


def test_ac10_demo_role_and_user_are_declared():
    from pathlib import Path

    import yaml

    from kurort_app.auth import ROLE_LABELS

    root = Path(__file__).resolve().parents[2] / "deploy/k3d/keycloak"
    values = yaml.safe_load((root / "values.yaml").read_text())
    template = (root / "templates/realm-configmap.yaml").read_text()
    declared = set(re.findall(r'\(dict "name" "([a-z]+)" "description"', template))
    assert declared == set(ROLE_LABELS) == {"leitung", "rezeption", "housekeeping", "kueche"}
    users = {user["username"]: user for user in values["users"]}
    assert users["j.becker"]["roles"] == ["kueche"]
    assert (users["j.becker"]["firstName"], users["j.becker"]["lastName"]) == ("Jana", "Becker")
    assert values["demoPassword"]
    assert all(set(user["roles"]) <= declared for user in users.values())
