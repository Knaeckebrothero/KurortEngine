"""F8 stock, breakfast forecast and ordering acceptance tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from tests.app.conftest import BUSINESS_DATE as D


def test_ac2_suggestion_rules():
    from kurort_app.apps.plugins.inventur import suggest

    article = {"pro_fruehstueck": "0.03", "mindestbestand": "1", "packungsgroesse": "0.5"}
    result = suggest(article, 20, Decimal("0.6"))
    assert result.amount == Decimal("1.0")
    assert "unter Mindestbestand" in result.flags
    assert suggest(article, 20, Decimal("2")).amount == 0
    assert suggest({"zielbestand": "3", "packungsgroesse": "0.5"}, 0, Decimal("1.2")).amount == 2
    assert suggest({"mindestbestand": "2"}, 0, Decimal("1")).amount == 1
    assert suggest({"pro_fruehstueck": "0", "mindestbestand": "0"}, 20, Decimal("0")).amount == 0
    result = suggest({}, 20, None)
    assert result.amount is None
    assert result.stock == 0
    assert set(result.flags) == {"Bestand unbekannt", "Kein Zielbestand"}
    assert suggest({"zielbestand": "2"}, 0, None).amount == 2


def test_ac3_breakfast_forecast_boundaries():
    from kurort_app.apps.plugins.inventur import expected_breakfasts

    def stay(arrival, departure, guests=2, status="reserved"):
        return SimpleNamespace(
            arrival=D + timedelta(days=arrival),
            departure=D + timedelta(days=departure),
            guests=[None] * guests,
            status=status,
        )

    stays = [
        stay(-1, 0),
        stay(0, 2, 3),
        stay(1, 3, 1),
        stay(-1, 4, 9, "cancelled"),
        stay(-1, 4, 8, "no_show"),
        stay(-1, 1, 1, "checked_out"),
    ]
    assert expected_breakfasts(stays, D, D + timedelta(days=3)) == 11
    assert expected_breakfasts(stays, D, D) == 0


def test_ac1_seed_definition_and_history(db, client):
    from kurort_app.apps import store
    from kurort_app.apps.models import AppInstallation
    from kurort_app.apps.registry import AppRegistry
    from kurort_app.seed import seed_demo_data

    registry = AppRegistry()
    assert not registry.broken
    app = registry.valid["inventur"]
    for _ in range(2):
        db.expunge_all()
        seed_demo_data(db, reset=True, anchor=D)
        assert db.get(AppInstallation, "inventur").enabled
        assert len(store.records(db, app, "lieferanten")) == 4
        articles = store.records(db, app, "artikel")
        assert len(articles) == 26
        orders = store.records(db, app, "bestellungen")
        assert len(orders) == 52
        lines = store.records(db, app, "positionen")
        assert all(any(line.data["bestellung"] == order.id for line in lines) for order in orders)
        assert all(order.data["status"] == "geliefert" for order in orders)
        counts = store.records(db, app, "bestaende")
        for article in articles:
            latest = max(
                datetime.fromisoformat(r.data["gezaehlt_am"])
                for r in counts
                if r.data["artikel"] == article.id
            )
            assert D - timedelta(days=3) <= latest.astimezone(UTC).date() < D
    assert client.get("/apps/inventur").status_code == 200


PATH = "/apps/inventur/ansicht/bestellvorschlag"


def supplier_and_articles(db, app):
    from kurort_app.apps import store

    supplier = next(
        r for r in store.records(db, app, "lieferanten") if r.data["name"].startswith("Großmarkt")
    )
    articles = sorted(
        [r for r in store.records(db, app, "artikel") if r.data["lieferant"] == supplier.id],
        key=lambda r: (r.data["kategorie"], r.data["name"]),
    )
    return supplier, articles


def test_ac4_supplier_active_articles_and_defaults(seeded, client):
    from kurort_app.apps import store

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    inactive = articles.pop()
    store.update(seeded, app, inactive, {**inactive.data, "aktiv": False})
    seeded.commit()
    page = client.get(PATH, params={"lieferant": supplier.id})
    assert page.status_code == 200
    assert [row["article"].id for row in page.context["rows"]] == [r.id for r in articles]
    assert all(row["latest"] is not None for row in page.context["rows"])
    assert inactive.data["name"] not in page.text
    assert "Brötchen" not in page.text
    assert "Erwartete Frühstücke" in page.text and "aus den Reservierungen" in page.text
    assert page.context["delivery"] == D + timedelta(days=1)
    assert page.context["next_delivery"] == D + timedelta(days=4)
    default = client.get(PATH)
    assert default.context["supplier"].data["name"] == "Bäckerei am Kurpark"


def test_ac5_recalculate_without_writes_and_preserve_errors(seeded, client):
    from sqlalchemy import select

    from kurort_app.apps import store
    from kurort_app.models import AuditEvent

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    article = articles[0]
    before = len(store.records(seeded, app))
    audit_before = len(seeded.scalars(select(AuditEvent)).all())
    data = {
        "lieferant": str(supplier.id),
        "lieferung_am": str(D + timedelta(days=1)),
        "naechste_lieferung": str(D + timedelta(days=4)),
        "aktion": "berechnen",
        f"bestand_{article.id}": "999,5",
        f"bestellt_{article.id}": "5",
        f"grund_{article.id}": "angebot",
    }
    page = client.post(PATH, data=data)
    assert page.status_code == 200
    row = next(r for r in page.context["rows"] if r["article"].id == article.id)
    assert row["suggestion"].amount == 0 and row["ordered"] == 0
    assert row["count_raw"] == "999,5"
    for action in ("berechnen", "speichern"):
        for key, value, message in [
            (f"bestand_{article.id}", "-1", "mindestens 0"),
            (f"bestellt_{article.id}", "abc", "gültige Zahl"),
            (f"bestand_{article.id}", "NaN", "gültige Zahl"),
            ("naechste_lieferung", data["lieferung_am"], "nach der Lieferung"),
            ("lieferung_am", "falsch", "gültiges Datum"),
        ]:
            invalid = client.post(PATH, data={**data, "aktion": action, key: value})
            assert invalid.status_code == 422
            assert message in invalid.text
            assert invalid.context["raw"][key] == value
            assert invalid.context["raw"][f"grund_{article.id}"] == "angebot"
    assert len(store.records(seeded, app)) == before
    assert len(seeded.scalars(select(AuditEvent)).all()) == audit_before


def test_ac6_save_atomic_counts_order_lines_notice_and_audit(seeded, client):
    from sqlalchemy import select

    from kurort_app.apps import store
    from kurort_app.models import AuditEvent

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    before = {r.id for r in store.records(seeded, app)}
    article = articles[0]
    data = {
        "lieferant": supplier.id,
        "aktion": "speichern",
        "lieferung_am": str(D + timedelta(days=1)),
        "naechste_lieferung": str(D + timedelta(days=4)),
        f"bestand_{article.id}": "1,5",
        f"bestellt_{article.id}": "7,5",
        f"grund_{article.id}": "angebot",
    }
    page = client.post(PATH, data=data)
    assert page.status_code == 200 and "/bestellungen/" in str(page.url)
    assert "Bestellung bei Großmarkt Main-Kinzig gespeichert" in page.text
    assert "Verknüpfte Einträge" in page.text
    created = [r for r in store.records(seeded, app) if r.id not in before]
    order = next(r for r in created if r.collection == "bestellungen")
    assert order.data["status"] == "bestellt" and order.data["bestellt_am"] == str(D)
    from kurort_app.apps.plugins.inventur import expected_breakfasts, reservations_for

    assert order.data["fruehstuecke"] == expected_breakfasts(
        reservations_for(seeded, D + timedelta(days=1), D + timedelta(days=4)),
        D + timedelta(days=1),
        D + timedelta(days=4),
    )
    counts = [r for r in created if r.collection == "bestaende"]
    assert len(counts) == 1 and Decimal(counts[0].data["menge"]) == Decimal("1.5")
    line = next(
        r for r in created if r.collection == "positionen" and r.data["artikel"] == article.id
    )
    assert line.data["bestellung"] == order.id
    assert Decimal(line.data["bestand"]) == Decimal("1.5")
    assert Decimal(line.data["bestellt"]) == Decimal("7.5") and line.data["grund"] == "angebot"
    assert "vorschlag" in line.data
    events = seeded.scalars(
        select(AuditEvent).where(AuditEvent.action == "app_record.created")
    ).all()
    assert all(sum(e.entity_id == str(r.id) for e in events) == 1 for r in created)


def test_ac7_value_and_missing_price_names(seeded, client):
    from kurort_app.apps import store

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    for article in articles[:3]:
        store.update(seeded, app, article, {k: v for k, v in article.data.items() if k != "preis"})
    seeded.commit()
    page = client.get(PATH, params={"lieferant": supplier.id})
    assert page.status_code == 200
    expected = sum(
        (row["ordered"] or 0) * Decimal(row["article"].data["preis"])
        for row in page.context["rows"]
        if row["article"].data.get("preis") is not None
    )
    assert page.context["total"] == expected
    assert "3 Artikel ohne Preis" in page.text
    assert all(
        article.data["name"] in page.text.split("3 Artikel ohne Preis")[1]
        for article in articles[:3]
    )


def test_ac8_last_five_supplier_orders_and_values(seeded, client):
    from kurort_app.apps import store

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    page = client.get(PATH, params={"lieferant": supplier.id})
    assert page.status_code == 200
    history = page.context["history"]
    expected = sorted(
        store.records(seeded, app, "bestellungen", {"lieferant": supplier.id}),
        key=lambda r: (r.data["bestellt_am"], r.id),
        reverse=True,
    )[:5]
    prices = {r.id: Decimal(r.data["preis"]) for r in articles}
    assert [h["order"].id for h in history] == [r.id for r in expected]
    for entry in history:
        lines = store.records(seeded, app, "positionen", {"bestellung": entry["order"].id})
        for key in ("vorschlag", "bestellt"):
            assert entry[key] == sum(
                Decimal(line.data[key]) * prices[line.data["artikel"]] for line in lines
            )
        assert entry["differences"] == sum(
            line.data["vorschlag"] != line.data["bestellt"] for line in lines
        )
        assert f"/bestellungen/{entry['order'].id}" in page.text


def test_ac9_role_permissions_and_kitchen_sidebar(seeded, oidc_client, idp):
    from kurort_app.apps import store
    from tests.app.auth_helpers import login

    app = oidc_client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    for role in ("rezeption", "kueche", "leitung"):
        idp.claims.update(roles=[role], preferred_username="j.becker")
        oidc_client.post("/auth/logout", follow_redirects=False)
        login(oidc_client)
        page = oidc_client.get(PATH, params={"lieferant": supplier.id})
        assert page.status_code == 200
        assert ("Bestellung speichern" in page.text) == (role != "rezeption")
        assert "Inventur &amp; Bestellung" in page.text
        assert (
            oidc_client.post(
                PATH, data={"lieferant": supplier.id, "aktion": "berechnen"}
            ).status_code
            == 200
        )
        saved = oidc_client.post(
            PATH, data={"lieferant": supplier.id, "aktion": "speichern"}, follow_redirects=False
        )
        assert saved.status_code == (403 if role == "rezeption" else 303)
        assert oidc_client.post("/apps/inventur/positionen/neu", data={}).status_code == (
            422 if role == "leitung" else 403
        )
    assert store.records(seeded, app, "bestellungen")[-1].created_by == "j.becker"


def test_ac10_reports_and_csv(seeded, client):
    csv = client.get(
        "/apps/inventur/positionen/export.csv?bericht=bestellungen&von=2026-10-01&bis=2026-10-14"
    )
    assert csv.status_code == 200
    header = csv.content.decode("utf-8-sig").splitlines()[0]
    assert all(
        label in header.split(";")
        for label in ("Bestand", "Vorschlag", "Bestellt", "Grund für Abweichung")
    )
    pdf = client.get(
        "/apps/inventur/bericht.pdf?bericht=bestellungen&von=2026-10-01&bis=2026-10-14"
    )
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


def test_counts_use_timestamp_and_zero_orders_are_omitted(seeded, client):
    from kurort_app.apps import store

    app = client.app.state.apps.valid["inventur"]
    supplier, articles = supplier_and_articles(seeded, app)
    article = articles[0]
    store.create(
        seeded,
        app,
        "bestaende",
        {
            "artikel": article.id,
            "gezaehlt_am": str(D - timedelta(days=10)) + "T07:00",
            "menge": "999",
        },
    )
    seeded.commit()
    page = client.get(PATH, params={"lieferant": supplier.id})
    assert page.context["rows"][0]["suggestion"].stock != 999
    before = {r.id for r in store.records(seeded, app)}
    data = {"lieferant": supplier.id, "aktion": "speichern"}
    for entry in articles:
        data[f"bestand_{entry.id}"] = "9999"
        data[f"bestellt_{entry.id}"] = "0"
    data[f"bestellt_{article.id}"] = "2,5"
    response = client.post(PATH, data=data, follow_redirects=False)
    assert response.status_code == 303
    created = [r for r in store.records(seeded, app) if r.id not in before]
    assert len([r for r in created if r.collection == "bestaende"]) == len(articles)
    lines = [r for r in created if r.collection == "positionen"]
    assert len(lines) == 1
    assert Decimal(lines[0].data["bestellt"]) == Decimal("2.5")
    assert Decimal(lines[0].data["vorschlag"]) == 0
    assert not lines[0].data.get("grund")


def test_kitchen_realm_raw_config_contract():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    values = yaml.safe_load((root / "deploy/k3d/keycloak/values.yaml").read_text())
    jana = next(u for u in values["users"] if u["username"] == "j.becker")
    assert (jana["firstName"], jana["lastName"], jana["roles"]) == ("Jana", "Becker", ["kueche"])
    template = (root / "deploy/k3d/keycloak/templates/realm-configmap.yaml").read_text()
    assert '(dict "name" "kueche" "description" "Küche")' in template
