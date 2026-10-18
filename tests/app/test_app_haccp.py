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


def reading(device, temperature, action=""):
    return {
        "geraet": str(device.id),
        "gemessen_am": "2026-10-14T07:30",
        "temperatur": temperature,
        "massnahme": action,
        "mitarbeiter": "j.becker",
    }


def test_ac4_corrective_action_required_before_saving_deviation(client, seeded):
    device = named(seeded, "geraete", "Kühlschrank Küche")
    app = AppRegistry().valid["haccp"]
    count = len(store.records(seeded, app, "messungen"))
    failed = client.post("/apps/haccp/messungen/neu", data=reading(device, "8,5"))
    assert failed.status_code == 422
    assert "Bei einer Abweichung ist „Korrekturmaßnahme" in failed.text
    assert 'value="8,5"' in failed.text
    assert len(store.records(seeded, app, "messungen")) == count
    saved = client.post(
        "/apps/haccp/messungen/neu",
        data=reading(device, "8,5", "Tür geschlossen"),
        follow_redirects=False,
    )
    assert saved.status_code == 303 and "Abweichung" in saved.headers["location"]
    row = max(store.records(seeded, app, "messungen"), key=lambda r: r.id)
    assert row.out_of_range and row.data["massnahme"] == "Tür geschlossen"
    assert "Abweichung" in client.get(f"/apps/haccp/messungen/{row.id}").text
    from sqlalchemy import select

    from kurort_app.models import AuditEvent

    event = seeded.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id == str(row.id), AuditEvent.action == "app_record.created"
        )
    ).one()
    assert event.payload["app"] == "haccp" and event.payload["collection"] == "messungen"


def test_ac4_all_device_ranges_and_open_hot_holding_upper_bound(client, seeded):
    app = AppRegistry().valid["haccp"]
    for name, temperature, expected in [
        ("Kühlschrank Küche", "-0,5", True),
        ("Kühlschrank Küche", "4,0", False),
        ("Tiefkühler Küche", "-15,0", True),
        ("Tiefkühler Küche", "-20,0", False),
        ("Warmhaltung Rührei", "60,0", True),
        ("Warmhaltung Rührei", "75,0", False),
    ]:
        device = named(seeded, "geraete", name)
        response = client.post(
            "/apps/haccp/messungen/neu",
            data=reading(device, temperature, "Nachkontrolle" if expected else ""),
            follow_redirects=False,
        )
        assert response.status_code == 303
        row = max(store.records(seeded, app, "messungen"), key=lambda r: r.id)
        assert row.out_of_range is expected


def test_ac5_due_capture_prefills_device_time_and_clears_due(client, seeded):
    device = named(seeded, "geraete", "Tiefkühler Küche")
    due = section(client.get("/apps/haccp").text, "due")
    link = f"/apps/haccp/messungen/neu?geraet={device.id}"
    assert f'href="{link}"' in due
    form = client.get(link)
    assert form.status_code == 200
    assert re.search(rf'<option value="{device.id}"[^>]*selected', form.text)
    assert re.search(
        r'name="gemessen_am"\s+type="datetime-local"\s+value="2026-10-14T\d\d:\d\d"', form.text
    )
    response = client.post(
        "/apps/haccp/messungen/neu", data=reading(device, "-20,0"), follow_redirects=False
    )
    assert response.status_code == 303
    assert "Tiefkühler Küche" not in section(client.get("/apps/haccp").text, "due")


def test_ac6_cleaning_requires_tasks_and_resolves_due(client, seeded):
    station = named(seeded, "stationen", "Eierstation")
    data = {"station": station.id, "erledigt_am": "2026-10-14T10:00", "mitarbeiter": "j.becker"}
    failed = client.post("/apps/haccp/reinigungen/neu", data=data)
    assert failed.status_code == 422 and "Aufgaben ist Pflicht." in failed.text
    assert "Eierstation" in section(client.get("/apps/haccp").text, "due")
    saved = client.post(
        "/apps/haccp/reinigungen/neu",
        data={**data, "aufgaben": ["geraet", "oberflaechen"]},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert "Eierstation" not in section(client.get("/apps/haccp").text, "due")


def test_ac6_weekly_cleaning_due_only_on_seventh_day(seeded):
    from kurort_app.apps import status

    app = AppRegistry().valid["haccp"]
    station = named(seeded, "stationen", "Kühlschränke innen")
    rows = store.records(seeded, app)
    for delta, expected in [(0, "erledigt"), (1, "erledigt"), (2, "fällig"), (3, "überfällig")]:
        day = D + timedelta(days=delta)
        item = next(
            s
            for s in status.schedules(app, rows, today=day, now=status.business_now(day))
            if s.record.id == station.id
        )
        assert item.status == expected


def test_ac7_use_by_default_and_done_silences_alert_without_losing_record(client, seeded):
    form = client.get("/apps/haccp/offene_produkte/neu")
    assert form.status_code == 200
    assert re.search(r'name="verbrauchen_bis"\s+type="date"\s+value="2026-10-17"', form.text)
    milk = named(seeded, "offene_produkte", "Milch")
    response = client.post(
        f"/apps/haccp/offene_produkte/{milk.id}/bearbeiten",
        data={**milk.data, "erledigt": "true"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    seeded.refresh(milk)
    assert milk.data["erledigt"] and milk.deleted_at is None
    assert "Milch" not in section(client.get("/apps/haccp").text, "alerts")
    assert client.get(f"/apps/haccp/offene_produkte/{milk.id}").status_code == 200


def test_ac8_four_pdfs_temperature_rows_and_rejected_goods_csv(client, seeded):
    import csv
    import io

    from kurort_app.apps import reports

    app = AppRegistry().valid["haccp"]
    page = client.get("/apps/haccp/bericht")
    assert page.status_code == 200
    assert [r.key for r in app.reports] == ["temperatur", "reinigung", "wareneingang", "gesamt"]
    for report in app.reports:
        assert report.title in page.text
        pdf = client.get(
            f"/apps/haccp/bericht.pdf?bericht={report.key}&von=2026-10-01&bis=2026-10-31"
        )
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF-") and len(pdf.content) > 1000
    rows = reports.build_rows(seeded, app, app.reports[0].sections[0], D - timedelta(days=28), D)
    deviations = [row for row in rows if row[-1] == "ja"]
    assert len(deviations) == 2
    assert any(
        row[1] == "Getränkekühlschrank Bar"
        and row[2] == "8,4"
        and row[4] == "Tür stand offen, nach 30 Min. 5,9 °C"
        for row in deviations
    )
    assert any(
        row[1] == "Tiefkühler Küche"
        and row[2] == "-16,5"
        and row[4] == "Abtauvorgang, nach 1 Std. −19,0 °C"
        for row in deviations
    )
    response = client.get("/apps/haccp/wareneingang/export.csv?von=2026-10-01&bis=2026-10-31")
    assert response.status_code == 200
    csv_rows = list(
        csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";")
    )
    rejected = next(row for row in csv_rows if row["Produkt"] == "Hackfleisch")
    assert rejected["Ergebnis"] == "Abgelehnt" and rejected["Temperatur"] == "9,2"
    assert rejected["Bemerkung"] == "Kühlkette unterbrochen, zurückgegeben"


def test_ac9_kitchen_home_sidebar_writes_and_master_edits(oidc_client, idp, seeded):
    from kurort_app.auth import ROLE_LABELS
    from tests.app.auth_helpers import login

    idp.claims.update(roles=["kueche"], preferred_username="j.becker", name="Jana Becker")
    login(oidc_client)
    assert ROLE_LABELS["kueche"] == "Küche"
    home = oidc_client.get("/", follow_redirects=False)
    assert home.status_code == 303 and home.headers["location"] == "/apps/haccp"
    page = oidc_client.get("/apps/haccp")
    assert page.status_code == 200
    nav = page.text.split('<nav class="rail-nav">')[1].split("</nav>")[0]
    assert re.findall(r'class="rail-label">([^<]+)', nav) == ["Apps"]
    assert 'href="/apps/haccp"' in nav
    assert "Neue Reservierung" not in page.text and 'class="assistant' not in page.text
    assert oidc_client.get("/anreisen").status_code == 403
    assert oidc_client.get("/zimmerstatus").status_code == 403
    assert oidc_client.get("/apps").status_code == 403
    device = named(seeded, "geraete", "Kühlschrank Küche")
    assert (
        oidc_client.post(
            "/apps/haccp/messungen/neu", data=reading(device, "4,0"), follow_redirects=False
        ).status_code
        == 303
    )
    assert "Bearbeiten" in oidc_client.get(f"/apps/haccp/geraete/{device.id}").text
    saved = oidc_client.post(
        f"/apps/haccp/geraete/{device.id}/bearbeiten",
        data={**device.data, "standort": "Küche EG"},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    seeded.refresh(device)
    assert device.data["standort"] == "Küche EG" and device.updated_by == "j.becker"


def test_ac9_reception_records_but_cannot_change_master_data(oidc_client, idp, seeded):
    from tests.app.auth_helpers import login

    login(oidc_client)
    device = named(seeded, "geraete", "Kühlschrank Küche")
    assert (
        oidc_client.post(
            "/apps/haccp/messungen/neu", data=reading(device, "4,0"), follow_redirects=False
        ).status_code
        == 303
    )
    station = named(seeded, "stationen", "Eierstation")
    assert (
        oidc_client.post(
            "/apps/haccp/reinigungen/neu",
            data={"station": station.id, "erledigt_am": "2026-10-14T10:00", "aufgaben": ["geraet"]},
            follow_redirects=False,
        ).status_code
        == 303
    )
    for collection, row in [("geraete", device), ("stationen", station)]:
        assert "Bearbeiten" not in oidc_client.get(f"/apps/haccp/{collection}/{row.id}").text
        assert oidc_client.get(f"/apps/haccp/{collection}/{row.id}/bearbeiten").status_code == 403
        assert (
            oidc_client.post(
                f"/apps/haccp/{collection}/{row.id}/bearbeiten", data=row.data
            ).status_code
            == 403
        )
        assert oidc_client.post(f"/apps/haccp/{collection}/neu", data=row.data).status_code == 403
        assert oidc_client.post(f"/apps/haccp/{collection}/{row.id}/loeschen").status_code == 403
